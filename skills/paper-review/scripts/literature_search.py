#!/usr/bin/env python3
"""Multi-database academic literature search helper with Scientific Area routing & Security Hardening.

Queries OpenAlex (250M+ works across all disciplines), PubMed/EuropePMC,
Crossref (journals, engineering standards, humanities, SciELO/LatAm), and arXiv
using standard-library urllib (zero third-party packages required).

Information Security Hardening:
- Enforces HTTPS-only connections (`https://`) across all APIs (including arXiv).
- Caps HTTP response size (`MAX_RESPONSE_BYTES = 4 MB`) to prevent memory exhaustion.
- Rejects XML DTD/Entity declarations (`<!DOCTYPE`, `<!ENTITY`) prior to XML parsing to block XXE/Billion Laughs.
- Strips control/bidi characters from external metadata before returning results to LLM context.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from area_profiles import (  # noqa: E402
    AREA_DEFINITIONS,
    INVISIBLE_AND_BIDI_REGEX,
    resolve_area_code,
)


USER_AGENT = (
    "gemini-peer-review/2.1 (LaBiOmicS - Universidade de Mogi das Cruzes; "
    "Prof. Dr. Fabiano Bezerra Menegidio; mailto:fabianomenegidio@umc.br)"
)
MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # 4 MB cap per HTTP response


def _validate_https_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Security policy violation: only https:// URLs are permitted (got {parsed.scheme!r}).")


def _clean_external_text(value: str, max_len: int = 500) -> str:
    cleaned = INVISIBLE_AND_BIDI_REGEX.sub("", value or "")
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_len:
        return cleaned[:max_len].rstrip() + "…"
    return cleaned


def _http_get_json(url: str, timeout: float = 10.0, retries: int = 2) -> Any:
    _validate_https_url(url)
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(MAX_RESPONSE_BYTES)
                return json.loads(raw.decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(3.0 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < retries:
                time.sleep(2.0)
                continue
            raise
    return None


def _safe_parse_xml(xml_bytes: bytes) -> ET.Element:
    head_upper = xml_bytes[:4096].upper()
    if b"<!DOCTYPE" in head_upper or b"<!ENTITY" in head_upper:
        raise ValueError("Security policy violation: XML DTD/ENTITY declarations are forbidden (XXE/XML bomb protection).")
    return ET.fromstring(xml_bytes)


def search_arxiv_api(query: str, max_papers: int = 6, sort: str = "relevance") -> list[dict[str, Any]]:
    sort_by = "relevance" if sort == "relevance" else "submittedDate"
    params = urllib.parse.urlencode({
        "search_query": f"all:{query[:400]}",
        "start": 0,
        "max_results": max(1, min(25, max_papers)),
        "sortBy": sort_by,
        "sortOrder": "descending",
    })
    url = f"https://export.arxiv.org/api/query?{params}"
    _validate_https_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=12.0) as resp:
        xml_bytes = resp.read(MAX_RESPONSE_BYTES)

    root = _safe_parse_xml(xml_bytes)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns):
        raw_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        short_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
        title = _clean_external_text(entry.findtext("atom:title", default="", namespaces=ns) or "", max_len=300)
        summary = _clean_external_text(entry.findtext("atom:summary", default="", namespaces=ns) or "", max_len=500)
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:4] or "n.d."
        authors = [
            _clean_external_text(a.findtext("atom:name", default="", namespaces=ns) or "", max_len=80)
            for a in entry.findall("atom:author", ns)
        ]
        authors = [a for a in authors if a]
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        results.append({
            "id": f"arXiv:{short_id}",
            "year": published,
            "title": title,
            "authors": author_str or "Unknown",
            "citations": None,
            "retracted": False,
            "summary": summary,
            "source": "arXiv",
        })
    return results


def _reconstruct_openalex_abstract(inv_idx: dict[str, list[int]] | None) -> str:
    if not inv_idx or not isinstance(inv_idx, dict):
        return ""
    pos_map: dict[int, str] = {}
    for word, positions in inv_idx.items():
        if not isinstance(positions, list):
            continue
        for pos in positions[:5000]:
            if isinstance(pos, int) and 0 <= pos <= 10000:
                pos_map[pos] = str(word)
    if not pos_map:
        return ""
    words = [pos_map[k] for k in sorted(pos_map.keys())]
    return _clean_external_text(" ".join(words), max_len=500)


def search_openalex(query: str, max_papers: int = 6, sort: str = "relevance") -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "search": query[:400],
        "per-page": max(1, min(25, max_papers)),
    }
    if sort == "date":
        params["sort"] = "publication_date:desc"
    elif sort == "citations":
        params["sort"] = "cited_by_count:desc"

    url = f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}"
    data = _http_get_json(url)
    results = []
    for item in (data or {}).get("results", []):
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        oa_id = (item.get("id") or "").rsplit("/", 1)[-1]
        ident = f"DOI:{doi}" if doi else f"OpenAlex:{oa_id}"
        title = _clean_external_text(item.get("title") or "Untitled", max_len=300)
        year = item.get("publication_year") or "n.d."
        auths = [
            _clean_external_text((a.get("author") or {}).get("display_name", ""), max_len=80)
            for a in (item.get("authorships") or [])[:4]
        ]
        auths = [a for a in auths if a]
        author_str = ", ".join(auths[:3]) + (" et al." if len(auths) > 3 else "")
        summary = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
        results.append({
            "id": ident,
            "year": str(year),
            "title": title,
            "authors": author_str or "Unknown",
            "citations": item.get("cited_by_count", 0),
            "retracted": bool(item.get("is_retracted", False)),
            "summary": summary or "(No abstract in OpenAlex)",
            "source": "OpenAlex",
        })
    return results


def search_europepmc(query: str, max_papers: int = 6) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "query": query[:400],
        "format": "json",
        "pageSize": max(1, min(25, max_papers)),
        "resultType": "core",
    })
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}"
    data = _http_get_json(url)
    results = []
    for item in ((data or {}).get("resultList") or {}).get("result", []):
        pmid = item.get("pmid")
        doi = item.get("doi")
        ident = f"PMID:{pmid}" if pmid else (f"DOI:{doi}" if doi else f"EPMC:{item.get('id', '')}")
        if pmid and doi:
            ident = f"PMID:{pmid} | DOI:{doi}"
        title = _clean_external_text(item.get("title") or "Untitled", max_len=300)
        year = item.get("pubYear") or "n.d."
        author_str = _clean_external_text(item.get("authorString") or "Unknown", max_len=160)
        summary = _clean_external_text(item.get("abstractText") or "", max_len=500)
        results.append({
            "id": ident,
            "year": str(year),
            "title": title,
            "authors": author_str,
            "citations": item.get("citedByCount", 0),
            "retracted": item.get("pubType", "").lower().find("retracted") >= 0,
            "summary": summary or "(No abstract available)",
            "source": "PubMed/EuropePMC",
        })
    return results


def search_crossref(query: str, max_papers: int = 6) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "query": query[:400],
        "rows": max(1, min(25, max_papers)),
    })
    url = f"https://api.crossref.org/works?{params}"
    data = _http_get_json(url)
    items = ((data or {}).get("message") or {}).get("items", [])
    results = []
    for it in items:
        doi = it.get("DOI") or ""
        titles = it.get("title") or ["Untitled"]
        title = _clean_external_text(titles[0] if titles else "Untitled", max_len=300)
        issued = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = str(issued[0]) if issued and issued[0] else "n.d."
        authors = []
        for a in (it.get("author") or [])[:4]:
            given = a.get("given", "")
            family = a.get("family", "")
            full = _clean_external_text(f"{given} {family}".strip() or a.get("name", ""), max_len=80)
            if full:
                authors.append(full)
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        raw_abs = re.sub(r"<[^>]+>", " ", it.get("abstract") or "")
        summary = _clean_external_text(raw_abs, max_len=500)
        container = _clean_external_text((it.get("container-title") or [""])[0], max_len=120)
        results.append({
            "id": f"DOI:{doi}" if doi else "Crossref",
            "year": year,
            "title": title,
            "authors": author_str or "Unknown",
            "citations": it.get("is-referenced-by-count", 0),
            "retracted": bool(it.get("update-to")),
            "summary": summary or (f"Published in: {container}" if container else "(No abstract in Crossref)"),
            "source": "Crossref",
        })
    return results


def format_results(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No papers found."
    blocks = []
    for p in items:
        cite_str = f" | Citations: {p['citations']}" if p.get("citations") is not None else ""
        retract_str = " [⚠️ RETRACTED / UPDATED PAPER]" if p.get("retracted") else ""
        blocks.append(
            f"[{p['id']}] ({p['year']}) {p['title']}{retract_str}\n"
            f"  Source: {p['source']}{cite_str} | Authors: {p['authors']}\n"
            f"  Summary: {p['summary']}"
        )
    return "\n\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-database academic literature search with Area routing.")
    parser.add_argument("query", type=str, help="Search query string.")
    parser.add_argument("--max-papers", type=int, default=8, help="Max results per query (default 8).")
    parser.add_argument(
        "--sort",
        choices=["relevance", "date", "citations"],
        default="relevance",
        help="Sort order (default: relevance).",
    )
    parser.add_argument(
        "--source",
        choices=["all", "arxiv", "openalex", "pubmed", "crossref"],
        default="all",
        help="Database to search (default: all — routed by scientific area).",
    )
    parser.add_argument(
        "--area",
        default="auto",
        help="Major Scientific Area hint (biologicas, saude, exatas, engenharias, humanas).",
    )
    args = parser.parse_args()

    max_papers = max(1, min(25, args.max_papers))
    items: list[dict[str, Any]] = []
    if args.source != "all":
        sources = [args.source]
    else:
        resolved = resolve_area_code(args.area)
        if resolved and resolved in AREA_DEFINITIONS:
            sources = AREA_DEFINITIONS[resolved]["preferred_sources"]
        else:
            sources = ["openalex", "arxiv", "pubmed", "crossref"]

    per_source = max(3, (max_papers + len(sources) - 1) // len(sources))

    for src in sources:
        try:
            if src == "arxiv":
                items.extend(search_arxiv_api(args.query, max_papers=per_source, sort=args.sort))
            elif src == "openalex":
                items.extend(search_openalex(args.query, max_papers=per_source, sort=args.sort))
            elif src == "pubmed":
                items.extend(search_europepmc(args.query, max_papers=per_source))
            elif src == "crossref":
                items.extend(search_crossref(args.query, max_papers=per_source))
        except Exception as e:
            if len(sources) == 1:
                print(f"Error querying {src}: {e}")
                return 0

    deduped: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for it in items:
        norm = "".join(ch.lower() for ch in it["title"] if ch.isalnum())[:60]
        if norm and norm in seen_titles:
            continue
        seen_titles.add(norm)
        deduped.append(it)
        if len(deduped) >= max_papers:
            break

    print(format_results(deduped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
