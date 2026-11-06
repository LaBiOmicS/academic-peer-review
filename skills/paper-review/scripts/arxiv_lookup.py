#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Batched arXiv identifier lookup (export.arxiv.org API), used to audit reviewer citations.

The API silently drops identifiers that do not exist, so an ID is *unresolvable* only when its
batch request succeeded and the ID did not come back. IDs whose request failed are *unchecked*,
never accused of being fabricated. Version suffixes (``v2``) are ignored when matching.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

USER_AGENT = "academic-peer-review/1.4.0 (LaBiOmicS - UMC; mailto:fabianomenegidio@umc.br)"
API_URL = "https://export.arxiv.org/api/query"
BATCH_SIZE = 50
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
# New-style (2310.12345) and old-style (hep-ex/0111081, math.AG/0101001) identifiers.
ARXIV_ID_REGEX = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})$")


def normalize_arxiv_id(raw: str) -> str | None:
    """Return the bare, version-less identifier (``2310.12345``), or None if malformed."""
    s = re.sub(r"^(?:arxiv:\s*|https?://arxiv\.org/abs/)", "", raw.strip(), flags=re.IGNORECASE)
    s = re.sub(r"v\d+$", "", s.rstrip(".,;)]}"))
    return s if ARXIV_ID_REGEX.match(s) else None


def _parse_feed(xml_bytes: bytes) -> dict[str, dict[str, Any]]:
    head = xml_bytes[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise ValueError("XML DTD/ENTITY declarations are forbidden (XXE protection).")
    root = ET.fromstring(xml_bytes)
    works: dict[str, dict[str, Any]] = {}
    for entry in root.findall("atom:entry", ATOM_NS):
        raw_id = (entry.findtext("atom:id", default="", namespaces=ATOM_NS) or "").strip()
        if "/abs/" not in raw_id:
            continue  # the API reports malformed IDs as error entries
        ident = normalize_arxiv_id(raw_id.rsplit("/abs/", 1)[-1])
        if ident:
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").split())
            year = (entry.findtext("atom:published", default="", namespaces=ATOM_NS) or "")[:4]
            works[ident] = {"arxiv_id": ident, "title": title[:300] or None, "year": int(year) if year.isdigit() else None}
    return works


def _fetch(ids: list[str], timeout: float) -> bytes:
    params = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": len(ids)})
    req = urllib.request.Request(f"{API_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_RESPONSE_BYTES)


def lookup_arxiv_ids(ids: list[str], *, max_checks: int = 100, timeout: float = 15.0) -> dict[str, Any]:
    """Return ``{"found": {id: work}, "unresolvable": [id], "unchecked": [id], "invalid": [raw]}``."""
    ordered: list[str] = []
    invalid: list[str] = []
    for raw in ids:
        ident = normalize_arxiv_id(raw)
        if ident is None:
            invalid.append(raw)
        elif ident not in ordered:
            ordered.append(ident)

    found: dict[str, dict[str, Any]] = {}
    unresolvable: list[str] = []
    unchecked: list[str] = list(ordered[max_checks:])
    targets = ordered[:max_checks]
    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i : i + BATCH_SIZE]
        try:
            returned = _parse_feed(_fetch(batch, timeout))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, ET.ParseError):
            unchecked.extend(batch)
            continue
        for ident in batch:
            if ident in returned:
                found[ident] = returned[ident]
            else:
                unresolvable.append(ident)
    return {"found": found, "unresolvable": unresolvable, "unchecked": unchecked, "invalid": invalid}
