from __future__ import annotations

import pytest

from stat_and_integrity_audit import calc_p_value, run_statcheck

stats = pytest.importorskip("scipy.stats")


@pytest.mark.parametrize(
    ("kind", "value", "df1", "df2", "reference"),
    [
        ("t", 2.1, 30, None, lambda: 2 * stats.t.sf(2.1, 30)),
        ("t", -3.4, 12, None, lambda: 2 * stats.t.sf(3.4, 12)),
        ("F", 4.2, 2, 50, lambda: stats.f.sf(4.2, 2, 50)),
        ("chi2", 7.8, 3, None, lambda: stats.chi2.sf(7.8, 3)),
        ("z", 1.96, 0, None, lambda: 2 * stats.norm.sf(1.96)),
        ("r", 0.35, 40, None, lambda: 2 * stats.t.sf(0.35 * (40 / (1 - 0.35**2)) ** 0.5, 40)),
    ],
)
def test_p_values_match_scipy(kind, value, df1, df2, reference):
    assert calc_p_value(kind, value, df1, df2) == pytest.approx(reference(), rel=1e-8, abs=1e-12)


def test_greater_than_p_is_not_a_significance_claim():
    # Regression: "p > .01" was treated as a reported significant result.
    res = run_statcheck("t(28) = 1.20, p > .01")
    assert res["tests_checked"] == 1
    assert res["decision_errors_count"] == 0


def test_real_decision_error_still_detected():
    res = run_statcheck("F(1, 20) = 3.1, p < .05")
    assert res["decision_errors_count"] == 1
    res_ns = run_statcheck("t(40) = 3.50, p > .05")
    assert res_ns["decision_errors_count"] == 1


def test_consistent_report_passes():
    res = run_statcheck("t(30) = 2.10, p = .044")
    assert res["inconsistencies_count"] == 0
    assert res["decision_errors_count"] == 0


def test_common_words_do_not_trigger_acronym_checks():
    from stat_and_integrity_audit import (
        check_area_specific_markers,
        check_article_type_markers,
    )

    en = "Patients received drug or placebo and outcomes were recorded or missed. " * 5
    assert check_area_specific_markers(en, "saude", "x")["effect_size_reported"] is False  # "or" != OR
    pt = "Os pacientes foram avaliados sem perdas nos centros. " * 5
    assert check_area_specific_markers(pt, "saude", "x")["confidence_intervals_or_error_bars"] is False  # "sem" != SEM
    assert check_article_type_markers(pt, "systematic_review")["risk_of_bias_tool_used"] is False  # "nos" != NOS
    assert check_area_specific_markers("OR = 2.1 (95% CI 1.2-3.4)", "saude", "x")["effect_size_reported"] is True


def test_boolean_search_string_requires_operators_near_database():
    from stat_and_integrity_audit import check_article_type_markers

    prose = "We searched PubMed and Scopus or Embase for studies."
    assert check_article_type_markers(prose, "systematic_review")["boolean_search_string_reported"] is False
    query = 'PubMed: ("sepsis" OR "septic shock") AND (child OR infant)'
    assert check_article_type_markers(query, "systematic_review")["boolean_search_string_reported"] is True


def test_partial_open_data_is_not_labelled_evasive():
    from stat_and_integrity_audit import audit_reproducibility_and_fair

    text = "Data availability: reads are in SRA (PRJNA123456). Additional data are available upon reasonable request."
    status = audit_reproducibility_and_fair(text, "biologicas", "experimental_lab")["data_status"]
    assert status.startswith("Partially Open")


def test_primer_mention_alone_is_not_primer_sequences():
    from stat_and_integrity_audit import audit_reproducibility_and_fair

    def primers(t):
        return audit_reproducibility_and_fair(t, "biologicas", "experimental_lab")["experimental_specificity"][
            "primer_sequences_reported"
        ]

    assert primers("Primers were designed as described previously.") is False
    assert primers("Forward primer: ACGTTGCAAGTCCGATTGCA") is True


@pytest.mark.parametrize(
    "text",
    [
        "t(28) = 2.10, P = .045",  # uppercase P (medical journals)
        "t(28) = 2,10; p = 0,045",  # decimal comma (PT/ES manuscripts)
        "χ²(2) = 7.8, p = .02",  # superscript two
        "t(28) = −2.10, p = .045",  # Unicode minus from PDF extraction
    ],
)
def test_statistic_formats_are_parsed(text):
    assert run_statcheck(text)["tests_checked"] == 1


def test_rounding_tolerance_avoids_false_decision_error():
    # z = 1.96 gives p = .04999..., but 1.96 stands for [1.955, 1.965]: "p = .05" is consistent.
    res = run_statcheck("z = 1.96, p = .05")
    assert res["inconsistencies_count"] == 0
    assert res["decision_errors_count"] == 0


def test_p_below_001_is_not_fragile():
    assert run_statcheck("p < .01")["fragile_p_values_001_to_005_count"] == 0
    assert run_statcheck("p = .03")["fragile_p_values_001_to_005_count"] == 1


def test_decision_errors_listed_in_markdown_report():
    import stat_and_integrity_audit as audit_mod
    from area_profiles import classify_manuscript

    text = "Results: t(30) = 2.00, p = .049."
    audit = {
        "scientific_area": classify_manuscript(text),
        "statcheck": run_statcheck(text),
        "methodological_markers": audit_mod.check_area_specific_markers(text, "exatas", "x"),
    }
    md = audit_mod.format_markdown_report(audit)
    assert "t(30) = 2.00, p = .049" in md
    assert "[DECISION ERROR]" in md


def test_markdown_report_sections_are_numbered_consecutively():
    import re

    import stat_and_integrity_audit as audit_mod
    from area_profiles import classify_manuscript

    text = "Results: t(30) = 2.00, p = .049."
    audit = {
        "scientific_area": classify_manuscript(text),
        "statcheck": run_statcheck(text),
        "methodological_markers": audit_mod.check_area_specific_markers(text, "exatas", "x"),
    }
    numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", audit_mod.format_markdown_report(audit), re.MULTILINE)]
    assert numbers == list(range(len(numbers)))
