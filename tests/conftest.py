from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "paper-review" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must be hermetic: any real HTTP request fails loudly."""

    def _blocked(*args, **kwargs):
        raise AssertionError("Network access attempted during tests")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)
