"""Bibliometric reviews are judged on their corpus and indicators, not on primary-study standards."""

from __future__ import annotations

import journal_scope
import spawn_reviewers
import stat_and_integrity_audit as audit_mod
from area_profiles import RESEARCH_APPROACH_DEFINITIONS, classify_manuscript, get_lens_tables
from journal_scope import audit_journal_scope
from stat_and_integrity_audit import SEARCH_DATE_PATTERN, format_markdown_report, run_statcheck

# Mirrors a real submission: the reviewed literature's vocabulary (metagenomics, WGS, PCR) used to
# classify the approach as computational_in_silico with 0.97 confidence and no confirmation step.
BIBLIOMETRIC_TEXT = (
    "A bibliometric analysis of antimicrobial resistance in insects. Searches were performed in Scopus, "
    "Web of Science, and PubMed on 20 November 2025. We analyzed metadata with Bibliometrix/Biblioshiny "
    "and VOSviewer, applying Bradford's law and Lotka's law. Keyword co-occurrence used All Keywords. "
    "Methods in the corpus included PCR, 16S rRNA, WGS and metagenomics; metagenomic studies and "
    "bioinformatics pipelines were more recent. "
) * 4


def test_bibliometric_review_gets_bibliometric_approach():
    sa = classify_manuscript(BIBLIOMETRIC_TEXT)
    assert sa["article_type"]["type_code"] == "bibliometric_review"
    assert sa["research_approach"]["approach_code"] == "bibliometric_scientometric"
    assert sa["research_approach"]["exempt_from_inferential_stats"]
    # An explicit approach still wins.
    forced = classify_manuscript(BIBLIOMETRIC_TEXT, explicit_research_approach="quantitative_statistical")
    assert forced["research_approach"]["approach_code"] == "quantitative_statistical"


def test_bibliometric_approach_is_selectable_by_alias():
    assert "bibliometric_scientometric" in RESEARCH_APPROACH_DEFINITIONS
    sa = classify_manuscript("We ran a survey of 300 farmers.", explicit_research_approach="scientometric")
    assert sa["research_approach"]["approach_code"] == "bibliometric_scientometric"


def test_bibliometric_lens_tables_replace_primary_study_lenses():
    lenses, axes, scope = get_lens_tables("biologicas", "bibliometric_review")
    # The templates derive lenses with mod 6 and red-team axes with mod 8 (see LENS_PERIOD).
    assert len(lenses) == 6 and len(axes) == 8
    assert scope == "biologicas × bibliometric_review"
    joined = " ".join(lenses + axes)
    assert "Pseudoreplication" not in joined and "SRA" not in joined
    assert get_lens_tables("biologicas", "original_research")[2] == "biologicas"


def test_redteam_prompt_uses_bibliometric_axes(tmp_path):
    template = tmp_path / "t.md"
    template.write_text("axis for `{lens_scope}`:\n{area_redteam_axes}\n{area_ssot_lenses}", encoding="utf-8")
    prompt = spawn_reviewers.build_prompt(
        template,
        reviewer_id="gamma",
        paper_text="",
        skill_dir=str(tmp_path),
        domain="x",
        area_info=classify_manuscript(BIBLIOMETRIC_TEXT),
        audit_text="",
        entropy_hint="00",
    )
    assert "biologicas × bibliometric_review" in prompt
    assert "Dominant-group effect" in prompt
    assert "Batch effect" not in prompt


def test_rubric_keeps_area_as_context_only_for_bibliometric_review():
    from area_profiles import compose_rubric

    rubric = compose_rubric(classify_manuscript(BIBLIOMETRIC_TEXT))
    assert "Domain context only" in rubric
    assert "pseudoreplication" not in rubric
    assert "pseudoreplication" in compose_rubric(classify_manuscript("We sequenced RNA-seq libraries in mice. " * 5))


def test_audit_skips_primary_study_checks_for_bibliometric_review():
    sa = classify_manuscript(BIBLIOMETRIC_TEXT)
    md = format_markdown_report({
        "scientific_area": sa,
        "statcheck": run_statcheck(BIBLIOMETRIC_TEXT),
        "methodological_markers": audit_mod.check_area_specific_markers(BIBLIOMETRIC_TEXT, "biologicas", "x"),
        "research_approach_checks": audit_mod.check_research_approach_markers(BIBLIOMETRIC_TEXT, "bibliometric_scientometric"),
        "reproducibility_and_fair_audit": audit_mod.audit_reproducibility_and_fair(BIBLIOMETRIC_TEXT, "biologicas", "x"),
    })
    assert "Not applicable" in md
    assert "Biological vs technical replicates" not in md
    assert "Multiple-comparison correction" not in md
    assert "Random Seeds" not in md
    assert "Ethics Committee Approval**: Not required" in md
    assert "Keyword field specified**: Yes" in md


def test_search_date_found_inside_the_search_sentence():
    assert SEARCH_DATE_PATTERN.search("Searches were performed in Scopus and PubMed on 20 November 2025.")
    assert SEARCH_DATE_PATTERN.search("A busca foi realizada em 12 de março de 2024.")
    assert not SEARCH_DATE_PATTERN.search("We searched broadly. On 2 occasions in 2020 we met.")


ECOLOGY_JOURNAL_TOPICS = [
    {"name": "Ecology and Vegetation Dynamics Studies", "domain": "Physical Sciences"},
    {"name": "Botany and Plant Ecology Studies", "domain": "Life Sciences"},
    {"name": "Forest ecology and management", "domain": "Physical Sciences"},
    {"name": "Animal Ecology and Behavior Studies", "domain": "Physical Sciences"},
    {"name": "Wildlife Ecology and Conservation", "domain": "Physical Sciences"},
    {"name": "Insect and Arachnid Ecology and Behavior", "domain": "Life Sciences"},
]


def test_words_shared_by_most_journal_topics_do_not_count_as_matches(monkeypatch):
    # Regression: "ecology" (in every topic of an ecology journal) plus one generic word such as
    # "dynamic" or "animal", or "management" from a cited journal title, matched three unrelated
    # topics and rated an AMR bibliometric review as 83% / Low Risk.
    monkeypatch.setattr(
        journal_scope,
        "query_openalex_journal",
        lambda *a, **k: {
            "display_name": "Ecología Austral",
            "topics": ECOLOGY_JOURNAL_TOPICS,
            "exact_title_match": True,
            "source": "OpenAlex Sources API",
        },
    )
    text = (
        "Antimicrobial resistance ecology in insects: animal production systems take part in this dynamic.\n"
        "REFERENCES\nSmith, J. 2020. Title. Journal of Environmental Management 1:1.\n"
    )
    sa = {"area_code": "biologicas", "article_type": {"type_code": "bibliometric_review"},
          "research_approach": {"approach_code": "bibliometric_scientometric"}}
    audit = audit_journal_scope(text, "Ecología Austral", sa)
    assert audit["matched_topics"] == []
    assert audit["desk_reject_risk"] != "Low Risk"


def test_reproducibility_lenses_follow_the_profile(tmp_path):
    from area_profiles import get_repro_lenses

    open_science, normative = get_repro_lenses("biologicas", "bibliometric_review", "bibliometric_scientometric")
    assert "SRA" not in open_science and "DOIs/EIDs" in open_science
    assert "ARRIVE" not in normative and "BIBLIO" in normative
    # A review of literature is not asked for animal-research approval; a primary study is.
    assert "no ethics approval" in get_repro_lenses("biologicas", "systematic_review")[1]
    assert "ARRIVE" in get_repro_lenses("biologicas", "original_research", "experimental_lab")[1]

    template = tmp_path / "t.md"
    template.write_text("- 3 — {repro_lens_open_science}\n- 4 — {repro_lens_normative}", encoding="utf-8")
    prompt = spawn_reviewers.build_prompt(
        template, reviewer_id="alfa", paper_text="", skill_dir=str(tmp_path), domain="x",
        area_info=classify_manuscript(BIBLIOMETRIC_TEXT), audit_text="", entropy_hint="00",
    )
    assert "thesaurus" in prompt and "{repro" not in prompt


def test_search_string_in_external_protocol_or_supplement():
    from stat_and_integrity_audit import format_check_value, search_string_status

    protocol = ("The full protocol, including the search strategies and eligibility criteria, "
                "is published in protocols.io (Oliveira 2026). Searches ran in Scopus.")
    assert search_string_status(protocol) == "No — only in an external protocol (protocols.io)"
    assert search_string_status("The search strategy is in Supplementary Table S1. Done.") == "Only in supplementary material"
    assert search_string_status("We searched Scopus.") is False
    assert search_string_status('Scopus: TITLE-ABS-KEY(insect AND (resistance OR AMR) AND NOT plant)') is True
    assert format_check_value("Only in supplementary material") == "Only in supplementary material"
    assert format_check_value(True) == "Yes" and format_check_value([]) == "None detected"
