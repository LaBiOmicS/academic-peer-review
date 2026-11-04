#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "reportlab>=4.0.0",
# ]
# ///
"""Deterministic post-processor and bundle compiler for academic-peer-review.

1. Reads all `review_<codename>.md` files in `<output_dir>` (Greek letter codenames:
   `alfa`, `beta`, `gamma`, `delta`, `epsilon`, `zeta`, `eta`, `theta`), extracting:
   - SSoT `SEED`, `LENS`/`AXIS`, and `STANCE`
   - Exact `Verdict` (Reject / Major revision / Minor revision / Accept) and justification
   - Cited external identifiers (`arXiv:...`, `DOI:...`, `PMID:...`)
2. Reads `<output_dir>/meta_review.md`, extracts the `CONCERNS_TABLE_DATA` JSON block,
   writes `<output_dir>/concerns_table.csv` and `<output_dir>/concerns_matrix.json`, and
   replaces the raw JSON block in `meta_review.md` with a clean Markdown matrix.
   Re-running is safe: once the JSON block has been consumed, the matrix is reloaded from
   `concerns_matrix.json` instead of being overwritten with an empty table.
   Each concern carries its severity tier and, per reviewer, whether it was raised as a major
   concern or only mentioned (``"major"`` / ``"minor"`` / ``""``).
3. Inserts the authoritative pre-review audit figures into the meta-review (between
   ``<!-- audit-figures:start -->`` markers) and warns when the meta-review was written against
   an older audit or contradicts its figures.
4. Writes ``author_letter.md``: the decision plus the Blocking and Essential roadmap items only.
5. Merges `<output_dir>/pre_review_audit.json` (if present) and writes `<output_dir>/results.json`.
6. Prints a compact per-reviewer verdict summary table to stdout.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arxiv_lookup import lookup_arxiv_ids, normalize_arxiv_id  # noqa: E402
from openalex_lookup import lookup_dois, normalize_doi  # noqa: E402

try:
    from generate_pdf_report import generate_pdf_report
except Exception as _pdf_import_error:  # noqa: BLE001 - PDF output is optional; never block compilation
    print(f"Notice: PDF report module unavailable ({_pdf_import_error}).", file=sys.stderr)
    generate_pdf_report = None


GREEK_ORDER = ["alfa", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]

# Matches "### Verdict\n**Major revision** — ..." as well as "### Verdict: Major revision" on one line.
VERDICT_REGEX = re.compile(
    r"(?:##+|\*\*)\s*(?:\d+\.\s*)?Verdict\b\**[ \t]*[:—-]?[ \t]*\**[ \t]*(?:\n+\s*(?:[-*]\s*)?)?"
    r"\*{0,2}(Reject|Major\s+revision|Minor\s+revision|Accept)\*{0,2}[.:—\s-]*(.*)",
    re.IGNORECASE,
)
VERDICT_LABEL_REGEX = re.compile(r"\b(Reject|Major\s+revision|Minor\s+revision|Accept)\b", re.IGNORECASE)
SEED_REGEX = re.compile(r"SEED:\s*([0-9a-fA-F]{16,64})")
LENS_REGEX = re.compile(r"(?:LENS|AXIS):\s*([^\n]+)")
STANCE_REGEX = re.compile(r"STANCE:\s*([^\n]+)")
CONCERNS_JSON_REGEX = re.compile(
    r"##+\s*CONCERNS_TABLE_DATA\s*\n+```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
# Reviewers cite DOIs as "DOI:10.x", "doi: 10.x", "https://doi.org/10.x" or a bare "10.x/...".
DOI_CITE_REGEX = re.compile(
    r"(?:\bdoi:\s*|https?://(?:dx\.)?doi\.org/|(?<![\w/.]))(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)",
    re.IGNORECASE,
)
ARXIV_CITE_REGEX = re.compile(
    r"(?:\barXiv:\s*|arxiv\.org/abs/)((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
PMID_CITE_REGEX = re.compile(r"\bPMID:?\s*(\d{6,9})\b", re.IGNORECASE)
FALLBACK_JSON_REGEX = re.compile(
    r"```json\s*(\{\s*\"concerns\"\s*:\s*\[.*?\]\s*\})\s*```",
    re.DOTALL,
)


# Seed arithmetic a reviewer may echo after its lens/stance ("(int(\"46\",16) = 70; 70 mod 6 = 4)").
SEED_ARITHMETIC_REGEX = re.compile(r"\s*[(\[—–-]*\s*(?:int\(|\d+\s*mod\s*\d|SEED\[).*$", re.IGNORECASE)


def _clean_label(value: str | None) -> str | None:
    """Strip echoed seed arithmetic and markdown emphasis from a LENS/STANCE value."""
    if not value:
        return None
    cleaned = SEED_ARITHMETIC_REGEX.sub("", value).strip(" *`")
    return cleaned or None


def parse_single_review(text: str) -> dict[str, Any]:
    seed_m = SEED_REGEX.search(text)
    lens_m = LENS_REGEX.search(text)
    stance_m = STANCE_REGEX.search(text)
    verdict_m = VERDICT_REGEX.search(text)

    verdict = "Unknown"
    verdict_reason = ""
    if verdict_m:
        raw_v = " ".join(verdict_m.group(1).split()).lower()
        verdict_map = {
            "reject": "Reject",
            "major revision": "Major revision",
            "minor revision": "Minor revision",
            "accept": "Accept",
        }
        verdict = verdict_map.get(raw_v, raw_v.capitalize())
        verdict_reason = verdict_m.group(2).strip().splitlines()[0] if verdict_m.group(2).strip() else ""
    else:
        # No Verdict heading: take the last verdict label mentioned near the end of the review.
        tail = "\n".join(text.splitlines()[-30:])
        labels = VERDICT_LABEL_REGEX.findall(tail)
        if labels:
            verdict = {
                "reject": "Reject",
                "major revision": "Major revision",
                "minor revision": "Minor revision",
                "accept": "Accept",
            }[" ".join(labels[-1].split()).lower()]

    cited_ids: set[str] = set()
    for m in ARXIV_CITE_REGEX.finditer(text):
        cited_ids.add(f"arXiv:{m.group(1)}")
    for m in DOI_CITE_REGEX.finditer(text):
        doi = normalize_doi(m.group(1))
        if doi:
            cited_ids.add(f"DOI:{doi}")
    for m in PMID_CITE_REGEX.finditer(text):
        cited_ids.add(f"PMID:{m.group(1)}")

    return {
        "seed": seed_m.group(1).strip() if seed_m else None,
        "lens_or_axis": _clean_label(lens_m.group(1)) if lens_m else None,
        "stance": _clean_label(stance_m.group(1)) if stance_m else None,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "external_citations": sorted(cited_ids),
        "char_count": len(text),
    }


def _sanitize_csv_cell(val: str) -> str:
    """Prevent CSV Formula / DDE Injection (OWASP CSV Injection mitigation)."""
    cleaned = " ".join(val.splitlines()).strip()
    if cleaned and cleaned[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + cleaned
    return cleaned


def manuscript_dois(paper_text: str) -> set[str]:
    """DOIs printed in the manuscript itself, normalized like reviewer citations."""
    return {d for m in DOI_CITE_REGEX.finditer(paper_text) if (d := normalize_doi(m.group(1)))}


def manuscript_arxiv_ids(paper_text: str) -> set[str]:
    """arXiv identifiers printed in the manuscript itself, normalized like reviewer citations."""
    return {a for m in ARXIV_CITE_REGEX.finditer(paper_text) if (a := normalize_arxiv_id(m.group(1)))}


def verify_reviewer_arxiv(
    reviewer_metadata: dict[str, Any], max_checks: int = 100, paper_arxiv: set[str] | None = None
) -> dict[str, Any]:
    """Check reviewer-cited arXiv IDs against the arXiv API; IDs quoted from the manuscript are skipped."""
    paper_arxiv = paper_arxiv or set()
    per_reviewer: dict[str, list[str]] = {}
    all_ids: list[str] = []
    for code, meta in reviewer_metadata.items():
        ids = sorted({
            a for c in meta.get("external_citations", [])
            if c.startswith("arXiv:") and (a := normalize_arxiv_id(c[6:])) and a not in paper_arxiv
        })
        if ids:
            per_reviewer[code] = ids
            all_ids.extend(ids)
    res = lookup_arxiv_ids(all_ids, max_checks=max_checks) if all_ids else {"found": {}, "unresolvable": [], "unchecked": []}
    flagged = {
        code: [f"arXiv:{a}" for a in ids if a in res["unresolvable"]]
        for code, ids in per_reviewer.items()
        if any(a in res["unresolvable"] for a in ids)
    }
    return {
        "arxiv_checked_count": len(res["found"]) + len(res["unresolvable"]),
        "verified_arxiv": [
            {"arxiv_id": a, "title": w.get("title") or "Untitled", "year": w.get("year")} for a, w in res["found"].items()
        ],
        "unresolvable_arxiv": res["unresolvable"],
        "unchecked_arxiv": res["unchecked"],
        "flagged": flagged,
    }


def verify_reviewer_citations(
    reviewer_metadata: dict[str, Any],
    max_checks: int = 100,
    paper_dois: set[str] | None = None,
    paper_arxiv: set[str] | None = None,
) -> dict[str, Any]:
    """Audit external DOIs (OpenAlex/doi.org) and arXiv IDs (arXiv API) cited by reviewers.

    DOIs and arXiv IDs that also appear in the manuscript are quotes of its reference list (often to
    point out a malformed DOI), not reviewer citations: they are reported separately and never flagged,
    since the pre-review audit already verifies the manuscript's own references. ``flagged_reviewers``
    lists bare DOIs and ``arXiv:``-prefixed IDs that could not be resolved.
    """
    paper_dois = paper_dois or set()
    reviewer_dois: dict[str, list[str]] = {}
    quoted_from_manuscript: dict[str, list[str]] = {}
    all_dois: list[str] = []

    for code, meta in reviewer_metadata.items():
        c_dois = sorted({c[4:] for c in meta.get("external_citations", []) if c.startswith("DOI:")})
        quoted = [d for d in c_dois if d in paper_dois]
        c_dois = [d for d in c_dois if d not in paper_dois]
        if quoted:
            quoted_from_manuscript[code] = quoted
        if c_dois:
            reviewer_dois[code] = c_dois
            all_dois.extend(c_dois)

    res = lookup_dois(all_dois, max_checks=max_checks)
    verified = [
        {"doi": doi, "title": work.get("title") or "Untitled", "year": work.get("publication_year")}
        for doi, work in res["found"].items()
    ]
    unresolvable = res["unresolvable"]

    hallucinating_reviewers: dict[str, list[str]] = {}
    for code, dois in reviewer_dois.items():
        hallucinated_hits = [d for d in dois if d in unresolvable]
        if hallucinated_hits:
            hallucinating_reviewers[code] = hallucinated_hits

    arxiv_audit = verify_reviewer_arxiv(reviewer_metadata, max_checks=max_checks, paper_arxiv=paper_arxiv)
    for code, ids in arxiv_audit.pop("flagged").items():
        hallucinating_reviewers.setdefault(code, []).extend(ids)

    return {
        "dois_checked_count": len(res["found"]) + len(unresolvable),
        "verified_citations": verified,
        "unresolvable_dois": unresolvable,
        "unchecked_dois": res["unchecked"],
        "flagged_reviewers": hallucinating_reviewers,
        "manuscript_dois_quoted": quoted_from_manuscript,
        **arxiv_audit,
    }


SEVERITY_TIERS = ("blocking", "essential", "optional")


def concern_cell(val: Any) -> str:
    """Normalize one reviewer cell to "major", "minor" or "" (legacy booleans: true -> major)."""
    if isinstance(val, bool):
        return "major" if val else ""
    text = str(val or "").strip().lower()
    if text in ("major", "true", "1", "yes", "x", "✓"):
        return "major"
    if text in ("minor", "mentioned", "partial", "~"):
        return "minor"
    return ""


def _normalize_concern_rows(raw_items: list[Any], codenames: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {"concern": " ".join(str(item.get("concern", "")).splitlines()).strip()}
        severity = str(item.get("severity") or "").strip().lower()
        row["severity"] = severity if severity in SEVERITY_TIERS else ""
        for code in codenames:
            row[code] = concern_cell(item.get(code, ""))
        if row["concern"]:
            rows.append(row)
    return rows


def _write_concerns_csv(rows: list[dict[str, Any]], codenames: list[str], csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["concern", "severity"] + codenames)
        writer.writeheader()
        for row in rows:
            csv_row = {"concern": _sanitize_csv_cell(row["concern"]), "severity": row.get("severity", "")}
            csv_row.update({code: row[code] for code in codenames})
            writer.writerow(csv_row)


def _load_previous_concerns(json_path: Path, csv_path: Path) -> list[Any]:
    """Recover the matrix from an earlier run (concerns_matrix.json, else concerns_table.csv)."""
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except ValueError:
            pass
    if csv_path.exists():
        try:
            with open(csv_path, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            for r in rows:
                if r.get("concern", "").startswith("'"):
                    r["concern"] = r["concern"][1:]
            return rows
        except (OSError, csv.Error):
            pass
    return []


CELL_MARKS = {"major": "✓", "minor": "(m)", "": "·"}


def _concerns_markdown(rows: list[dict[str, Any]], codenames: list[str]) -> str:
    # Reviewers share one model, so the count is attribution, not corroboration: the legend says so.
    lines = [
        "## Major Concerns Matrix",
        "",
        "✓ = raised as a major concern; (m) = mentioned only in passing or as a minor point. "
        "Reviewers share one underlying model, so agreement is attribution, not independent corroboration.",
        "",
        "| Concern | Tier | " + " | ".join(codenames) + " | Raised as major |",
        "|---|:---:|" + "|".join([":---:" for _ in codenames]) + "|:---:|",
    ]
    for r in rows:
        marks = [CELL_MARKS[r[c]] for c in codenames]
        count = sum(1 for c in codenames if r[c] == "major")
        safe_concern = r["concern"].replace("|", "\\|")
        tier = (r.get("severity") or "—").capitalize()
        lines.append(f"| {safe_concern} | {tier} | " + " | ".join(marks) + f" | {count}/{len(codenames)} |")
    return "\n".join(lines) + "\n"


def extract_and_clean_concerns(
    meta_text: str, codenames: list[str], csv_path: Path, json_path: Path | None = None
) -> tuple[str, list[dict[str, Any]]]:
    """Parse CONCERNS_TABLE_DATA, write CSV/JSON, and swap the raw JSON for a Markdown matrix.

    When the block was already consumed by a previous run, the matrix is reloaded from
    ``json_path`` / ``csv_path`` and ``meta_text`` is returned unchanged.
    """
    json_path = json_path or csv_path.with_name("concerns_matrix.json")
    match = CONCERNS_JSON_REGEX.search(meta_text) or FALLBACK_JSON_REGEX.search(meta_text)

    if not match:
        rows = _normalize_concern_rows(_load_previous_concerns(json_path, csv_path), codenames)
        _write_concerns_csv(rows, codenames, csv_path)
        return meta_text, rows

    raw_items: list[Any] = []
    try:
        parsed = json.loads(match.group(1))
        raw_items = parsed.get("concerns", []) if isinstance(parsed, dict) else []
    except ValueError as e:
        print(f"[compile_results] Warning: Failed to parse CONCERNS_TABLE_DATA JSON: {e}", file=sys.stderr)
        # Keep the raw block in place so the data is not lost; nothing to rewrite.
        rows = _normalize_concern_rows(_load_previous_concerns(json_path, csv_path), codenames)
        _write_concerns_csv(rows, codenames, csv_path)
        return meta_text, rows

    rows = _normalize_concern_rows(raw_items, codenames)
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_concerns_csv(rows, codenames, csv_path)

    cleaned_meta = meta_text[: match.start()].rstrip()
    if rows:
        cleaned_meta += "\n\n" + _concerns_markdown(rows, codenames)
    suffix = meta_text[match.end() :].strip()
    if suffix:
        cleaned_meta += "\n" + suffix + "\n"
    return cleaned_meta, rows


AUDIT_SECTION = "## Statistical, Provenance & Reproducibility Audit Highlights"
AUDIT_START = "<!-- audit-figures:start -->"
AUDIT_END = "<!-- audit-figures:end -->"
AUDIT_BLOCK_REGEX = re.compile(re.escape(AUDIT_START) + r".*?" + re.escape(AUDIT_END) + r"\n?", re.DOTALL)
RISK_REGEX = re.compile(r"\b(Low|Moderate|High|Critical)\s+(?:desk[- ]reject(?:ion)?\s+)?Risk\b", re.IGNORECASE)
ADHERENCE_PCT_REGEX = re.compile(
    r"(\d{1,3})\s*%[^.\n]{0,40}\b(?:adherence|fit|scope)\b|\b(?:adherence|fit|scope)\b[^.\n]{0,40}?(\d{1,3})\s*%",
    re.IGNORECASE,
)


def audit_figures_lines(pre_audit: dict[str, Any]) -> list[str]:
    """Authoritative audit figures, rendered from pre_review_audit.json."""
    lines: list[str] = []
    scope = pre_audit.get("journal_scope_audit") or {}
    if scope:
        score = scope.get("adherence_score_pct")
        lines.append(
            f"- **Journal scope ({scope.get('target_journal') or 'target journal'})**: "
            f"{score if score is not None else 'n/a'}% adherence, {scope.get('fit_category') or 'n/a'}; "
            f"desk-reject risk: {scope.get('desk_reject_risk') or 'n/a'} (automated estimate)."
        )
    cit = pre_audit.get("citation_audit") or {}
    if cit:
        lines.append(
            f"- **Manuscript DOIs**: {cit.get('verified_count', 0)} of {cit.get('checked_count', 0)} resolved; "
            f"{len(cit.get('unresolvable_dois') or [])} unresolvable; {len(cit.get('retracted_works') or [])} retracted."
        )
    stat = pre_audit.get("statcheck") or {}
    if stat:
        lines.append(
            f"- **Statistical recalculation**: {stat.get('tests_checked', 0)} tests checked; "
            f"{stat.get('inconsistencies_count', 0)} inconsistencies; {stat.get('decision_errors_count', 0)} decision errors."
        )
    ai = pre_audit.get("ai_provenance_audit") or {}
    if ai:
        lines.append(
            f"- **AI provenance**: disclosure {'present' if ai.get('has_ai_disclosure') else 'absent'}; "
            f"{ai.get('uncleaned_llm_artifacts_count', 0)} uncleaned LLM artifacts."
        )
    fair = pre_audit.get("reproducibility_and_fair_audit") or {}
    if fair.get("data_status"):
        lines.append(f"- **Data/code availability**: {fair['data_status']}.")
    return lines


def inject_audit_figures(meta_text: str, pre_audit: dict[str, Any] | None) -> str:
    """Insert (or refresh) the audit-figures block at the end of the audit-highlights section."""
    meta_text = AUDIT_BLOCK_REGEX.sub("", meta_text)
    lines = audit_figures_lines(pre_audit or {})
    if not lines or AUDIT_SECTION not in meta_text:
        return meta_text
    block = "\n".join([AUDIT_START, "", "**Audit figures (from the automated audit file):**", "", *lines, "", AUDIT_END]) + "\n"
    start = meta_text.index(AUDIT_SECTION) + len(AUDIT_SECTION)
    nxt = meta_text.find("\n## ", start)
    end = len(meta_text) if nxt == -1 else nxt + 1
    body = meta_text[start:end].rstrip("\n")
    return meta_text[:start] + body + "\n\n" + block + ("\n" if nxt != -1 else "") + meta_text[end:]


def audit_consistency_warnings(
    meta_text: str, pre_audit: dict[str, Any] | None, meta_mtime: float | None = None, audit_mtime: float | None = None
) -> list[str]:
    """Flag a meta-review written against an older audit, or prose contradicting the audit figures."""
    warnings: list[str] = []
    if meta_mtime is not None and audit_mtime is not None and audit_mtime > meta_mtime + 1:
        warnings.append(
            "pre_review_audit was regenerated after meta_review.md was written; re-check the meta-review against it."
        )
    scope = (pre_audit or {}).get("journal_scope_audit") or {}
    if not scope:
        return warnings
    prose = AUDIT_BLOCK_REGEX.sub("", meta_text)
    score = scope.get("adherence_score_pct")
    if score is not None:
        quoted = {int(a or b) for a, b in ADHERENCE_PCT_REGEX.findall(prose)}
        wrong = sorted(q for q in quoted if q != int(score))
        if wrong:
            warnings.append(
                f"meta-review cites a scope adherence of {', '.join(f'{w}%' for w in wrong)}, but the audit reports {score}%."
            )
    risk = str(scope.get("desk_reject_risk") or "")
    risk_level = risk.split()[0].lower() if risk else ""
    if risk_level:
        mentioned = {m.lower() for m in RISK_REGEX.findall(prose)}
        if mentioned and risk_level not in mentioned:
            warnings.append(
                f"meta-review describes the automated desk-reject risk as {', '.join(sorted(mentioned))}, "
                f"but the audit reports '{risk}'."
            )
    return warnings


ROADMAP_SECTION_REGEX = re.compile(r"^##\s+Actionable Revision Roadmap\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
TIER_HEADING_REGEX = re.compile(r"^\s*\d+\.\s*\*\*([^*]+)\*\*.*$", re.MULTILINE)
VERDICT_SECTION_REGEX = re.compile(r"^##\s+Verdict synthesis\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)


def roadmap_tiers(meta_text: str) -> list[tuple[str, str]]:
    """Split the roadmap into (tier heading, body) pairs, in document order."""
    m = ROADMAP_SECTION_REGEX.search(meta_text)
    if not m:
        return []
    section = m.group(1)
    heads = list(TIER_HEADING_REGEX.finditer(section))
    tiers = []
    for i, h in enumerate(heads):
        body_end = heads[i + 1].start() if i + 1 < len(heads) else len(section)
        tiers.append((h.group(1).strip(), section[h.end() : body_end].strip("\n")))
    return tiers


def _tier_key(heading: str) -> str:
    head = heading.lower()
    if head.startswith("blocking"):
        return "blocking"
    if head.startswith("essential"):
        return "essential"
    return "optional"


def build_author_letter(meta_text: str, consensus: str) -> str | None:
    """Short author-facing letter: the decision, its rationale and the Blocking/Essential items only."""
    tiers = roadmap_tiers(meta_text)
    if not tiers:
        return None
    verdict_m = VERDICT_SECTION_REGEX.search(meta_text)
    rationale = verdict_m.group(1).strip() if verdict_m else ""
    decision_m = VERDICT_LABEL_REGEX.search(rationale)
    decision = " ".join(decision_m.group(1).split()).capitalize() if decision_m else consensus
    out = ["# Decision letter to the authors", "", f"**Editorial recommendation: {decision}**", ""]
    if rationale:
        out += [rationale, ""]
    optional_items = 0
    for heading, body in tiers:
        if _tier_key(heading) == "optional":
            optional_items += len(re.findall(r"^\s*[-*]\s", body, re.MULTILINE))
            continue
        out += [f"## {heading}", "", textwrap.dedent(body.strip("\n")).strip(), ""]
    if optional_items:
        out += [
            f"*{optional_items} optional suggestion(s) are listed in the full editorial report. "
            "The authors may decline any of them with a one-line justification.*",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"


MAX_BLOCKING = 5
MAJOR_SECTION_REGEX = re.compile(r"^###\s+Major concerns\s*$(.*?)(?=^###\s|\Z)", re.MULTILINE | re.DOTALL)
CONCERN_ITEM_REGEX = re.compile(r"^\s{0,3}\d+\.\s+\S", re.MULTILINE)
SEVERITY_TAG_REGEX = re.compile(r"Severity\W{0,12}?(Blocking|Essential|Optional)\b", re.IGNORECASE)


def review_contract(text: str) -> dict[str, Any]:
    """Count Major concerns and their severity tags; list breaches of the severity contract."""
    m = MAJOR_SECTION_REGEX.search(text)
    section = m.group(1) if m else ""
    starts = [x.start() for x in CONCERN_ITEM_REGEX.finditer(section)] + [len(section)]
    tiers: list[str | None] = []
    for a, b in zip(starts, starts[1:], strict=False):
        tag = SEVERITY_TAG_REGEX.search(section[a:b])
        tiers.append(tag.group(1).lower() if tag else None)
    counts = {t: tiers.count(t) for t in SEVERITY_TIERS}
    issues: list[str] = []
    if not m:
        issues.append("no '### Major concerns' section")
    untagged = tiers.count(None)
    if untagged:
        issues.append(f"{untagged} of {len(tiers)} major concerns have no severity tier")
    if counts["blocking"] > MAX_BLOCKING:
        issues.append(f"{counts['blocking']} Blocking concerns (limit {MAX_BLOCKING})")
    return {"major_concerns": len(tiers), "severity_counts": counts, "untagged": untagged, "issues": issues}


def meta_contract(meta_text: str, concerns: list[dict[str, Any]]) -> list[str]:
    """Breaches of the meta-review contract: verification table, three-tier roadmap, tiered matrix."""
    issues: list[str] = []
    if not re.search(r"^##\s+Blocking-concern verification\s*$", meta_text, re.MULTILINE):
        issues.append("no '## Blocking-concern verification' section")
    tiers = roadmap_tiers(meta_text)
    keys = [_tier_key(h) for h, _ in tiers]
    heads = [h.lower() for h, _ in tiers]
    if not tiers:
        issues.append("no '## Actionable Revision Roadmap' tiers")
    elif not (any(h.startswith("blocking") for h in heads) and any(h.startswith("essential") for h in heads)
              and any(h.startswith("optional") for h in heads)):
        issues.append("roadmap does not use the Blocking / Essential / Optional tiers")
    for (_, body), key in zip(tiers, keys, strict=True):
        if key == "blocking":
            n = len(re.findall(r"^\s*[-*]\s", body, re.MULTILINE))
            if n > MAX_BLOCKING:
                issues.append(f"roadmap lists {n} Blocking items (limit {MAX_BLOCKING})")
    if concerns and any(not c.get("severity") for c in concerns):
        issues.append("concerns matrix has rows without a severity tier")
    return issues


def compute_consensus_verdict(verdicts: list[str]) -> str:
    valid = [v for v in verdicts if v != "Unknown"]
    if not valid:
        return "Unknown"
    counts = Counter(valid)
    severity = {"Reject": 4, "Major revision": 3, "Minor revision": 2, "Accept": 1}
    return sorted(counts.items(), key=lambda kv: (kv[1], severity.get(kv[0], 0)), reverse=True)[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile peer review outputs into CSV and results.json.")
    parser.add_argument("--output-dir", required=True, help="Directory containing review_*.md and meta_review.md.")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip compiling the standardized PDF report.")
    parser.add_argument(
        "--no-ai-disclosure",
        action="store_true",
        help="Omit the AI-assistance disclosure from the PDF report (the referee handles disclosure).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    if not out_dir.exists():
        print(f"Error: Output directory not found: {out_dir}", file=sys.stderr)
        return 1

    individual_reviews: dict[str, str] = {}
    reviewer_metadata: dict[str, Any] = {}
    reviewer_mapping: dict[str, str] = {}

    manifest_path = out_dir / ".prompts" / "panel_manifest.json"
    manifest_data: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # With a panel manifest, only its reviewers count: review files left over from an earlier,
    # larger panel in the same directory must not leak into the verdicts and consensus.
    panel_codes = set((manifest_data.get("reviewers") or {}).keys())
    for idx, code in enumerate(GREEK_ORDER, start=1):
        rev_file = out_dir / f"review_{code}.md"
        if not rev_file.exists():
            continue
        if panel_codes and code not in panel_codes:
            print(f"[compile_results] Ignoring {rev_file.name}: not part of the current panel manifest.", file=sys.stderr)
            continue
        text = rev_file.read_text(encoding="utf-8", errors="replace")
        individual_reviews[code] = text
        parsed_meta = parse_single_review(text)
        archetype = (
            manifest_data.get("reviewers", {}).get(code, {}).get("archetype")
            or f"reviewer-{idx}"
        )
        parsed_meta["archetype"] = archetype
        rev_manifest = manifest_data.get("reviewers", {}).get(code, {})
        parsed_meta["runner"] = rev_manifest.get("runner")
        parsed_meta["model"] = rev_manifest.get("model")
        parsed_meta["contract"] = review_contract(text)
        reviewer_metadata[code] = parsed_meta
        reviewer_mapping[code] = f"reviewer-{idx} ({archetype})"

    codenames = list(individual_reviews.keys())
    if not codenames:
        print(f"Error: No review_<codename>.md files found in {out_dir}", file=sys.stderr)
        return 1

    meta_path = out_dir / "meta_review.md"
    csv_path = out_dir / "concerns_table.csv"
    cleaned_meta = ""
    concerns_matrix: list[dict[str, Any]] = []

    pre_audit = None
    audit_path = out_dir / "pre_review_audit.json"
    audit_sha256 = None
    if audit_path.exists():
        try:
            audit_bytes = audit_path.read_bytes()
            audit_sha256 = hashlib.sha256(audit_bytes).hexdigest()
            pre_audit = json.loads(audit_bytes.decode("utf-8"))
        except Exception:
            pass

    audit_warnings: list[str] = []
    if meta_path.exists():
        raw_meta = meta_path.read_text(encoding="utf-8", errors="replace")
        # A meta-review compiled before already carries the audit block, so its mtime is ours, not the LLM's.
        first_compile = AUDIT_START not in raw_meta
        audit_warnings = audit_consistency_warnings(
            raw_meta,
            pre_audit,
            meta_mtime=meta_path.stat().st_mtime if first_compile else None,
            audit_mtime=audit_path.stat().st_mtime if audit_path.exists() else None,
        )
        cleaned_meta, concerns_matrix = extract_and_clean_concerns(raw_meta, codenames, csv_path)
        cleaned_meta = inject_audit_figures(cleaned_meta, pre_audit)
        if cleaned_meta != raw_meta:
            meta_path.write_text(cleaned_meta, encoding="utf-8")

    verdicts_list = [reviewer_metadata[c]["verdict"] for c in codenames]
    consensus = compute_consensus_verdict(verdicts_list)
    paper_text_path = out_dir / "paper_text.txt"
    paper_text = paper_text_path.read_text(encoding="utf-8", errors="replace") if paper_text_path.exists() else ""
    reviewer_citation_audit = verify_reviewer_citations(
        reviewer_metadata, paper_dois=manuscript_dois(paper_text), paper_arxiv=manuscript_arxiv_ids(paper_text)
    )

    contract_issues: dict[str, list[str]] = {
        code: meta["contract"]["issues"] for code, meta in reviewer_metadata.items() if meta["contract"]["issues"]
    }
    if cleaned_meta:
        meta_issues = meta_contract(cleaned_meta, concerns_matrix)
        if meta_issues:
            contract_issues["meta_review"] = meta_issues
    panel_models = sorted({f"{m.get('runner') or 'default'}:{m.get('model') or 'default'}" for m in reviewer_metadata.values()})

    author_letter = build_author_letter(cleaned_meta, consensus) if cleaned_meta else None
    if author_letter:
        (out_dir / "author_letter.md").write_text(author_letter, encoding="utf-8")

    results_payload = {
        "individual_reviews": individual_reviews,
        "meta_review": cleaned_meta,
        "reviewer_mapping": reviewer_mapping,
        "reviewer_metadata": reviewer_metadata,
        "verdict_summary": {
            "per_reviewer": {c: reviewer_metadata[c]["verdict"] for c in codenames},
            "consensus": consensus,
        },
        "concerns_matrix": concerns_matrix,
        "pre_review_audit": pre_audit,
        "reviewer_citation_audit": reviewer_citation_audit,
        "audit_provenance": {"pre_review_audit_sha256": audit_sha256, "warnings": audit_warnings},
        "severity_contract": {"issues": contract_issues, "panel_models": panel_models, "single_model_panel": len(panel_models) == 1},
    }

    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(results_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for c in codenames:
        v = reviewer_metadata[c]["verdict"]
        lens = reviewer_metadata[c].get("lens_or_axis") or ""
        lens_suffix = f" [{lens}]" if lens else ""
        print(f"{c:<8} — {v}{lens_suffix}")
    print("---")
    print(f"Consensus: {consensus}")

    if reviewer_citation_audit.get("flagged_reviewers"):
        print("\n⚠️  CITATION HALLUCINATION ALERT:")
        for r_code, h_dois in reviewer_citation_audit["flagged_reviewers"].items():
            print(f"  - Reviewer '{r_code}' cited unresolvable/hallucinated identifier(s): {', '.join(h_dois)}")

    if contract_issues:
        print("\n⚠️  SEVERITY CONTRACT NOT MET:")
        for who, issues in contract_issues.items():
            for issue in issues:
                print(f"  - {who}: {issue}")

    if audit_warnings:
        print("\n⚠️  META-REVIEW / AUDIT MISMATCH:")
        for w in audit_warnings:
            print(f"  - {w}")

    if not args.skip_pdf and generate_pdf_report:
        try:
            generate_pdf_report(out_dir, ai_disclosure=not args.no_ai_disclosure)
        except Exception as e:
            print(f"Notice: Automatic PDF generation encountered: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
