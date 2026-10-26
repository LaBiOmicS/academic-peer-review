from __future__ import annotations

import urllib.error
import urllib.parse

import openalex_lookup
from openalex_lookup import lookup_dois, normalize_doi


def test_normalize_doi_variants():
    assert normalize_doi("https://doi.org/10.1038/Nature12373.") == "10.1038/nature12373"
    assert normalize_doi("doi: 10.1093/bioinformatics/btp324") == "10.1093/bioinformatics/btp324"
    assert normalize_doi("not a doi") is None


def test_batch_lookup_splits_found_unresolvable_and_unchecked(monkeypatch):
    requested = []

    def fake_get_json(url, timeout):
        requested.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert "select" in query
        return {
            "results": [
                {"doi": "https://doi.org/10.1000/real", "title": "Real", "publication_year": 2020, "is_retracted": True},
            ]
        }

    monkeypatch.setattr(openalex_lookup, "_get_json", fake_get_json)
    res = lookup_dois(["10.1000/REAL", "10.1000/fake", "10.1000/real"])
    assert len(requested) == 1  # one batched request, duplicates collapsed
    assert set(res["found"]) == {"10.1000/real"}
    assert res["unresolvable"] == ["10.1000/fake"]
    assert res["unchecked"] == []


def test_network_failure_marks_unchecked_not_unresolvable(monkeypatch):
    def failing(url, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(openalex_lookup, "_get_json", failing)
    res = lookup_dois(["10.1000/a", "10.1000/b"])
    assert res["unresolvable"] == []
    assert sorted(res["unchecked"]) == ["10.1000/a", "10.1000/b"]


def test_more_than_one_batch(monkeypatch):
    calls = []

    def fake_get_json(url, timeout):
        calls.append(url)
        return {"results": []}

    monkeypatch.setattr(openalex_lookup, "_get_json", fake_get_json)
    res = lookup_dois([f"10.1000/x{i}" for i in range(120)])
    assert len(calls) == 3
    assert len(res["unresolvable"]) == 120
