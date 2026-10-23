---
name: paper-review
description: >-
  Use this skill when the user asks for a peer review, critique, methodological audit,
  red-team evaluation, or editorial meta-review of an academic paper (PDF, DOCX, LaTeX,
  Markdown, or text). Automatically classifies the manuscript across 3 orthogonal axes:
  5 Major Scientific Areas (Biológicas/Ômicas, Saúde, Exatas, Engenharias, Humanas),
  15 Article Types (Original, Systematic Review, Meta-Analysis, Umbrella, Scoping,
  Integrative, Narrative, Bibliometric, Consensus/Guideline, Case Study, Data Paper,
  Software Paper, Protocol, Essay/Perspective, Short Communication), and 12 Research
  Approaches (Clinical Interventional, Diagnostic/Biomarker, Epidemiological/Observational,
  Field/Ecological/Agronomic, Experimental Lab, Computational/In Silico, Quantitative,
  Qualitative, Mixed Methods, Action/Design Science, Documentary/Archival, Theoretical/Formal),
  plus SAGER and Clinical/Bio-AI transversal guidelines. Spawns N independent specialist
  reviewer subagents in parallel under Greek letter codenames (alfa, beta, gamma, …) and
  compiles an editorial meta-review, revision roadmap, CSV concerns matrix, and results.json.
---

# Academic Paper Peer Review (`gemini-peer-review`)

Multi-reviewer, 3-axis composable peer review and methodological audit system for **Gemini / Antigravity (`agy`)**.
Automatically detects three orthogonal dimensions of the manuscript and injects a compact (~12-line) micro-rubric into each reviewer prompt:
1. **Axis 1 — Major Scientific Area (`--area` — 5 options)**: `biologicas`, `saude`, `exatas`, `engenharias`, `humanas`.
2. **Axis 2 — Academic Article Type (`--article-type` — 15 options)**: `original_research`, `systematic_review`, `meta_analysis`, `umbrella_review`, `scoping_review`, `integrative_review`, `narrative_review`, `bibliometric_review`, `consensus_or_guideline`, `case_study`, `data_paper`, `software_paper`, `methods_or_protocol_paper`, `theoretical_essay_perspective`, `short_communication`.
3. **Axis 3 — Research Approach / Study Design (`--research-approach` — 12 options)**: `clinical_interventional`, `diagnostic_prognostic_biomarker`, `epidemiological_observational`, `field_ecological_agronomic`, `experimental_lab`, `computational_in_silico`, `quantitative_statistical`, `qualitative`, `mixed_methods`, `action_or_design_science`, `documentary_archival_historical`, `theoretical_formal_deductive`.
4. **Transversal Triggers**: `SAGER Guidelines` (sex/gender equity) and `Clinical/Bio-AI` (`TRIPOD+AI`, `CONSORT-AI`, `DECIDE-AI`, `CLAIM`).

For detailed notes on the 3-Axis Matrix, String Seed of Thought (SSoT), and audit internals, see [panel_and_audit_guide.md](./references/panel_and_audit_guide.md).

## Inputs

| Argument | Required | Default | Notes |
|---|---|---|---|
| `paper` | yes | — | Path to a `.pdf`, `.docx`, `.tex`, `.md`, or `.txt` manuscript. |
| `area` | no | `auto` | Major Scientific Area (`auto`, `biologicas`, `saude`, `exatas`, `engenharias`, `humanas`). |
| `article_type` | no | `auto` | Article Type (`auto` or any of the 15 article type codes). |
| `research_approach` | no | `auto` | Research Approach (`auto` or any of the 12 research approach codes). |
| `domain` | no | inferred | Specific scientific field (e.g. `"bioinformatics and genomics"`, `"constitutional law"`). |
| `num_reviewers` | no | `4` | Number of independent reviewers (`alfa`, `beta`, `gamma`, `delta`, …) to spawn (`3` to `8`). |
| `output_dir` | no | `./papers/<paper-stem>/` | Directory where all review artifacts are written. |
| `alignment_critic` | no | `true` | Includes an Area- and Genre-Adapted Epistemic Red-Team Critic in the panel. |
| `specialist_panel` | no | `true` | Includes specialized Methodological/Analytical and Reproducibility/Normative auditors alongside Domain Reviewers. |
| `verify_citations` | no | `true` | Queries OpenAlex during the pre-review audit to verify extracted DOIs and detect retracted papers. |
| `execution_mode` | no | `auto` | `subagents` (native Antigravity `invoke_subagent` parallel execution) or `cli` (`spawn_reviewers.py` parallel `agy -p` / `gemini -p` subprocesses). |
| `skip_meta` | no | `false` | If `true`, produces individual reviews and audit only. |
| `overwrite` | no | `false` | If `false`, reuses valid existing `review_<codename>.md` files. |

---

## Workflow

### Step 1. Extract Manuscript Text, Structural Metadata & 3-Axis Classification

Run [extract_paper.py](./scripts/extract_paper.py) to extract clean text, section coverage, figure/table captions, bibliography/accession identifiers, and automatic **Area × Article Type × Research Approach** classification:

```bash
python3 {skill_dir}/scripts/extract_paper.py \
  "<paper_path>" \
  --output-text "<output_dir>/paper_text.txt" \
  --output-meta "<output_dir>/paper_structure.json" \
  --area "<area>" \
  --article-type "<article_type>" \
  --research-approach "<research_approach>" \
  --domain "<domain>"
```

### Step 2. Run 3-Axis Pre-Review Audit (`statcheck` + Normative & Citation Integrity)

Run [stat_and_integrity_audit.py](./scripts/stat_and_integrity_audit.py) to execute statistical test consistency checks ($t, F, r, \chi^2, z$ vs reported $p$-values), article-type checks (`PRISMA`, `PRISMA-ScR`, `PRIOR/AMSTAR-2`, `SANRA`, `BIBLIO`, `AGREE II/ACCORD`, `CARE`, `FAIR`, `JOSS/FAIR4RS`, `SPIRIT`), research-approach checks (`CONSORT`, `STARD/TRIPOD/REMARK`, `STROBE`, `ARRIVE`, `COREQ/SRQR`, `GRAMMS`), area-specific checks, and live DOI/retraction verification:

```bash
python3 {skill_dir}/scripts/stat_and_integrity_audit.py \
  --paper-text-file "<output_dir>/paper_text.txt" \
  --output-json "<output_dir>/pre_review_audit.json" \
  --output-md "<output_dir>/pre_review_audit.md" \
  --area "<area>" \
  --article-type "<article_type>" \
  --research-approach "<research_approach>" \
  --domain "<domain>" \
  --verify-citations
```

### Step 3. Spawn 3-Axis Specialized Reviewers in Parallel

#### Path A (Recommended inside interactive Antigravity sessions): Native Parallel Subagents (`invoke_subagent`)
1. Prepare the anonymized, specialized prompts and panel manifest:
   ```bash
   python3 {skill_dir}/scripts/spawn_reviewers.py \
     --paper-text-file "<output_dir>/paper_text.txt" \
     --audit-file "<output_dir>/pre_review_audit.md" \
     --output-dir "<output_dir>" \
     --skill-dir "{skill_dir}" \
     --num-reviewers <N> \
     --area "<area>" \
     --article-type "<article_type>" \
     --research-approach "<research_approach>" \
     --domain "<domain>" \
     --prepare-only
   ```
2. For each Greek letter codename (`alfa`, `beta`, `gamma`, `delta`, …) in `<output_dir>/.prompts/panel_manifest.json`, call `invoke_subagent` **in a single parallel tool turn** (`TypeName="peer-reviewer"` — or `"self"` — with `Model="inherit"`).

#### Path B (Headless CLI / Subprocess Parallelism): Direct OS Subprocesses via `spawn_reviewers.py`
```bash
python3 {skill_dir}/scripts/spawn_reviewers.py \
  --paper-text-file "<output_dir>/paper_text.txt" \
  --audit-file "<output_dir>/pre_review_audit.md" \
  --output-dir "<output_dir>" \
  --skill-dir "{skill_dir}" \
  --num-reviewers <N> \
  --area "<area>" \
  --article-type "<article_type>" \
  --research-approach "<research_approach>" \
  --domain "<domain>" \
  --runner auto \
  --effort high \
  $([ "<alignment_critic>" = "false" ] && echo --no-alignment-critic) \
  $([ "<specialist_panel>" = "false" ] && echo --no-specialist-panel) \
  $([ "<overwrite>" = "true" ] && echo --overwrite)
```

### Step 4. Synthesize the Editorial Meta-Review

Read all `<output_dir>/review_<codename>.md` files, `<output_dir>/pre_review_audit.md`, and [metareview.md](./prompts/metareview.md), then write the synthesized editorial meta-review to `<output_dir>/meta_review.md`.

### Step 5. Compile Final Bundle & Concerns Matrix

```bash
python3 {skill_dir}/scripts/compile_results.py --output-dir "<output_dir>"
```

### Step 6. Present Results & Verdict Table to the User

State the detected **Major Scientific Area**, **Article Type**, and **Research Approach**, display the compact per-reviewer verdict table (`alfa`, `beta`, `gamma`, `delta`, …), and link to all generated artifacts.
