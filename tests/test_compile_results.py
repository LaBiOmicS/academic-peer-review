from __future__ import annotations

import csv
import json
import sys

import compile_results
from compile_results import parse_single_review

REVIEW = """SEED: {seed}
LENS: Statistics

## Summary
A paper. See DOI:10.1038/nature12373 and https://doi.org/10.1093/bioinformatics/btp324.
Also doi: 10.1101/2020.01.01.123456 and arXiv:2301.12345v2 and PMID: 12345678.
p = 2023.12345

### Verdict
{verdict} — reasons here.
"""

META = """## Per-reviewer verdicts
- **alfa** — Major revision

## CONCERNS_TABLE_DATA

```json
{"concerns": [
  {"concern": "=HYPERLINK(\\"x\\") sample size too small | underpowered", "alfa": true, "beta": false},
  {"concern": "No code availability", "alfa": true, "beta": true}
]}
```
"""


def test_parse_single_review_extracts_all_doi_styles():
    meta = parse_single_review(REVIEW.format(seed="a" * 32, verdict="Major revision"))
    assert meta["verdict"] == "Major revision"
    assert "DOI:10.1038/nature12373" in meta["external_citations"]
    assert "DOI:10.1093/bioinformatics/btp324" in meta["external_citations"]
    assert "DOI:10.1101/2020.01.01.123456" in meta["external_citations"]
    assert "arXiv:2301.12345v2" in meta["external_citations"]
    assert "PMID:12345678" in meta["external_citations"]
    # bare numbers are no longer mistaken for arXiv IDs
    assert not any("2023.12345" in c for c in meta["external_citations"])


def _run(out_dir, monkeypatch):
    monkeypatch.setattr(
        compile_results,
        "lookup_dois",
        lambda dois, max_checks=100: {"found": {}, "unresolvable": ["10.1038/nature12373"], "unchecked": [], "invalid": []},
    )
    monkeypatch.setattr(sys, "argv", ["compile_results.py", "--output-dir", str(out_dir), "--skip-pdf"])
    assert compile_results.main() == 0
    return json.loads((out_dir / "results.json").read_text(encoding="utf-8"))


def test_compile_is_idempotent(tmp_path, monkeypatch):
    (tmp_path / "review_alfa.md").write_text(REVIEW.format(seed="a" * 32, verdict="Major revision"), encoding="utf-8")
    (tmp_path / "review_beta.md").write_text(REVIEW.format(seed="b" * 32, verdict="Reject"), encoding="utf-8")
    (tmp_path / "meta_review.md").write_text(META, encoding="utf-8")

    first = _run(tmp_path, monkeypatch)
    assert len(first["concerns_matrix"]) == 2
    meta_after_first = (tmp_path / "meta_review.md").read_text(encoding="utf-8")
    assert "CONCERNS_TABLE_DATA" not in meta_after_first
    assert "## Major Concerns Matrix" in meta_after_first

    # Regression: a second run used to wipe the matrix and the CSV.
    second = _run(tmp_path, monkeypatch)
    assert second["concerns_matrix"] == first["concerns_matrix"]
    assert (tmp_path / "meta_review.md").read_text(encoding="utf-8") == meta_after_first

    with open(tmp_path / "concerns_table.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["concern"].startswith("'=")  # CSV formula injection neutralized
    assert second["reviewer_citation_audit"]["flagged_reviewers"] == {
        "alfa": ["10.1038/nature12373"],
        "beta": ["10.1038/nature12373"],
    }


def test_verdict_variants():
    cases = {
        "### Verdict\n**Major revision** — weak stats.": "Major revision",
        "### Verdict: Minor revision. Fine.": "Minor revision",
        "**Verdict**: Reject — fabricated data.": "Reject",
        "We do not reject the null.\nFinal recommendation: Minor revision": "Minor revision",
    }
    for text, expected in cases.items():
        assert parse_single_review(text)["verdict"] == expected, text


def test_stale_reviews_outside_manifest_are_ignored(tmp_path, monkeypatch):
    (tmp_path / ".prompts").mkdir()
    (tmp_path / ".prompts" / "panel_manifest.json").write_text(
        json.dumps({"reviewers": {"alfa": {"archetype": "domain-reviewer"}, "beta": {"archetype": "domain-reviewer"}}}),
        encoding="utf-8",
    )
    for code, verdict in (("alfa", "Accept"), ("beta", "Accept"), ("gamma", "Reject"), ("delta", "Reject"), ("zeta", "Reject")):
        (tmp_path / f"review_{code}.md").write_text(REVIEW.format(seed="c" * 32, verdict=verdict), encoding="utf-8")
    results = _run(tmp_path, monkeypatch)
    assert set(results["verdict_summary"]["per_reviewer"]) == {"alfa", "beta"}
    assert results["verdict_summary"]["consensus"] == "Accept"


def test_seed_arithmetic_is_stripped_from_lens_and_stance():
    # Regression (real run): "LENS: Algorithmic & numerical reproducibility (int("46",16) = 70; 70 mod 6 = 4)"
    # leaked the internal seed mechanics into the PDF panel table.
    from compile_results import parse_single_review

    meta = parse_single_review(
        'SEED: 46ab12cd34ef5678\nLENS: Algorithmic & numerical reproducibility (int("46",16) = 70; 70 mod 6 = 4)\n'
        "STANCE: Adversarial — int(SEED[2:4], 16) mod 3 = 1\n\n### Verdict\n**Reject** — x.\n"
    )
    assert meta["lens_or_axis"] == "Algorithmic & numerical reproducibility"
    assert meta["stance"] == "Adversarial"
