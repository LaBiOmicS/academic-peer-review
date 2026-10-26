#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""arXiv & multi-source literature search helper (delegates to hardened literature_search.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literature_search import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
