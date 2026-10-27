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
3. Merges `<output_dir>/pre_review_audit.json` (if present) and writes `<output_dir>/results.json`.
4. Prints a compact per-reviewer verdict summary table to stdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def verify_reviewer_citations(reviewer_metadata: dict[str, Any], max_checks: int = 100) -> dict[str, Any]:
    """Audit external DOIs cited by reviewers (batched OpenAlex lookup) to detect hallucinated references."""
    reviewer_dois: dict[str, list[str]] = {}
    all_dois: list[str] = []

    for code, meta in reviewer_metadata.items():
        c_dois = sorted({c[4:] for c in meta.get("external_citations", []) if c.startswith("DOI:")})
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

    return {
        "dois_checked_count": len(res["found"]) + len(unresolvable),
        "verified_citations": verified,
        "unresolvable_dois": unresolvable,
        "unchecked_dois": res["unchecked"],
        "flagged_reviewers": hallucinating_reviewers,
    }


def _normalize_concern_rows(raw_items: list[Any], codenames: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {"concern": " ".join(str(item.get("concern", "")).splitlines()).strip()}
        for code in codenames:
            val = item.get(code, False)
            if isinstance(val, str):
                val = val.strip().lower() in ("true", "1", "yes", "x", "✓")
            row[code] = bool(val)
        if row["concern"]:
            rows.append(row)
    return rows


def _write_concerns_csv(rows: list[dict[str, Any]], codenames: list[str], csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["concern"] + codenames)
        writer.writeheader()
        for row in rows:
            csv_row = {"concern": _sanitize_csv_cell(row["concern"])}
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


def _concerns_markdown(rows: list[dict[str, Any]], codenames: list[str]) -> str:
    lines = [
        "## Major Concerns Matrix",
        "",
        "| Major Concern | " + " | ".join(codenames) + " | Total |",
        "|---|" + "|".join([":---:" for _ in codenames]) + "|:---:|",
    ]
    for r in rows:
        marks = ["✓" if r[c] else "·" for c in codenames]
        count = sum(1 for c in codenames if r[c])
        safe_concern = r["concern"].replace("|", "\\|")
        lines.append(f"| {safe_concern} | " + " | ".join(marks) + f" | {count}/{len(codenames)} |")
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

    if meta_path.exists():
        raw_meta = meta_path.read_text(encoding="utf-8", errors="replace")
        cleaned_meta, concerns_matrix = extract_and_clean_concerns(raw_meta, codenames, csv_path)
        if cleaned_meta != raw_meta:
            meta_path.write_text(cleaned_meta, encoding="utf-8")

    pre_audit = None
    audit_path = out_dir / "pre_review_audit.json"
    if audit_path.exists():
        try:
            pre_audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    verdicts_list = [reviewer_metadata[c]["verdict"] for c in codenames]
    consensus = compute_consensus_verdict(verdicts_list)
    reviewer_citation_audit = verify_reviewer_citations(reviewer_metadata)

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
            print(f"  - Reviewer '{r_code}' cited unresolvable/hallucinated DOI(s): {', '.join(h_dois)}")

    if not args.skip_pdf and generate_pdf_report:
        try:
            generate_pdf_report(out_dir)
        except Exception as e:
            print(f"Notice: Automatic PDF generation encountered: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
