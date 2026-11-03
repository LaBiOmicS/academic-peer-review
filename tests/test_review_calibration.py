"""Regression tests for review calibration, drawn from a real bibliometric-review run.

The run over-weighted its critique: every gap became a must-fix item, agreement among reviewers
sharing one model was read as consensus, an incomplete final year was said to inflate a peak it
actually undercounts, a primary-study axis (sequence accessions) drove a verdict on a bibliometric
review, and the meta-review quoted scope figures from an older audit. Each test pins one fix.
"""

from __future__ import annotations

import re
from pathlib import Path

import compile_results as cr
import spawn_reviewers
from area_profiles import get_lens_tables
from stat_and_integrity_audit import check_article_type_markers

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "paper-review"
PROMPTS = SKILL_DIR / "prompts"
REVIEWER_TEMPLATES = [
    "reviewer.md",
    "reviewer_alignment_forum.md",
    "reviewer_methodology_stats.md",
    "reviewer_reproducibility_integrity.md",
    "reviewer_author_advocate.md",
]

BIBLIOMETRIC_METHODS = (
    "We conducted a quantitative, descriptive bibliometric study of antimicrobial resistance associated "
    "with insects from 2010 to 2025. Searches were performed in Scopus, Web of Science, and PubMed on "
    "20 November 2025. We exported their metadata as a single BibTeX file on 22 June 2026 and analysed "
    "it with Bibliometrix/Biblioshiny and VOSviewer."
)


# --- Audit: deterministic checks ------------------------------------------------------------


def test_search_date_detected_in_bibliometric_methods():
    checks = check_article_type_markers(BIBLIOMETRIC_METHODS, "bibliometric_review")
    assert checks["search_date_reported"] is True


def test_bibliometric_review_uses_its_own_lenses_not_primary_study_ones():
    lenses, axes, scope = get_lens_tables("biologicas", "bibliometric_review")
    assert scope == "biologicas × bibliometric_review"
    joined = " ".join(lenses + axes).lower()
    assert "accession" not in joined and "replicate" not in joined


def test_incomplete_year_axis_does_not_presume_inflation():
    _, axes, _ = get_lens_tables("biologicas", "bibliometric_review")
    axis = next(a for a in axes if "final year" in a.lower())
    assert "spurious" not in axis.lower()
    assert "undercount" in axis.lower()


# --- Panel composition and reviewer prompts -------------------------------------------------


def _roles(n: int, **kwargs) -> list[str]:
    return sorted(role for role, _ in spawn_reviewers.assign_templates(n, SKILL_DIR, **kwargs))


def test_default_panel_includes_author_advocate_and_all_specialists():
    assert _roles(5) == sorted([
        "epistemic-redteam-critic",
        "author-advocate",
        "methodology-stats-auditor",
        "reproducibility-integrity-inspector",
        "domain-reviewer",
    ])


def test_small_panel_keeps_critic_and_advocate_paired():
    roles = _roles(3)
    assert "epistemic-redteam-critic" in roles and "author-advocate" in roles


def test_author_advocate_can_be_disabled():
    assert "author-advocate" not in _roles(5, author_advocate=False)


def test_every_reviewer_template_renders_the_severity_rubric(tmp_path):
    area_info = spawn_reviewers.classify_manuscript(BIBLIOMETRIC_METHODS, explicit_article_type="bibliometric_review")
    for name in REVIEWER_TEMPLATES:
        template = PROMPTS / name
        assert "{severity_rubric}" in template.read_text(encoding="utf-8"), name
        prompt = spawn_reviewers.build_prompt(
            template,
            reviewer_id="alfa",
            paper_text="PAPER",
            skill_dir=str(SKILL_DIR),
            domain="x",
            area_info=area_info,
            audit_text="",
            entropy_hint="00" * 16,
        )
        assert "Severity Calibration & Proportionality" in prompt, name
        assert f"At most {spawn_reviewers.MAX_BLOCKING_CONCERNS} `Blocking` concerns" in prompt, name
        assert "{severity_rubric}" not in prompt and "{area_rubric}" not in prompt, name


def test_severity_rubric_requires_bias_direction_and_existing_caveats():
    rubric = spawn_reviewers.SEVERITY_RUBRIC
    assert "direction" in rubric and "undercounts" in rubric
    assert "already" in rubric and "hypothesis to test" in rubric


def test_author_advocate_review_parses_like_any_other():
    review = (
        "SEED: " + "ab" * 16 + "\nLENS: Author advocate — already-addressed critiques and proportionality\n"
        "STANCE: Fair advocate\n\n### Summary\nx\n\n### Already addressed in the manuscript\n1. y\n\n"
        "### Proportionality guardrails\n- z\n\n### Major concerns\n1. **Issue** — w [Severity: Essential]\n\n"
        "### Minor concerns\n- v\n\n### Verdict\n**Minor revision** — the reporting gaps are fixable.\n"
    )
    meta = cr.parse_single_review(review)
    assert meta["verdict"] == "Minor revision"
    assert meta["lens_or_axis"].startswith("Author advocate")


# --- Meta-review prompt ---------------------------------------------------------------------


def test_metareview_prompt_forbids_headcount_and_requires_verification():
    text = (PROMPTS / "metareview.md").read_text(encoding="utf-8")
    assert "not** independent corroboration" in text
    assert "## Blocking-concern verification" in text
    for tier in ("**Blocking**", "**Essential**", "**Optional**"):
        assert tier in text
    assert '"severity": "blocking"' in text and '"alfa": "major"' in text


# --- Concerns matrix --------------------------------------------------------------------------


def test_concern_cells_distinguish_major_from_passing_mentions():
    rows = cr._normalize_concern_rows(
        [{"concern": "Search strings missing", "severity": "Essential", "alfa": "major", "beta": "minor", "gamma": False},
         {"concern": "Legacy row", "alfa": True, "beta": "false", "gamma": "x"}],
        ["alfa", "beta", "gamma"],
    )
    assert rows[0] == {"concern": "Search strings missing", "severity": "essential", "alfa": "major", "beta": "minor", "gamma": ""}
    assert rows[1]["alfa"] == "major" and rows[1]["beta"] == "" and rows[1]["gamma"] == "major"
    md = cr._concerns_markdown(rows, ["alfa", "beta", "gamma"])
    assert "| Search strings missing | Essential | ✓ | (m) | · | 1/3 |" in md
    assert "not independent corroboration" in md


# --- Audit figures and staleness ------------------------------------------------------------

AUDIT = {
    "journal_scope_audit": {
        "target_journal": "Ecología Austral",
        "adherence_score_pct": 65,
        "fit_category": "Moderate Adherence",
        "desk_reject_risk": "Moderate Risk",
    },
    "citation_audit": {"checked_count": 54, "verified_count": 54, "unresolvable_dois": [], "retracted_works": []},
}

META = (
    "## Common concerns\nx\n\n"
    "## Statistical, Provenance & Reproducibility Audit Highlights\n"
    "- **Journal scope**: the automatic audit gives 83% adherence and **Low Risk**.\n\n"
    "## Actionable Revision Roadmap\n"
    "1. **Blocking**\n   - [ ] Soften the method-trend claim.\n"
    "2. **Essential**\n   - [ ] Report the search strings.\n"
    "3. **Optional**\n   - [ ] Add a co-authorship network.\n   - [ ] Search SciELO.\n\n"
    "## Verdict synthesis\n**Major revision.** One conclusion needs softening.\n"
)


def test_stale_scope_figures_are_flagged():
    warnings = cr.audit_consistency_warnings(META, AUDIT)
    assert any("83%" in w and "65%" in w for w in warnings)
    assert any("low" in w and "Moderate Risk" in w for w in warnings)


def test_audit_regenerated_after_meta_review_is_flagged():
    warnings = cr.audit_consistency_warnings("", AUDIT, meta_mtime=100.0, audit_mtime=200.0)
    assert any("regenerated after meta_review.md" in w for w in warnings)


def test_consistent_meta_review_raises_no_warning():
    ok = META.replace("83% adherence and **Low Risk**", "a moderate fit")
    assert cr.audit_consistency_warnings(ok, AUDIT, meta_mtime=200.0, audit_mtime=100.0) == []


def test_audit_figures_injected_once_inside_their_section():
    once = cr.inject_audit_figures(META, AUDIT)
    twice = cr.inject_audit_figures(once, AUDIT)
    assert once == twice
    assert once.count(cr.AUDIT_START) == 1
    section = once.split("## Statistical, Provenance & Reproducibility Audit Highlights")[1].split("\n## ")[0]
    assert "65% adherence" in section and "54 of 54 resolved" in section
    # The injected block itself never trips the consistency check.
    clean = once.replace("83% adherence and **Low Risk**", "a moderate fit")
    assert cr.audit_consistency_warnings(clean, AUDIT) == []


# --- Author letter --------------------------------------------------------------------------


def test_author_letter_keeps_blocking_and_essential_only():
    letter = cr.build_author_letter(META, "Major revision")
    assert "**Editorial recommendation: Major revision**" in letter
    assert "Soften the method-trend claim" in letter and "Report the search strings" in letter
    assert "co-authorship network" not in letter and "SciELO" not in letter
    assert "2 optional suggestion(s)" in letter
    assert not re.search(r"^[ \t]+- \[ \]", letter, re.MULTILINE)


def test_author_letter_absent_without_roadmap():
    assert cr.build_author_letter("## Verdict synthesis\nAccept.\n", "Accept") is None
