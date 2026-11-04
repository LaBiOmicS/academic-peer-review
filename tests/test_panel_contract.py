from __future__ import annotations

import json
import sys

import pytest

import compile_results as cr
import spawn_reviewers

# --- Mixed-model panel ----------------------------------------------------------------------


def test_parse_panel_models():
    assert spawn_reviewers.parse_panel_models("claude:opus, agy ,sonnet,") == [
        ("claude", "opus"),
        ("agy", None),
        (None, "sonnet"),
    ]
    assert spawn_reviewers.parse_panel_models("") == []
    with pytest.raises(ValueError):
        spawn_reviewers.parse_panel_models("openai:gpt")


def test_assign_panel_models_cycles():
    entries = [("claude", "opus"), ("agy", None)]
    got = spawn_reviewers.assign_panel_models(["alfa", "beta", "gamma"], entries)
    assert got == {"alfa": ("claude", "opus"), "beta": ("agy", None), "gamma": ("claude", "opus")}
    assert spawn_reviewers.assign_panel_models(["alfa"], []) == {"alfa": (None, None)}


def test_manifest_records_runner_and_model(tmp_path, monkeypatch):
    paper = tmp_path / "p.txt"
    paper.write_text("Methods. We ran a randomized trial with 40 patients.", encoding="utf-8")
    skill_dir = spawn_reviewers.Path(spawn_reviewers.__file__).resolve().parent.parent
    monkeypatch.setattr(sys, "argv", [
        "spawn_reviewers.py", "--paper-text-file", str(paper), "--output-dir", str(tmp_path),
        "--skill-dir", str(skill_dir), "--num-reviewers", "3", "--panel-models", "claude:opus,agy",
        "--prepare-only",
    ])
    assert spawn_reviewers.main() == 0
    manifest = json.loads((tmp_path / ".prompts" / "panel_manifest.json").read_text(encoding="utf-8"))
    pairs = [(r["runner"], r["model"]) for r in manifest["reviewers"].values()]
    assert pairs == [("claude", "opus"), ("agy", None), ("claude", "opus")]


# --- Severity contract ----------------------------------------------------------------------

TAGGED = """### Summary
x

### Major concerns
1. **Issue** — A [Lens: x]
   - **Severity** — Blocking. Quote: "the claim".
2. **Issue** — B `[Severity: Essential]`
3. **Issue** — C
   - **Severity** — `Optional`

### Minor concerns
- y

### Verdict
**Major revision** — z.
"""


def test_review_contract_counts_tiers_and_flags_untagged():
    c = cr.review_contract(TAGGED)
    assert c["major_concerns"] == 3
    assert c["severity_counts"] == {"blocking": 1, "essential": 1, "optional": 1}
    assert c["issues"] == []
    c = cr.review_contract(TAGGED.replace("   - **Severity** — `Optional`\n", ""))
    assert c["untagged"] == 1 and "1 of 3 major concerns have no severity tier" in c["issues"]


def test_review_contract_flags_too_many_blocking():
    items = "".join(f"{i}. **Issue** — x\n   - **Severity** — Blocking.\n" for i in range(1, 8))
    c = cr.review_contract(f"### Major concerns\n{items}\n### Verdict\n**Reject**\n")
    assert any("7 Blocking concerns" in i for i in c["issues"])


GOOD_META = """## Blocking-concern verification
| a | b |

## Actionable Revision Roadmap
1. **Blocking**
   - [ ] one
2. **Essential**
   - [ ] two
3. **Optional**
   - [ ] three

## Verdict synthesis
**Minor revision.**
"""


def test_meta_contract_accepts_calibrated_meta_review():
    assert cr.meta_contract(GOOD_META, [{"concern": "x", "severity": "blocking"}]) == []


def test_meta_contract_flags_legacy_meta_review():
    legacy = (
        "## Actionable Revision Roadmap\n1. **Blocking / Must-Fix Requirements**\n"
        + "".join(f"   - [ ] item {i}\n" for i in range(9))
        + "2. **High-Impact Improvements**\n   - [ ] x\n\n## Verdict synthesis\nMajor.\n"
    )
    issues = cr.meta_contract(legacy, [{"concern": "x", "severity": ""}])
    assert "no '## Blocking-concern verification' section" in issues
    assert "roadmap does not use the Blocking / Essential / Optional tiers" in issues
    assert "roadmap lists 9 Blocking items (limit 5)" in issues
    assert "concerns matrix has rows without a severity tier" in issues
