#!/usr/bin/env python3
"""Spawn N independent peer reviewer agents in parallel with 3-Axis Specialization & Security Hardening.

Designed for Gemini / Antigravity (`agy`):
1. Multi-runner support (`--runner auto|agy|gemini`).
2. Greek letter reviewer codenames (`alfa`, `beta`, `gamma`, `delta`, `epsilon`, `zeta`, `eta`, `theta`).
3. 3-Axis Composable Classification (`5 Areas × 15 Article Types × 12 Research Approaches`).
4. Information Security Hardening:
   - Single-pass regex template rendering (prevents cross-placeholder template injection).
   - Cryptographic CSPRNG (`secrets.SystemRandom`) for archetype assignment and SSoT entropy hints.
   - Manuscript sanitization (`sanitize_and_scan_manuscript`) & `<UNTRUSTED_MANUSCRIPT_CONTENT>` sandboxing.
   - Subprocess timeout enforcement (`--timeout-seconds`, default 600s) and secret environment variable scrubbing.
   - Restrictive `0o700` permissions on `.prompts/` directory.
   - Reviewer CLIs run sandboxed by default (`--tool-permissions sandboxed`); the manuscript is untrusted
     input, so unsandboxed auto-approval (`unsafe`) must be requested explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal_scope import clean_journal_name  # noqa: E402
from area_profiles import (  # noqa: E402
    ARTICLE_TYPE_DEFINITIONS,
    RESEARCH_APPROACH_DEFINITIONS,
    classify_manuscript,
    compose_rubric,
    get_area_profile,
    get_article_type_profile,
    get_research_approach_profile,
    sanitize_and_scan_manuscript,
)


GREEK = ["alfa", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
CSPRNG = secrets.SystemRandom()

SCRUBBED_ENV_VARS = {
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "NPM_TOKEN",
    "PYPI_API_TOKEN",
    "DATABASE_URL",
    "PGPASSWORD",
    "MYSQL_PWD",
    "SLACK_BOT_TOKEN",
    "STRIPE_SECRET_KEY",
    "SSH_AUTH_SOCK",
}
# Any variable whose name looks like a credential is removed, except the ones the runners need.
SECRET_NAME_REGEX = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY|ACCESS_KEY|CREDENTIAL)", re.I)
RUNNER_ENV_ALLOWLIST = {
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_VERTEXAI",
}


def detect_runner(requested: str) -> str:
    if requested != "auto":
        if not shutil.which(requested):
            raise RuntimeError(f"Requested runner '{requested}' not found in PATH.")
        return requested
    for candidate in ("agy", "gemini"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError("No supported CLI runner ('agy' or 'gemini') found in PATH.")


def build_cli_cmd(
    runner: str, model: str | None, effort: str | None, tool_permissions: str = "sandboxed"
) -> list[str]:
    """Build the reviewer CLI command.

    tool_permissions:
      - "sandboxed" (default): auto-approve tools, but inside the runner's terminal sandbox.
      - "none": no auto-approval; tools needing permission are not run (literature search may be skipped).
      - "unsafe": auto-approve tools without a sandbox (only for trusted manuscripts).
    """
    if runner == "agy":
        cmd = ["agy"]
        if tool_permissions == "sandboxed":
            cmd.extend(["--sandbox", "--dangerously-skip-permissions"])
        elif tool_permissions == "unsafe":
            cmd.append("--dangerously-skip-permissions")
        cmd.append("-p")
        if model and model not in ("auto", "default", "inherit"):
            cmd.extend(["--model", model])
        if effort:
            cmd.extend(["--effort", effort])
        return cmd
    if runner == "gemini":
        cmd = ["gemini"]
        if tool_permissions == "sandboxed":
            cmd.extend(["--sandbox", "-y"])
        elif tool_permissions == "unsafe":
            cmd.append("-y")
        cmd.extend(["-p", ""])
        if model and model not in ("auto", "default", "inherit"):
            cmd.extend(["-m", model])
        return cmd
    raise ValueError(f"Unsupported runner: {runner}")


def build_sanitized_env() -> dict[str, str]:
    env = os.environ.copy()
    for k in list(env.keys()):
        if k in RUNNER_ENV_ALLOWLIST:
            continue
        if k in SCRUBBED_ENV_VARS or SECRET_NAME_REGEX.search(k):
            env.pop(k, None)
    return env


def assign_templates(
    n: int,
    skill_dir: Path,
    *,
    alignment_critic: bool = True,
    specialist_panel: bool = True,
) -> list[tuple[str, Path]]:
    prompts_dir = skill_dir / "prompts"
    standard = ("domain-reviewer", prompts_dir / "reviewer.md")
    af_critic = ("epistemic-redteam-critic", prompts_dir / "reviewer_alignment_forum.md")
    stats_auditor = ("methodology-stats-auditor", prompts_dir / "reviewer_methodology_stats.md")
    repro_inspector = ("reproducibility-integrity-inspector", prompts_dir / "reviewer_reproducibility_integrity.md")

    slots: list[tuple[str, Path]] = []
    if alignment_critic and af_critic[1].exists():
        slots.append(af_critic)
    if specialist_panel and n >= 3 and stats_auditor[1].exists():
        slots.append(stats_auditor)
    if specialist_panel and n >= 4 and repro_inspector[1].exists():
        slots.append(repro_inspector)

    while len(slots) < n:
        slots.append(standard)

    slots = slots[:n]
    CSPRNG.shuffle(slots)
    return slots


def build_prompt(
    template: Path,
    *,
    reviewer_id: str,
    paper_text: str,
    skill_dir: str,
    domain: str,
    area_info: dict[str, Any],
    audit_text: str,
    entropy_hint: str,
    target_journal: str = "",
) -> str:
    area_profile = get_area_profile(area_info["area_code"])
    type_code = area_info["article_type"]["type_code"]
    type_profile = get_article_type_profile(type_code)
    approach_code = area_info["research_approach"]["approach_code"]
    approach_profile = get_research_approach_profile(approach_code)

    lenses_block = "\n".join(f"- {ln}" for ln in area_profile["ssot_lenses"])
    redteam_block = "\n".join(f"- {ax}" for ax in area_profile["redteam_axes"])
    composed_rubric = compose_rubric(area_info)
    study_design_label = (
        f"{approach_profile['name']} [{approach_code}] | "
        f"Article Type: {type_profile['name']} [{type_code}]"
    )

    journal_scope_directive = ""
    if target_journal:
        journal_scope_directive = (
            f"- **Target Journal & Scope Directive (`{target_journal}`)**: "
            f"Specifically evaluate whether this manuscript fits the editorial aims, scope, and technical depth of **{target_journal}**. "
            f"Explicitly note in your evaluation if the paper faces risk of editorial desk-rejection due to scope mismatch, "
            f"insufficient novelty for this specific outlet, or violation of key journal submission policies.\n"
        )
        composed_rubric = composed_rubric + "\n" + journal_scope_directive

    replacements = {
        "reviewer_id": reviewer_id,
        "skill_dir": skill_dir,
        "domain": domain,
        "target_journal": target_journal,
        "target_journal_scope_directive": journal_scope_directive,
        "area_code": area_info["area_code"],
        "area_name": area_info["area_name"],
        "study_design": study_design_label,
        "article_type_code": type_code,
        "article_type_name": type_profile["name"],
        "research_approach_code": approach_code,
        "research_approach_name": approach_profile["name"],
        "area_ssot_lenses": lenses_block,
        "area_redteam_axes": redteam_block,
        "area_rubric": composed_rubric,
        "entropy_hint": entropy_hint,
        "pre_review_audit": audit_text,
        "paper_text": paper_text,
    }

    text = template.read_text(encoding="utf-8")
    pattern = re.compile(r"\{(" + "|".join(re.escape(k) for k in replacements) + r")\}")
    return pattern.sub(lambda m: replacements[m.group(1)], text)


def validate_review_content(content: str) -> tuple[bool, bool, int]:
    size = len(content)
    has_verdict = any(
        marker in content
        for marker in ("## Verdict", "### Verdict", "**Verdict**", "## 4. Verdict", "### 5. Verdict")
    )
    is_valid = size >= 600 and has_verdict
    return is_valid, has_verdict, size


def main() -> int:
    p = argparse.ArgumentParser(description="Spawn 3-axis specialized parallel peer reviewers.")
    p.add_argument("--paper-text-file", required=True, help="Path to extracted paper text.")
    p.add_argument("--output-dir", required=True, help="Directory where review_<codename>.md files are written.")
    p.add_argument("--skill-dir", required=True, help="Root directory of the paper-review skill.")
    p.add_argument("--num-reviewers", type=int, default=4, help="Number of reviewers (3 to 8, default 4).")
    p.add_argument("--alignment-critic", dest="alignment_critic", action="store_true", default=True)
    p.add_argument("--no-alignment-critic", dest="alignment_critic", action="store_false")
    p.add_argument("--specialist-panel", dest="specialist_panel", action="store_true", default=True)
    p.add_argument("--no-specialist-panel", dest="specialist_panel", action="store_false")
    p.add_argument("--audit-file", help="Optional path to pre_review_audit.md to include as context.")
    p.add_argument(
        "--area",
        choices=["auto", "biologicas", "saude", "exatas", "engenharias", "humanas"],
        default="auto",
        help="Major Scientific Area override or auto-detect (default: auto).",
    )
    p.add_argument(
        "--article-type",
        choices=["auto"] + list(ARTICLE_TYPE_DEFINITIONS.keys()),
        default="auto",
        help="Academic Article Type override or auto-detect (default: auto).",
    )
    p.add_argument(
        "--research-approach",
        choices=["auto"] + list(RESEARCH_APPROACH_DEFINITIONS.keys()),
        default="auto",
        help="Research Approach override or auto-detect (default: auto).",
    )
    p.add_argument("--domain", default="", help="Specific scientific domain (inferred from area/text if omitted).")
    p.add_argument("--journal", "--target-journal", dest="journal", default="", help="Target journal name for aims & scope validation.")
    p.add_argument(
        "--paper-meta",
        help="Optional paper_structure.json from extract_paper.py; its inferred target_journal is used when --journal is empty.",
    )
    p.add_argument(
        "--tool-permissions",
        choices=["sandboxed", "none", "unsafe"],
        default="sandboxed",
        help="Tool approval policy for reviewer CLIs (default: sandboxed). 'unsafe' disables the sandbox.",
    )
    p.add_argument("--runner", choices=["auto", "agy", "gemini"], default="auto")
    p.add_argument("--model", default="auto", help="Model override (default: auto/inherit).")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="high")
    p.add_argument("--stagger-seconds", type=float, default=6.0, help="Stagger delay between spawns (default 6s).")
    p.add_argument("--timeout-seconds", type=float, default=600.0, help="Per-reviewer subprocess timeout in seconds (default 600s).")
    p.add_argument("--max-retries", type=int, default=1, help="Retries for failed or truncated reviewers.")
    p.add_argument("--prepare-only", action="store_true", help="Only write rendered prompts & manifest (for native subagents).")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing review_<codename>.md files.")
    args = p.parse_args()

    n = max(3, min(8, args.num_reviewers))
    codenames = GREEK[:n]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompts_out_dir = output_dir / ".prompts"
    prompts_out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(prompts_out_dir, 0o700)
    except OSError:
        pass

    skill_dir = Path(args.skill_dir).resolve()
    paper_file = Path(args.paper_text_file).resolve()
    if not paper_file.exists() or not paper_file.is_file():
        print(f"Error: Paper text file not found: {paper_file}", file=sys.stderr)
        return 1
    if not skill_dir.exists() or not skill_dir.is_dir():
        print(f"Error: Skill directory not found: {skill_dir}", file=sys.stderr)
        return 1
    raw_paper_text = paper_file.read_text(encoding="utf-8", errors="replace")
    paper_text, security_scan = sanitize_and_scan_manuscript(raw_paper_text)

    area_info = classify_manuscript(
        paper_text,
        domain_hint=args.domain,
        explicit_area=args.area,
        explicit_article_type=args.article_type,
        explicit_research_approach=args.research_approach,
    )
    type_code = area_info["article_type"]["type_code"]
    approach_code = area_info["research_approach"]["approach_code"]
    effective_domain = (
        args.domain.strip()
        if args.domain.strip()
        else f"{area_info['area_name']} — {area_info['article_type']['type_name']} ({area_info['research_approach']['approach_name']})"
    )

    target_journal = clean_journal_name(args.journal)
    if not target_journal and args.paper_meta and Path(args.paper_meta).is_file():
        try:
            meta = json.loads(Path(args.paper_meta).read_text(encoding="utf-8"))
            target_journal = clean_journal_name(meta.get("target_journal"))
        except (OSError, ValueError):
            pass

    audit_text = "No pre-review automated audit was supplied."
    if args.audit_file and Path(args.audit_file).exists():
        audit_text = Path(args.audit_file).resolve().read_text(encoding="utf-8", errors="replace")

    assigned = assign_templates(
        n,
        skill_dir,
        alignment_critic=args.alignment_critic,
        specialist_panel=args.specialist_panel,
    )

    manifest: dict[str, Any] = {
        "domain": effective_domain,
        "target_journal": target_journal or None,
        "security_scan": security_scan,
        "scientific_area": area_info,
        "num_reviewers": n,
        "reviewers": {},
    }

    rendered_prompts: dict[str, str] = {}
    for i, code in enumerate(codenames):
        role_name, template_path = assigned[i]
        slot_byte = ((i * 37 + CSPRNG.randrange(1, 250)) % 256)
        entropy_hint = f"{slot_byte:02x}{secrets.token_hex(15)}"
        prompt = build_prompt(
            template_path,
            reviewer_id=code,
            paper_text=paper_text,
            skill_dir=str(skill_dir),
            domain=effective_domain,
            area_info=area_info,
            audit_text=audit_text,
            entropy_hint=entropy_hint,
            target_journal=target_journal,
        )
        prompt_file = prompts_out_dir / f"prompt_{code}.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        rendered_prompts[code] = prompt
        manifest["reviewers"][code] = {
            "codename": code,
            "archetype": role_name,
            "area_code": area_info["area_code"],
            "article_type": type_code,
            "research_approach": approach_code,
            "study_design": approach_code,
            "template": template_path.name,
            "prompt_file": str(prompt_file),
            "output_file": str(output_dir / f"review_{code}.md"),
            "entropy_hint": entropy_hint,
        }

    manifest_path = prompts_out_dir / "panel_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.prepare_only:
        print(
            f"[spawn_reviewers] Prepared {n} prompts (Area={area_info['area_code']} | Type={type_code} | Approach={approach_code}) in {prompts_out_dir}",
            file=sys.stderr,
            flush=True,
        )
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    runner = detect_runner(args.runner)
    cmd_base = build_cli_cmd(runner, args.model, args.effort, args.tool_permissions)
    if args.tool_permissions == "unsafe":
        print(
            "[spawn_reviewers] WARNING: --tool-permissions unsafe auto-approves tools without a sandbox; "
            "a prompt injection in the manuscript could run commands on this machine.",
            file=sys.stderr,
            flush=True,
        )
    print(
        f"[spawn_reviewers] Area='{area_info['area_code']}' | Type='{type_code}' | Approach='{approach_code}' | runner='{runner}' | tools='{args.tool_permissions}'",
        file=sys.stderr,
        flush=True,
    )

    start = time.time()
    clean_env = build_sanitized_env()

    def launch_batch(target_codes: list[str], attempt: int = 1) -> list[str]:
        procs: list[tuple[str, subprocess.Popen[str], Any, Any, Path]] = []
        spawn_count = 0
        for code in target_codes:
            out_path = output_dir / f"review_{code}.md"
            if attempt == 1 and out_path.exists() and not args.overwrite:
                content = out_path.read_text(encoding="utf-8", errors="replace")
                ok, _, _ = validate_review_content(content)
                if ok:
                    print(f"[spawn_reviewers] skip {code} (valid review exists, --overwrite not set)", file=sys.stderr, flush=True)
                    continue
            if spawn_count > 0 and args.stagger_seconds > 0:
                time.sleep(args.stagger_seconds)
            spawn_count += 1
            out_fh = open(out_path, "w", encoding="utf-8")
            # stderr goes to a file, not a PIPE: an unread pipe fills up (~64 KB) and deadlocks the child.
            err_fh = open(prompts_out_dir / f"stderr_{code}.log", "w+", encoding="utf-8")
            proc = subprocess.Popen(
                cmd_base,
                stdin=subprocess.PIPE,
                stdout=out_fh,
                stderr=err_fh,
                text=True,
                env=clean_env,
            )
            assert proc.stdin is not None
            try:
                proc.stdin.write(rendered_prompts[code])
                proc.stdin.close()
            except BrokenPipeError:
                pass  # child exited early; reported below via its return code
            elapsed = time.time() - start
            t_name = manifest["reviewers"][code]["template"]
            print(
                f"[spawn_reviewers] {code} started (attempt={attempt}, pid={proc.pid}, template={t_name}, t+{elapsed:.1f}s)",
                file=sys.stderr,
                flush=True,
            )
            procs.append((code, proc, out_fh, err_fh, out_path))

        failed: list[str] = []
        deadline_base = time.time()
        for code, proc, out_fh, err_fh, out_path in procs:
            # Every reviewer gets the same wall-clock budget, measured from batch start.
            remaining = max(1.0, args.timeout_seconds - (time.time() - deadline_base))
            try:
                rc = proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                out_fh.close()
                err_fh.close()
                elapsed = time.time() - start
                print(
                    f"[spawn_reviewers] {code} TIMEOUT after {args.timeout_seconds}s (attempt={attempt}, t+{elapsed:.1f}s)",
                    file=sys.stderr,
                    flush=True,
                )
                failed.append(code)
                continue

            out_fh.close()
            err_fh.seek(0)
            err = err_fh.read()
            err_fh.close()
            elapsed = time.time() - start
            if rc != 0:
                print(
                    f"[spawn_reviewers] {code} FAIL rc={rc} (attempt={attempt}, t+{elapsed:.1f}s): {err[:500]}",
                    file=sys.stderr,
                    flush=True,
                )
                failed.append(code)
                continue
            content = out_path.read_text(encoding="utf-8", errors="replace")
            ok, has_verdict, size = validate_review_content(content)
            if not ok:
                print(
                    f"[spawn_reviewers] {code} FAIL_CONTENT (attempt={attempt}, t+{elapsed:.1f}s, size={size}, has_verdict={has_verdict})",
                    file=sys.stderr,
                    flush=True,
                )
                failed.append(code)
                continue
            print(f"[spawn_reviewers] {code} OK (attempt={attempt}, t+{elapsed:.1f}s, size={size})", file=sys.stderr, flush=True)
        return failed

    failed_codes = launch_batch(codenames, attempt=1)
    attempt_num = 1
    while failed_codes and attempt_num <= args.max_retries:
        attempt_num += 1
        print(
            f"[spawn_reviewers] Retrying failed reviewers (attempt {attempt_num}): {', '.join(failed_codes)}",
            file=sys.stderr,
            flush=True,
        )
        failed_codes = launch_batch(failed_codes, attempt=attempt_num)

    return 1 if failed_codes else 0


if __name__ == "__main__":
    sys.exit(main())
