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
    monkeypatch.setattr(openalex_lookup, "_doi_registered", lambda doi, timeout: False)
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
    monkeypatch.setattr(openalex_lookup, "_doi_registered", lambda doi, timeout: False)
    res = lookup_dois([f"10.1000/x{i}" for i in range(120)])
    assert len(calls) == 3
    # Beyond the registry cap, missing DOIs stay unchecked instead of being called unresolvable.
    assert len(res["unresolvable"]) == openalex_lookup.MAX_REGISTRY_CHECKS
    assert len(res["unresolvable"]) + len(res["unchecked"]) == 120


def test_doi_missing_from_openalex_but_registered_is_not_unresolvable(monkeypatch):
    # Regression (real run): a JMIR preprint DOI absent from OpenAlex was reported as hallucinated.
    def fake_get_json(url, timeout):
        if "doi.org/api/handles/10.2196/preprints.82364" in url:
            return {"responseCode": 1, "handle": "10.2196/preprints.82364"}
        if "doi.org/api/handles/" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return {"results": []}

    monkeypatch.setattr(openalex_lookup, "_get_json", fake_get_json)
    res = lookup_dois(["10.2196/preprints.82364", "10.9999/fake.123"])
    assert res["found"]["10.2196/preprints.82364"]["registry_only"] is True
    assert res["unresolvable"] == ["10.9999/fake.123"]


def test_registry_failure_leaves_doi_unchecked(monkeypatch):
    def fake_get_json(url, timeout):
        if "doi.org/api/handles/" in url:
            raise urllib.error.URLError("offline")
        return {"results": []}

    monkeypatch.setattr(openalex_lookup, "_get_json", fake_get_json)
    res = lookup_dois(["10.1000/maybe"])
    assert res["unresolvable"] == []
    assert res["unchecked"] == ["10.1000/maybe"]


def test_registry_checks_are_capped(monkeypatch):
    registry_calls = []
    monkeypatch.setattr(openalex_lookup, "_get_json", lambda url, timeout: {"results": []})

    def registered(doi, timeout):
        registry_calls.append(doi)
        return False

    monkeypatch.setattr(openalex_lookup, "_doi_registered", registered)
    res = lookup_dois([f"10.1000/y{i}" for i in range(50)])
    assert len(registry_calls) == openalex_lookup.MAX_REGISTRY_CHECKS
    assert len(res["unchecked"]) == 50 - openalex_lookup.MAX_REGISTRY_CHECKS
