from __future__ import annotations

import json

import pytest

from generate_pdf_report import (
    AI_ASSISTANCE_NOTICE,
    _layout_tables_for_latex,
    assemble_consolidated_markdown,
    render_with_reportlab,
)


def _make_bundle(tmp_path):
    (tmp_path / "results.json").write_text(
        json.dumps(
            {
                "verdict_summary": {"consensus": "Major revision"},
                "reviewer_metadata": {"alfa": {"verdict": "Reject", "lens_or_axis": "A | B", "external_citations": ["DOI:10.1/x"]}},
                "reviewer_citation_audit": {"flagged_reviewers": {"alfa": ["10.1/x"]}},
                "pre_review_audit": {
                    "scientific_area": {"area_code": "saude", "area_name": "Saúde"},
                    "journal_scope_audit": {
                        "target_journal": "The Lancet",
                        "adherence_score_pct": 10,
                        "fit_category": "Out of Scope",
                        "desk_reject_risk": "Critical Desk-Reject Risk",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "meta_review.md").write_text(
        "## Verdict synthesis\nMajor revision for p < 0.05 & n > 30 with **bold** and `code` 🔴 ✓\n", encoding="utf-8"
    )
    (tmp_path / "concerns_table.csv").write_text("concern,alfa\n'=x | y,True\n", encoding="utf-8")
    (tmp_path / "pre_review_audit.md").write_text("### ⚠️ Critical Desk-Reject Red Flags\n- 🔴 **Flag** <tag>\n", encoding="utf-8")
    (tmp_path / "review_alfa.md").write_text("### Verdict\nReject — a < b & c.\n", encoding="utf-8")


def test_assembled_markdown_is_well_formed(tmp_path):
    _make_bundle(tmp_path)
    md, _ = assemble_consolidated_markdown(tmp_path)
    assert "The Lancet" in md
    assert "verified |" not in md  # citation counts are not labelled as verified
    assert "1 cited | 1 |" in md
    assert AI_ASSISTANCE_NOTICE in md
    assert "🔴" not in md and "✓" not in md and "⚠" not in md
    assert "A \\| B" in md  # pipes escaped inside table cells
    assert "| =x \\| y | X |" in md


def test_ai_disclosure_can_be_omitted(tmp_path):
    _make_bundle(tmp_path)
    md, _ = assemble_consolidated_markdown(tmp_path, ai_disclosure=False)
    assert AI_ASSISTANCE_NOTICE not in md
    assert "AI-assisted draft" not in md
    assert "author: 'Editorial Review Panel'" in md


def test_reportlab_fallback_handles_markup_and_front_matter(tmp_path):
    pytest.importorskip("reportlab")
    _make_bundle(tmp_path)
    md, results = assemble_consolidated_markdown(tmp_path)
    out = tmp_path / "report.pdf"
    assert render_with_reportlab(md, out, results)
    assert out.stat().st_size > 1000


def test_pdflatex_transliteration_keeps_accents():
    from generate_pdf_report import _pdflatex_safe

    out = _pdflatex_safe("Decision errors at α = 0.05; χ² ≤ 3 — Saúde, revisión")
    assert out == "Decision errors at alpha = 0.05; chi^2 <= 3 — Saúde, revisión"


def test_concerns_matrix_rendered_once_and_bad_dois_listed(tmp_path):
    _make_bundle(tmp_path)
    (tmp_path / "meta_review.md").write_text(
        "## Verdict synthesis\nMajor revision.\n\n## Major Concerns Matrix\n\n"
        "| Major Concern | alfa | Total |\n|---|:---:|:---:|\n| Data | ✓ | 1/1 |\n\n## Ranking\nalfa first.\n",
        encoding="utf-8",
    )
    md, _ = assemble_consolidated_markdown(tmp_path)
    assert "Major Concerns Matrix" in md  # Part II heading
    assert md.count("| Data |") == 0  # the meta-review copy is gone; Part II comes from the CSV
    assert "alfa first." in md  # content after the matrix is kept
    assert "Reviewer Alfa: `10.1/x`" in md


def test_rule_followed_by_text_does_not_open_yaml_block(tmp_path):
    # Regression: a review ending in "---\n*This report is…*" made pandoc parse a YAML block and
    # fail with "Unknown alias `This`".
    _make_bundle(tmp_path)
    (tmp_path / "review_alfa.md").write_text("### Verdict\nReject.\n\n---\n*This report is a draft.*\n", encoding="utf-8")
    md, _ = assemble_consolidated_markdown(tmp_path)
    body = md.split("# Part IV", 1)[1]
    assert "---\n*This" not in body and "---\n\n*This report is a draft.*" in body


def test_italic_inside_bold_nests_and_bad_markup_does_not_abort(tmp_path):
    from generate_pdf_report import _inline_markup

    assert _inline_markup("**Fit with *Ecología Austral***") == "<b>Fit with <i>Ecología Austral</i></b>"
    pytest.importorskip("reportlab")
    out = tmp_path / "r.pdf"
    md = "# T\n\n- **Fit with *Journal***: ok\n- a **b *c** d*\n" + "text\n" * 50
    assert render_with_reportlab(md, out, {})


VERIFICATION_TABLE = (
    "| Concern | Conclusion at stake | Already addressed? | Bias direction | Remedy | Tier |\n"
    "|---|---|---|---|---|---|\n"
    "| Keyword trend | " + "the conclusion says methods coexist throughout the period " * 2
    + "| Partly: the Results say positions differ, not methods | Not an inflation or deflation of a count "
    "| Recode the method used in each of the 53 papers | Blocking |\n"
)
SMALL_TABLE = "| Reviewer | Verdict |\n|---|---|\n| alfa | Major revision |\n"


def test_wide_tables_get_landscape_pages_and_proportional_columns():
    out = _layout_tables_for_latex(SMALL_TABLE + "\ntext\n\n" + VERIFICATION_TABLE)
    assert out.count("\\begin{landscape}") == 1
    small, wide = out.split("text")
    assert "landscape" not in small
    separator = next(ln for ln in wide.splitlines() if ln.startswith("|-"))
    widths = [len(c) for c in separator.strip("|").split("|")]
    # The prose column is wider than the tier column; pandoc reads widths from these dashes.
    assert widths[1] > widths[5] >= 10


def test_reportlab_puts_wide_tables_on_landscape_pages(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    md = "# Part I\n\nIntro.\n\n" + VERIFICATION_TABLE + "\n\nAfter.\n\n" + SMALL_TABLE
    pdf = tmp_path / "r.pdf"
    assert render_with_reportlab(md, pdf, {})
    pages = pypdf.PdfReader(str(pdf)).pages
    orientation = ["L" if float(p.mediabox.width) > float(p.mediabox.height) else "P" for p in pages]
    assert orientation == ["P", "L", "P"]


def test_reviewer_metadata_block_becomes_a_wrapping_list():
    from generate_pdf_report import _clean_markdown_for_pdf

    axis = "Indexing artefact: indexer-assigned keywords or vocabulary drift masquerading as thematic change"
    text = f"# Referee report\n\n```\nSEED: 828d2b5ffe0be6a4\nAXIS: {axis}\nSTANCE: Sharp but balanced\n```\n\n### Summary\n\n```\ncode stays\n```\n"
    out = _clean_markdown_for_pdf(text)
    assert f"- **Axis:** {axis}" in out
    assert "- **Seed:** `828d2b5ffe0be6a4`" in out and "- **Stance:** Sharp but balanced" in out
    assert out.count("```") == 2  # ordinary code blocks are untouched
