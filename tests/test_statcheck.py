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
