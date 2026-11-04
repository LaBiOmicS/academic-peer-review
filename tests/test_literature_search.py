"""Literature search: each database's payload is parsed into one record shape, offline."""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request

import pytest

import literature_search as ls

OPENALEX = {
    "results": [
        {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1/abc",
            "title": "Insect​ resistome",
            "publication_year": 2020,
            "authorships": [{"author": {"display_name": n}} for n in ("Ana", "Bo", "Cy", "Di")],
            "abstract_inverted_index": {"Flies": [0], "carry": [1], "genes": [2]},
            "cited_by_count": 7,
            "is_retracted": True,
        },
        {"id": "https://openalex.org/W2", "title": None, "authorships": []},
    ]
}
EUROPEPMC = {
    "resultList": {
        "result": [
            {"pmid": "123", "doi": "10.2/x", "title": "Housefly AMR", "pubYear": "2019",
             "authorString": "Smith J", "abstractText": "Abstract.", "citedByCount": 3, "pubType": "journal article"},
            {"id": "PPR9", "title": "Preprint", "pubType": "Retracted Publication"},
        ]
    }
}
CROSSREF = {
    "message": {
        "items": [
            {"DOI": "10.3/y", "title": ["Cockroach <i>bacteria</i>"], "issued": {"date-parts": [[2021, 5]]},
             "author": [{"given": "Li", "family": "Wang"}, {"name": "Consortium X"}],
             "abstract": "<jats:p>Resistant <b>strains</b>.</jats:p>", "is-referenced-by-count": 2,
             "updated-by": [{"type": "retraction"}]},
            {"title": [], "container-title": ["J. Ecol."], "update-to": [{"type": "retraction"}]},
        ]
    }
}
ARXIV = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <title>Mapping  science</title>
    <summary>Co-word maps.</summary>
    <published>2023-01-30T00:00:00Z</published>
    <author><name>A</name></author><author><name>B</name></author>
    <author><name>C</name></author><author><name>D</name></author>
  </entry>
</feed>"""


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_apis(monkeypatch):
    calls: list[str] = []

    def urlopen(req, timeout=None):
        url = req.full_url
        calls.append(url)
        if "openalex" in url:
            return _Resp(json.dumps(OPENALEX).encode())
        if "europepmc" in url:
            return _Resp(json.dumps(EUROPEPMC).encode())
        if "crossref" in url:
            return _Resp(json.dumps(CROSSREF).encode())
        if "arxiv" in url:
            return _Resp(ARXIV)
        raise AssertionError(url)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return calls


def test_only_https_urls_are_fetched():
    with pytest.raises(ValueError):
        ls._validate_https_url("http://api.openalex.org/works")
    ls._validate_https_url("https://api.openalex.org/works")


def test_external_text_is_cleaned_and_truncated():
    assert ls._clean_external_text("a‮ b\n\n c") == "a b c"
    assert ls._clean_external_text("x" * 20, max_len=5) == "xxxxx…"


def test_xml_with_entities_is_refused():
    with pytest.raises(ValueError):
        ls._safe_parse_xml(b'<!DOCTYPE x [<!ENTITY a "b">]><x>&a;</x>')


def test_openalex_records(fake_apis):
    first, second = ls.search_openalex("insect resistome", max_papers=2, sort="citations")
    assert "sort=cited_by_count" in fake_apis[0]
    assert first["id"] == "DOI:10.1/abc" and first["title"] == "Insect resistome"
    assert first["authors"] == "Ana, Bo, Cy et al." and first["summary"] == "Flies carry genes"
    assert first["retracted"] is True
    assert second["id"] == "OpenAlex:W2" and second["summary"] == "(No abstract in OpenAlex)"


def test_europepmc_records(fake_apis):
    first, second = ls.search_europepmc("housefly")
    assert first["id"] == "PMID:123 | DOI:10.2/x" and not first["retracted"]
    assert second["id"] == "EPMC:PPR9" and second["retracted"]


def test_crossref_retraction_comes_from_updated_by_only(fake_apis):
    first, second = ls.search_crossref("cockroach")
    assert first["retracted"] and first["summary"] == "Resistant strains ."
    assert first["authors"] == "Li Wang, Consortium X" and first["year"] == "2021"
    assert not second["retracted"] and second["summary"] == "Published in: J. Ecol."


def test_arxiv_records(fake_apis):
    (rec,) = ls.search_arxiv_api("mapping", sort="date")
    assert "sortBy=submittedDate" in fake_apis[0]
    assert rec["id"] == "arXiv:2301.12345v2" and rec["year"] == "2023"
    assert rec["title"] == "Mapping science" and rec["authors"] == "A, B, C et al."


def test_format_results_flags_retractions():
    assert ls.format_results([]) == "No papers found."
    out = ls.format_results([{"id": "DOI:1", "year": "2020", "title": "T", "authors": "A",
                              "citations": None, "retracted": True, "summary": "S", "source": "X"}])
    assert "RETRACTED" in out and "Citations" not in out


def test_main_round_robins_and_dedupes(fake_apis, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["literature_search.py", "insects", "--max-papers", "4"])
    assert ls.main() == 0
    out = capsys.readouterr().out
    assert out.count("[") >= 4
    assert {u.split("/")[2] for u in fake_apis} >= {"api.openalex.org", "export.arxiv.org"}


def test_main_reports_when_every_source_fails(monkeypatch, capsys):
    def down(req, timeout=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    monkeypatch.setattr(ls.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["literature_search.py", "x", "--source", "openalex"])
    assert ls.main() == 1
    assert "all sources failed" in capsys.readouterr().err
