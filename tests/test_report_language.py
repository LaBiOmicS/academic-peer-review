"""The report follows the manuscript's language (pt, en, es; en for any other language)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import compile_results
from conftest import SCRIPTS_DIR
from generate_pdf_report import assemble_consolidated_markdown
from i18n import (
    CHECK_LABELS,
    CLASS_NAMES,
    M,
    detect_language,
    language_of,
    localize_markdown,
    report_language,
    status_label,
    t,
)
from test_compile_results import _run

PT = (
    "Este estudo avaliou a expressão gênica de plantas submetidas ao estresse hídrico. Os dados foram "
    "analisados com testes estatísticos e não foram encontradas diferenças entre os grupos, que também "
    "são descritos na seção de métodos. A população de estudo foi composta por amostras coletadas em campo."
)
EN = (
    "This study evaluated the gene expression of plants under drought stress. The data were analysed with "
    "statistical tests, and no differences were found between the groups that are described in the methods."
)
ES = (
    "Este estudio evaluó la expresión génica de plantas sometidas a estrés hídrico. Los datos fueron "
    "analizados con pruebas estadísticas y no se encontraron diferencias entre los grupos, que se describen "
    "en la sección de métodos. La población del estudio estuvo compuesta por muestras recolectadas en campo."
)
FR = (
    "Cette étude a évalué l'expression des gènes chez les plantes soumises au stress hydrique. Les données "
    "ont été analysées avec des tests statistiques et nous avons observé que les groupes sont différents dans "
    "les deux conditions, pour une population qui est décrite dans la section des méthodes."
)


@pytest.mark.parametrize(("text", "code"), [(PT, "pt"), (EN, "en"), (ES, "es"), (FR, "fr")])
def test_detect_language(text, code):
    assert detect_language(text)["code"] == code


def test_report_language_falls_back_to_english():
    assert report_language("auto", "pt") == "pt"
    assert report_language("auto", "es") == "es"
    assert report_language("auto", "fr") == "en"
    assert report_language("auto", "unknown") == "en"
    assert report_language("es", "pt") == "es"  # an explicit choice wins


def test_catalogs_are_complete():
    assert all(len(row) == 3 and all(row) for row in M.values())
    assert all(len(row) == 2 and all(row) for row in CHECK_LABELS.values())
    sys.path.insert(0, str(SCRIPTS_DIR))
    from area_profiles import AREA_DEFINITIONS, ARTICLE_TYPE_DEFINITIONS, RESEARCH_APPROACH_DEFINITIONS

    codes = set(AREA_DEFINITIONS) | set(ARTICLE_TYPE_DEFINITIONS) | set(RESEARCH_APPROACH_DEFINITIONS)
    assert codes <= set(CLASS_NAMES)


def test_every_check_key_has_a_translation():
    import stat_and_integrity_audit as audit

    text = "We used PRISMA and searched Scopus. " * 5
    keys = set()
    for code in ("systematic_review", "meta_analysis", "scoping_review", "umbrella_review", "bibliometric_review",
                 "integrative_review", "narrative_review", "consensus_or_guideline", "data_paper", "software_paper",
                 "case_study", "methods_or_protocol_paper"):
        keys |= set(audit.check_article_type_markers(text, code))
    from area_profiles import RESEARCH_APPROACH_DEFINITIONS

    for code in RESEARCH_APPROACH_DEFINITIONS:
        keys |= set(audit.check_research_approach_markers(text, code))
    for area in ("biologicas", "saude", "exatas", "engenharias", "humanas"):
        keys |= set(audit.check_area_specific_markers(text, area, "experimental")["area_specific_checks"])
    assert keys and keys <= set(CHECK_LABELS)


def test_status_phrases_are_translated():
    assert status_label("Critical Desk-Reject Risk", "pt") == "Risco crítico de desk reject"
    assert status_label("Open & FAIR — Public repository, DOIs, or accessions provided (3 targets found)", "es").startswith("Abierto y FAIR")
    assert status_label("Evasive — Author used 'upon request' instead of open deposition", "pt") == (
        "Evasivo — os autores usaram 'upon request' em vez de depósito aberto"
    )
    assert status_label("Critical Desk-Reject Risk", "en") == "Critical Desk-Reject Risk"
    assert status_label("Something new", "pt") == "Something new"


def test_localize_markdown_translates_parsing_labels_only():
    review = (
        "## Summary\nO estudo é bom.\n\n### Major concerns\n1. **Issue** — amostra pequena `[Severity: Blocking]`.\n"
        "- **Severity** — `Essential`\n\n### Verdict\n**Major revision** — falta poder estatístico.\n"
        "- **alfa** — Minor revision *(Lens: x)*\n"
    )
    pt = localize_markdown(review, "pt")
    assert "## Síntese" in pt and "### Questões principais" in pt and "### Parecer" in pt
    assert "**Revisão maior**" in pt and "**alfa** — Revisão menor" in pt
    assert "[Severidade: Impeditivo]" in pt and "`Essencial`" in pt
    assert "O estudo é bom." in pt
    assert localize_markdown(review, "en") == review
    es = localize_markdown(review, "es")
    assert "### Dictamen" in es and "**Revisión mayor**" in es


def _audit(lang):
    import stat_and_integrity_audit as audit

    data = {
        "scientific_area": {
            "area_code": "biologicas", "area_name": "Ciências Biológicas, Ômicas, Bioinformática & Ciências Agrárias",
            "matched_signals": [], "transversal_flags": {},
            "article_type": {"type_code": "systematic_review", "type_name": "Revisão Sistemática sem Metanálise (PRISMA 2020 / SWiM)", "guidelines": ["PRISMA"]},
            "research_approach": {"approach_code": "quantitative_statistical", "approach_name": "x", "guidelines": []},
        },
        "statcheck": {"tests_checked": 1, "inconsistencies_count": 0, "decision_errors_count": 0,
                      "fragile_p_values_001_to_005_count": 0, "inconsistencies": [], "decision_errors": []},
        "methodological_markers": {"area_specific_checks": {"batch_effect_assessed": False}, "power_or_sample_size_justification": True,
                                   "multiple_comparison_correction": False, "effect_size_reported": False,
                                   "confidence_intervals_or_error_bars": False, "code_or_data_links": [], "reporting_guidelines": []},
        "article_type_checks": {"prisma_guideline_cited": True, "search_date_reported": "Only in supplementary material"},
        "reproducibility_and_fair_audit": {"data_status": "Missing — No dedicated data/code availability statement or repository link detected"},
        "journal_scope_audit": {"target_journal": "PeerJ", "fit_category": "Borderline / Questionable Scope Adherence",
                                "desk_reject_risk": "High Risk of Desk Reject", "adherence_score_pct": 40},
    }
    return audit.format_markdown_report(data, lang)


def test_audit_markdown_in_portuguese_and_spanish():
    pt = _audit("pt")
    assert pt.startswith("# Auditoria diagnóstica automática pré-revisão")
    assert "Ciências Biológicas" in pt and "**Diretriz PRISMA citada**: Sim" in pt
    assert "**Data da busca relatada**: Só no material suplementar" in pt
    assert "Ausente — nenhuma declaração" in pt and "Risco alto de desk reject" in pt
    assert "## Aderência ao escopo do periódico-alvo" in pt
    assert "Yes" not in pt and "Desk-Reject Risk Assessment" not in pt
    es = _audit("es")
    assert "Biological" not in es and "Ciencias Biológicas" in es and "**Guía PRISMA citada**: Sí" in es
    en = _audit("en")
    assert "Biological Sciences, Omics" in en and "**Prisma guideline cited**: Yes" in en


def test_extraction_records_the_language(tmp_path):
    paper = tmp_path / "artigo.md"
    paper.write_text("# Resumo\n\n" + PT * 20, encoding="utf-8")
    out = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "extract_paper.py"), str(paper), "--output-text", str(tmp_path / "paper_text.txt"),
         "--output-meta", str(tmp_path / "paper_structure.json")],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode in (0, 2), out.stderr
    meta = json.loads((tmp_path / "paper_structure.json").read_text(encoding="utf-8"))
    assert meta["language"] == "pt" and meta["report_language"] == "pt"
    assert language_of(tmp_path) == "pt"


def test_reviewer_prompts_name_the_report_language(tmp_path):
    (tmp_path / "paper_text.txt").write_text(ES * 30, encoding="utf-8")
    (tmp_path / "paper_structure.json").write_text(json.dumps({"language": "es", "report_language": "es"}), encoding="utf-8")
    skill = SCRIPTS_DIR.parent
    out = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "spawn_reviewers.py"), "--paper-text-file", str(tmp_path / "paper_text.txt"),
         "--output-dir", str(tmp_path), "--skill-dir", str(skill), "--num-reviewers", "3",
         "--paper-meta", str(tmp_path / "paper_structure.json"), "--prepare-only"],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, out.stderr
    prompts = sorted((tmp_path / ".prompts").glob("prompt_*.md"))
    assert prompts and all("formal academic **Spanish**" in p.read_text(encoding="utf-8") for p in prompts)
    assert "{output_language}" not in prompts[0].read_text(encoding="utf-8")
    assert json.loads((tmp_path / ".prompts" / "panel_manifest.json").read_text())["report_language"] == "es"


META_PT = """## Per-reviewer verdicts
- **alfa** — Major revision

## Statistical, Provenance & Reproducibility Audit Highlights
Sem achados graves.

## Actionable Revision Roadmap
1. **Blocking**
   - Informar o tamanho amostral.
2. **Essential**
   - Depositar os dados.
3. **Optional**
   - Ampliar a amostra.

## Verdict synthesis
**Major revision** — o tamanho amostral não sustenta a conclusão.

## CONCERNS_TABLE_DATA

```json
{"concerns": [{"concern": "Tamanho amostral", "severity": "blocking", "alfa": "major", "beta": false}]}
```
"""


def test_compiled_bundle_in_portuguese(tmp_path, monkeypatch):
    from test_compile_results import REVIEW

    (tmp_path / "paper_structure.json").write_text(json.dumps({"language": "pt", "report_language": "pt"}), encoding="utf-8")
    (tmp_path / "pre_review_audit.json").write_text(json.dumps({
        "statcheck": {"tests_checked": 2, "inconsistencies_count": 1, "decision_errors_count": 0},
        "reproducibility_and_fair_audit": {"data_status": "Missing — No dedicated data/code availability statement or repository link detected"},
    }), encoding="utf-8")
    (tmp_path / "review_alfa.md").write_text(REVIEW.format(seed="a" * 32, verdict="Major revision"), encoding="utf-8")
    (tmp_path / "review_beta.md").write_text(REVIEW.format(seed="b" * 32, verdict="Reject"), encoding="utf-8")
    (tmp_path / "meta_review.md").write_text(META_PT, encoding="utf-8")

    res = _run(tmp_path, monkeypatch)
    assert res["report_language"] == "pt"
    meta = (tmp_path / "meta_review.md").read_text(encoding="utf-8")
    assert "## Major Concerns Matrix" in meta  # parsing heading kept
    assert "| Questão | Nível |" in meta and "| Tamanho amostral | Impeditivo |" in meta
    assert "**Números da auditoria" in meta and "2 testes conferidos; 1 inconsistências" in meta
    assert "Ausente — nenhuma declaração" in meta

    letter = (tmp_path / "author_letter.md").read_text(encoding="utf-8")
    assert letter.startswith("# Carta de decisão aos autores")
    assert "**Recomendação editorial: Revisão maior**" in letter
    assert "## Impeditivo" in letter and "## Essencial" in letter and "Blocking" not in letter
    assert "1 sugestão(ões) opcional(is)" in letter

    md, _ = assemble_consolidated_markdown(tmp_path)
    assert "title: 'PARECER DE REVISÃO POR PARES E RELATÓRIO EDITORIAL'" in md
    assert "# Resumo executivo e recomendação do painel" in md
    assert "**Parecer editorial de consenso**: **REJEIÇÃO**" in md or "**REVISÃO MAIOR**" in md
    assert "# Parte I: Síntese editorial e meta-revisão" in md and "## Síntese do parecer" in md
    assert "## Avaliação confidencial: Revisor Alfa" in md and "### Parecer" in md
    assert "**Aviso de assistência de IA.**" in md
    assert "Executive Summary" not in md and "Confidential Evaluation" not in md
    assert " de 20" in md.split("date: ", 1)[1].splitlines()[0]  # "6 de novembro de 2026"


def test_english_bundle_is_unchanged(tmp_path, monkeypatch):
    from test_compile_results import META, REVIEW

    (tmp_path / "paper_text.txt").write_text(EN * 10, encoding="utf-8")
    (tmp_path / "review_alfa.md").write_text(REVIEW.format(seed="a" * 32, verdict="Major revision"), encoding="utf-8")
    (tmp_path / "review_beta.md").write_text(REVIEW.format(seed="b" * 32, verdict="Reject"), encoding="utf-8")
    (tmp_path / "meta_review.md").write_text(META, encoding="utf-8")
    assert _run(tmp_path, monkeypatch)["report_language"] == "en"
    md, _ = assemble_consolidated_markdown(tmp_path)
    assert "title: 'ACADEMIC PEER REVIEW & EDITORIAL REPORT'" in md and "# Executive Summary & Panel Recommendation" in md
    assert t("en", "ai_notice") in md
    assert compile_results.build_author_letter("## Actionable Revision Roadmap\n1. **Blocking**\n- x\n", "Reject").startswith(
        "# Decision letter to the authors"
    )


def test_matrix_follows_the_language_on_recompile_and_appears_once_in_the_pdf(tmp_path, monkeypatch):
    from test_compile_results import META, REVIEW

    (tmp_path / "review_alfa.md").write_text(REVIEW.format(seed="a" * 32, verdict="Major revision"), encoding="utf-8")
    (tmp_path / "review_beta.md").write_text(REVIEW.format(seed="b" * 32, verdict="Reject"), encoding="utf-8")
    (tmp_path / "meta_review.md").write_text(META, encoding="utf-8")
    (tmp_path / "paper_structure.json").write_text(json.dumps({"report_language": "en"}), encoding="utf-8")
    _run(tmp_path, monkeypatch)
    assert "| Concern | Tier |" in (tmp_path / "meta_review.md").read_text(encoding="utf-8")
    (tmp_path / "paper_structure.json").write_text(json.dumps({"report_language": "es"}), encoding="utf-8")
    _run(tmp_path, monkeypatch)
    meta = (tmp_path / "meta_review.md").read_text(encoding="utf-8")
    assert "| Cuestión | Nivel |" in meta and "| Concern |" not in meta and meta.count("## Major Concerns Matrix") == 1
    md, _ = assemble_consolidated_markdown(tmp_path)
    assert "Matriz de las cuestiones principales" not in md.split("# Parte II")[0]  # rendered once, in Part II
    assert "# Parte II: Matriz consolidada de las cuestiones principales" in md


def test_bold_verdict_with_punctuation_is_translated():
    assert localize_markdown("**Major revision.** Texto.", "pt") == "**Revisão maior.** Texto."
