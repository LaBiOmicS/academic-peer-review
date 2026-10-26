from __future__ import annotations

import subprocess
import sys

import extract_paper
from conftest import SCRIPTS_DIR


def test_arxiv_ids_require_prefix():
    text = "Revenue grew 1203.4567 units; see arXiv:2301.12345 and arxiv.org/abs/1912.01234v2."
    assert extract_paper.ARXIV_REGEX.findall(text) == ["2301.12345", "1912.01234v2"]


def _run(path, out):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "extract_paper.py"), str(path), "--output-text", str(out)],
        capture_output=True,
        text=True,
    )


def test_unsupported_and_binary_inputs_are_rejected(tmp_path):
    doc = tmp_path / "paper.doc"
    doc.write_bytes(b"\xd0\xcf\x11\xe0binary")
    res = _run(doc, tmp_path / "o.txt")
    assert res.returncode == 1 and "unsupported input format" in res.stderr

    fake_txt = tmp_path / "paper.txt"
    fake_txt.write_bytes(b"PK\x03\x04\x00\x00binary zip")
    res = _run(fake_txt, tmp_path / "o.txt")
    assert res.returncode == 1 and "binary" in res.stderr
