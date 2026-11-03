from __future__ import annotations

import subprocess
import urllib.error

import arxiv_lookup
import compile_results as cr
import generate_pdf_report

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>https://arxiv.org/api/abc</id>
  <entry>
    <id>http://arxiv.org/abs/2610.38748v1</id>
    <title>Guidance List for repOrting Bibliometric AnaLyses (GLOBAL)</title>
    <published>2026-10-01T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/hep-ex/0111081v1</id>
    <title>MACRIB</title>
    <published>2001-11-01T00:00:00Z</published>
  </entry>
</feed>"""


def test_normalize_arxiv_id():
    assert arxiv_lookup.normalize_arxiv_id("arXiv:2610.38748v1") == "2610.38748"
    assert arxiv_lookup.normalize_arxiv_id("https://arxiv.org/abs/hep-ex/0111081v2") == "hep-ex/0111081"
    assert arxiv_lookup.normalize_arxiv_id("arXiv:not-an-id") is None


def test_ids_missing_from_a_successful_batch_are_unresolvable(monkeypatch):
    seen = []

    def fake_fetch(ids, timeout):
        seen.append(ids)
        return FEED

    monkeypatch.setattr(arxiv_lookup, "_fetch", fake_fetch)
    res = arxiv_lookup.lookup_arxiv_ids(["arXiv:2610.38748v1", "hep-ex/0111081", "2610.99999", "2610.38748", "junk"])
    assert seen == [["2610.38748", "hep-ex/0111081", "2610.99999"]]
    assert set(res["found"]) == {"2610.38748", "hep-ex/0111081"}
    assert res["found"]["2610.38748"]["year"] == 2026
    assert res["unresolvable"] == ["2610.99999"]
    assert res["invalid"] == ["junk"]


def test_network_failure_leaves_ids_unchecked(monkeypatch):
    def boom(ids, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(arxiv_lookup, "_fetch", boom)
    res = arxiv_lookup.lookup_arxiv_ids(["2610.38748"])
    assert res["unresolvable"] == [] and res["unchecked"] == ["2610.38748"]


def test_xml_entities_are_rejected(monkeypatch):
    monkeypatch.setattr(arxiv_lookup, "_fetch", lambda ids, timeout: b'<!DOCTYPE x [<!ENTITY a "b">]><feed/>')
    assert arxiv_lookup.lookup_arxiv_ids(["2610.38748"])["unchecked"] == ["2610.38748"]


def test_reviewer_arxiv_citations_are_audited(monkeypatch):
    monkeypatch.setattr(cr, "lookup_dois", lambda dois, max_checks=100: {"found": {}, "unresolvable": [], "unchecked": [], "invalid": []})
    monkeypatch.setattr(arxiv_lookup, "_fetch", lambda ids, timeout: FEED)
    meta = {
        "alfa": {"external_citations": ["arXiv:2610.38748v1", "arXiv:2610.99999"]},
        "beta": {"external_citations": ["arXiv:2301.11111"]},  # quoted from the manuscript: not checked
    }
    audit = cr.verify_reviewer_citations(meta, paper_arxiv={"2301.11111"})
    assert audit["flagged_reviewers"] == {"alfa": ["arXiv:2610.99999"]}
    assert audit["unresolvable_arxiv"] == ["2610.99999"]
    assert [v["arxiv_id"] for v in audit["verified_arxiv"]] == ["2610.38748"]


def test_manuscript_arxiv_ids_are_normalized():
    assert cr.manuscript_arxiv_ids("see arXiv:2301.11111v3 and arxiv.org/abs/2302.22222") == {"2301.11111", "2302.22222"}


def test_pandoc_falls_back_quietly_when_one_engine_fails(tmp_path, monkeypatch, capsys):
    out = tmp_path / "r.pdf"
    monkeypatch.setattr(generate_pdf_report.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, **kwargs):
        engine = next(a for a in cmd if a.startswith("--pdf-engine=")).split("=", 1)[1]
        if engine == "pdflatex":
            out.write_bytes(b"%PDF" + b"0" * 2000)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 43, "", "! Font \\TU/lmr/m/n/10 not loadable")

    monkeypatch.setattr(generate_pdf_report.subprocess, "run", fake_run)
    assert generate_pdf_report.render_with_pandoc("# x\n", out) is True
    err = capsys.readouterr().err
    assert "Font" not in err
    assert "rendered with pdflatex (xelatex, lualatex failed" in err
