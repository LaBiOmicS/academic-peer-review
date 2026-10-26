from __future__ import annotations

import py_compile
from pathlib import Path

import pytest

SCRIPTS = sorted((Path(__file__).resolve().parent.parent / "skills" / "paper-review" / "scripts").glob("*.py"))


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_script_compiles(script):
    # Regression: a SyntaxError in generate_pdf_report.py broke compile_results.py at import time.
    py_compile.compile(str(script), doraise=True)
