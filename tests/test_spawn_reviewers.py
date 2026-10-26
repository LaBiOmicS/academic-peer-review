from __future__ import annotations

import spawn_reviewers
from spawn_reviewers import build_cli_cmd, build_sanitized_env


def test_default_runner_command_is_sandboxed():
    agy = build_cli_cmd("agy", "auto", "high")
    assert "--sandbox" in agy and "--dangerously-skip-permissions" in agy
    gem = build_cli_cmd("gemini", "auto", None)
    assert "--sandbox" in gem


def test_none_and_unsafe_policies():
    assert "--dangerously-skip-permissions" not in build_cli_cmd("agy", None, None, "none")
    assert "-y" not in build_cli_cmd("gemini", None, None, "none")
    unsafe = build_cli_cmd("agy", None, None, "unsafe")
    assert "--sandbox" not in unsafe and "--dangerously-skip-permissions" in unsafe


def test_env_scrubbing_keeps_runner_credentials(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "keep")
    monkeypatch.setenv("OPENAI_API_KEY", "drop")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "drop")
    monkeypatch.setenv("MY_SERVICE_TOKEN", "drop")
    monkeypatch.setenv("HOME_PATH_HINT", "keep")
    env = build_sanitized_env()
    assert env["GEMINI_API_KEY"] == "keep"
    assert env["HOME_PATH_HINT"] == "keep"
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MY_SERVICE_TOKEN"):
        assert k not in env


def test_journal_directive_rendered_once(tmp_path):
    template = tmp_path / "t.md"
    template.write_text("{area_rubric}\n---\n{paper_text}", encoding="utf-8")
    area_info = spawn_reviewers.classify_manuscript("Methods. We ran a randomized trial.")
    prompt = spawn_reviewers.build_prompt(
        template,
        reviewer_id="alfa",
        paper_text="{target_journal}",
        skill_dir=str(tmp_path),
        domain="x",
        area_info=area_info,
        audit_text="",
        entropy_hint="00",
        target_journal="The Lancet",
    )
    assert prompt.count("Target Journal & Scope Directive") == 1
    # single-pass rendering: placeholders inside the manuscript are not expanded
    assert prompt.rstrip().endswith("{target_journal}")
