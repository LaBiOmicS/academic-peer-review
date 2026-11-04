#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "reportlab>=4.0.0",
# ]
# ///
"""Standardized PDF Report Generator for academic-peer-review.

Assembles an authoritative, publication-grade Editorial Peer Review PDF report
combining:
1. Executive Editorial Summary & Consensus Verdict Banner
2. 3-Axis Scientific Classification (Area x Article Type x Research Approach)
3. Editorial Meta-Review & Prioritized Revision Roadmap
4. Consolidated Concerns Matrix (from concerns_table.csv)
5. Automated Pre-Review Diagnostic (statcheck, OpenAlex, FAIR data, AI provenance)
6. Individual Blind Referee Reports (Alfa, Beta, Gamma, Delta, ...)

Engines supported:
- Primary: pandoc + xelatex / lualatex (Unicode-capable), then pdflatex
- Fallback: reportlab (Python native, zero system dependencies)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

GREEK_ORDER = ["alfa", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]


AI_ASSISTANCE_NOTICE = (
    "**AI-assistance disclosure.** This report was drafted with the assistance of AI language models "
    "and automated checks (statistical recalculation, citation lookup, reporting-guideline screening). "
    "It must be verified, edited, and signed off by a human referee or editor, who remains responsible "
    "for its content. Before uploading a confidential manuscript to an AI service, confirm that the "
    "journal's peer-review policy permits it, and disclose AI assistance as that policy requires."
)

# Glyphs that LaTeX default fonts and ReportLab's Helvetica cannot render.
_PDF_SYMBOL_MAP = {
    "✓": "X",
    "✔": "X",
    "✗": "-",
    "·": "-",
    "🔴": "[!]",
    "🟡": "[*]",
    "⚠️": "",
    "⚠": "",
    "💡": "",
    "🔄": "",
    "\ufe0f": "",
}


def _pdf_safe_symbols(text: str) -> str:
    for src, dst in _PDF_SYMBOL_MAP.items():
        text = text.replace(src, dst)
    # Drop any remaining astral-plane characters (emoji), which no default PDF font provides.
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF)


# pdflatex (8-bit fonts) cannot typeset Greek letters and most math symbols from UTF-8 text.
_PDFLATEX_TRANSLITERATION = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "η": "eta",
    "θ": "theta", "κ": "kappa", "λ": "lambda", "μ": "mu", "π": "pi", "ρ": "rho",
    "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi", "ω": "omega", "Δ": "Delta", "Σ": "Sigma",
    "≤": "<=", "≥": ">=", "≠": "!=", "≈": "~", "±": "+/-", "→": "->", "←": "<-", "•": "-",
    "²": "^2", "³": "^3", "√": "sqrt", "∞": "inf", "∑": "sum", "−": "-", "…": "...",
}


def _pdflatex_safe(text: str) -> str:
    for src, dst in _PDFLATEX_TRANSLITERATION.items():
        text = text.replace(src, dst)
    # Keep Latin-1 (accented Portuguese/Spanish) plus common typographic punctuation.
    keep = set("—–‘’“”€")
    return "".join(ch for ch in text if ord(ch) < 0x100 or ch in keep)


def _md_cell(value: str) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _clean_markdown_for_pdf(text: str) -> str:
    """Strip prompt injection delimiters or noisy comment tags from markdown."""
    text = text.replace("<UNTRUSTED_MANUSCRIPT_CONTENT>", "")
    text = text.replace("</UNTRUSTED_MANUSCRIPT_CONTENT>", "")
    # Remove raw JSON block from meta_review if still present
    text = text.split("## CONCERNS_TABLE_DATA")[0]
    # compile_results.py fences the audit figures with HTML comments, which ReportLab would print.
    text = re.sub(r"<!--\s*audit-figures:(?:start|end)\s*-->\n?", "", text)
    # A "---" rule followed directly by text opens a YAML metadata block in pandoc (a review ending
    # in "---\n*This report is…*" broke the PDF with "Unknown alias"); blank lines make it a rule.
    text = re.sub(r"(?m)^[ \t]*-{3,}[ \t]*\n", "\n---\n\n", text)
    return text.strip()


def assemble_consolidated_markdown(output_dir: Path, ai_disclosure: bool = True) -> tuple[str, dict[str, Any]]:
    """Assemble all review artifacts into a single standardized Markdown document.

    With ``ai_disclosure=False`` the AI-assistance notice and the "(AI-assisted draft)" author
    label are left out; the human referee then remains responsible for any disclosure the
    journal's policy requires.
    """
    results_json_path = output_dir / "results.json"
    results: dict[str, Any] = {}
    if results_json_path.exists():
        try:
            results = json.loads(results_json_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass

    pre_audit = results.get("pre_review_audit") or {}
    sa = pre_audit.get("scientific_area") or {}
    area_name = sa.get("area_name", "General Scientific")
    area_code = sa.get("area_code", "multidisciplinary")
    at = sa.get("article_type") or {}
    type_name = at.get("type_name", "Original Research")
    ra = sa.get("research_approach") or {}
    approach_name = ra.get("approach_name", "Standard")
    consensus = results.get("verdict_summary", {}).get("consensus", "Under Review")
    rev_meta = results.get("reviewer_metadata") or {}

    # Header with YAML frontmatter (use single quotes to avoid YAML escape collision on \today)
    doc = [
        "---",
        "title: 'ACADEMIC PEER REVIEW & EDITORIAL REPORT'",
        "subtitle: 'Consolidated Blind Panel Evaluation & Scientific Integrity Audit'",
        f"author: '{'Editorial Review Panel (AI-assisted draft)' if ai_disclosure else 'Editorial Review Panel'}'",
        "date: '\\today'",
        "geometry: 'margin=2.2cm'",
        "header-includes:",
        "  - '\\usepackage{booktabs}'",
        "  - '\\usepackage{pdflscape}'",
        "  - '\\usepackage{fancyhdr}'",
        "  - '\\pagestyle{fancy}'",
        # Clear the default left/right marks (section titles), which overlap the centred header.
        "  - '\\fancyhf{}'",
        "  - '\\fancyhead[CO,CE]{CONFIDENTIAL ACADEMIC PEER REVIEW}'",
        "  - '\\fancyfoot[C]{\\thepage}'",
        "---",
        "",
        "# Executive Summary & Panel Recommendation",
        "",
        f"- **Consensus Editorial Verdict**: **{consensus.upper()}**",
        f"- **Major Scientific Area**: **{area_name}** (`{area_code}`)",
        f"- **Academic Article Type**: **{type_name}** (`{at.get('type_code', 'original')}`)",
        f"- **Research Approach**: **{approach_name}** (`{ra.get('approach_code', 'general')}`)",
    ]

    scope = pre_audit.get("journal_scope_audit")
    if scope:
        score = scope.get("adherence_score_pct")
        score_txt = f"{score}%" if score is not None else "n/a"
        doc.append(
            f"- **Target Journal & Scope Fit**: **{scope.get('target_journal')}** "
            f"({score_txt} — `{scope.get('fit_category')}` | "
            f"Desk-Reject Risk: **{scope.get('desk_reject_risk')}**)"
        )

    doc.extend([
        "",
        "### Reviewer Panel Overview",
        "",
        "| Reviewer | Recommendation | Dominant Analytical Lens | External Citations | Unresolvable IDs |",
        "|---|---|---|---|---|",
    ])

    flagged = (results.get("reviewer_citation_audit") or {}).get("flagged_reviewers") or {}

    for code in GREEK_ORDER:
        if code in rev_meta:
            m = rev_meta[code]
            v = m.get("verdict", "Under Review")
            lens = _md_cell(m.get("lens_or_axis") or "General")
            cits = len(m.get("external_citations", []))
            bad = len(flagged.get(code, []))
            doc.append(f"| **Reviewer {code.capitalize()}** | **{v}** | {lens} | {cits} cited | {bad} |")

    if flagged:
        doc.extend(["", "**Unresolvable identifiers cited by reviewers** (DOIs unknown to OpenAlex and doi.org, or arXiv IDs unknown to arXiv — verify before relying on them):", ""])
        for code in GREEK_ORDER:
            for doi in flagged.get(code, []):
                doc.append(f"- Reviewer {code.capitalize()}: `{_md_cell(doi)}`")

    if ai_disclosure:
        doc.extend(["", AI_ASSISTANCE_NOTICE])
    doc.extend(["", "---", ""])

    # Part 1: Editorial Meta-Review
    meta_path = output_dir / "meta_review.md"
    if meta_path.exists():
        raw_meta = meta_path.read_text(encoding="utf-8", errors="replace")
        # compile_results.py embeds the concerns matrix in the meta-review; Part II renders it once.
        raw_meta = re.sub(r"#+\s*Major Concerns Matrix\s*\n+(?:\|[^\n]*(?:\n|$))+", "", raw_meta)
        cleaned_meta = _clean_markdown_for_pdf(raw_meta)
        doc.extend([
            "# Part I: Editorial Synthesis & Meta-Review",
            "",
            cleaned_meta,
            "",
            "---",
            "",
        ])

    # Part 2: Concerns Matrix Table
    csv_path = output_dir / "concerns_table.csv"
    if csv_path.exists():
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if rows:
                doc.extend([
                    "# Part II: Consolidated Major Concerns Matrix",
                    "",
                    "The table below cross-tabulates the Blocking and Essential concerns across referees "
                    "(X = raised as a major concern; (m) = mentioned only in passing). "
                    + (
                        "Referees ran on different models, so agreement across models carries some weight:"
                        if (results.get("severity_contract") or {}).get("single_model_panel") is False
                        else "All referees share one underlying model, so agreement is attribution, not "
                        "independent corroboration:"
                    ),
                    "",
                ])
                header = rows[0]
                # Older bundles have no severity column: every column after the concern is a reviewer.
                first_reviewer_col = 2 if len(header) > 1 and header[1] == "severity" else 1
                doc.append("| " + " | ".join(_md_cell(h.capitalize() if h == "severity" else h) for h in header) + " |")
                doc.append("| " + " | ".join(["---"] * len(header)) + " |")
                for r in rows[1:]:
                    if not r:
                        continue
                    cells = [_md_cell(r[0].removeprefix("'"))]
                    if first_reviewer_col == 2:
                        cells.append(_md_cell((r[1] if len(r) > 1 else "").capitalize() or "-"))
                    for c in r[first_reviewer_col:]:
                        v = c.strip().lower()
                        cells.append("✓" if v in ("true", "major") else "(m)" if v == "minor" else "·")
                    doc.append("| " + " | ".join(cells) + " |")
                doc.extend(["", "---", ""])
        except Exception:
            pass

    # Part 3: Automated Pre-Review Diagnostic
    audit_md_path = output_dir / "pre_review_audit.md"
    if audit_md_path.exists():
        audit_md = audit_md_path.read_text(encoding="utf-8", errors="replace")
        doc.extend([
            "# Part III: Deterministic Pre-Review Integrity Audit",
            "",
            audit_md.strip(),
            "",
            "---",
            "",
        ])

    # Part 4: Individual Blind Referee Reports
    doc.extend(["# Part IV: Individual Independent Referee Reports", ""])
    # Only the panel compiled into results.json (stale review files from older runs are skipped).
    panel = [c for c in GREEK_ORDER if c in rev_meta] if rev_meta else GREEK_ORDER
    for code in panel:
        rf = output_dir / f"review_{code}.md"
        if rf.exists():
            r_text = rf.read_text(encoding="utf-8", errors="replace")
            cleaned_r = _clean_markdown_for_pdf(r_text)
            doc.extend([
                f"## Confidential Evaluation: Reviewer {code.capitalize()}",
                "",
                cleaned_r,
                "",
                "---",
                "",
            ])

    full_md = _pdf_safe_symbols("\n".join(doc))
    return full_md, results


# A table with several prose columns (e.g. the blocking-concern verification table) or very many
# columns is unreadable on a portrait page: it gets a landscape page of its own.
WIDE_TABLE_MIN_TEXT_COLUMNS = 3
WIDE_TABLE_TEXT_COLUMN_CHARS = 30
WIDE_TABLE_MIN_COLUMNS = 8

_TABLE_SEPARATOR = re.compile(r"\|?(\s*:?-{3,}:?\s*\|)+\s*:?-*:?\s*")


def _table_cells(line: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _is_wide_table(rows: list[list[str]]) -> bool:
    if not rows:
        return False
    ncols = max(len(r) for r in rows)
    text_columns = sum(
        1 for i in range(ncols) if max(len(r[i]) if i < len(r) else 0 for r in rows) > WIDE_TABLE_TEXT_COLUMN_CHARS
    )
    return ncols >= WIDE_TABLE_MIN_COLUMNS or text_columns >= WIDE_TABLE_MIN_TEXT_COLUMNS


def _column_weights(rows: list[list[str]]) -> list[int]:
    """Relative column widths from the longest cell, with a floor so short columns stay legible."""
    ncols = max(len(r) for r in rows)
    return [max(10, min(80, 2 + max(len(r[i]) if i < len(r) else 0 for r in rows))) for i in range(ncols)]


def _markdown_blocks(markdown_content: str) -> list[tuple[str, list[str]]]:
    """Split Markdown into ("table", lines) blocks of consecutive pipe-table lines and ("text", lines)."""
    blocks: list[tuple[str, list[str]]] = []
    for line in markdown_content.splitlines():
        kind = "table" if line.lstrip().startswith("|") else "text"
        if blocks and blocks[-1][0] == kind:
            blocks[-1][1].append(line)
        else:
            blocks.append((kind, [line]))
    return blocks


def _layout_tables_for_latex(markdown_content: str) -> str:
    """Size pipe-table columns by content and put wide tables on landscape pages (pandoc raw blocks).

    pandoc takes relative column widths from the dashes of the separator row, so equal "---" cells
    gave a prose column the same width as a column of ticks.
    """
    out: list[str] = []
    for kind, lines in _markdown_blocks(markdown_content):
        rows = [_table_cells(ln) for ln in lines if not _TABLE_SEPARATOR.fullmatch(ln.strip())]
        if kind != "table" or not rows:
            out.extend(lines)
            continue
        separator = "|" + "|".join("-" * w for w in _column_weights(rows)) + "|"
        lines = [separator if _TABLE_SEPARATOR.fullmatch(ln.strip()) else ln for ln in lines]
        if _is_wide_table(rows):
            out.extend(["", "```{=latex}", "\\begin{landscape}\\footnotesize", "```", "", *lines, "",
                        "```{=latex}", "\\normalsize\\end{landscape}", "```", ""])
        else:
            out.extend(lines)
    return "\n".join(out)


def render_with_pandoc(markdown_content: str, output_pdf_path: Path) -> bool:
    """Render PDF using pandoc and pdflatex."""
    markdown_content = _layout_tables_for_latex(markdown_content)
    pandoc_bin = shutil.which("pandoc")
    if not pandoc_bin:
        return False

    engines = [e for e in ("xelatex", "lualatex", "pdflatex") if shutil.which(e)]
    if not engines:
        return False

    temp_md = output_pdf_path.with_suffix(".temp.md")
    # A broken TeX setup (e.g. a stale luaotfload font cache) makes one engine fail while the next
    # works; errors are reported only if every engine fails, and a fallback is named in one line.
    failures: list[str] = []
    try:
        for engine in engines:
            content = _pdflatex_safe(markdown_content) if engine == "pdflatex" else markdown_content
            temp_md.write_text(content, encoding="utf-8")
            cmd = [
                pandoc_bin,
                "--sandbox",
                str(temp_md),
                "-o",
                str(output_pdf_path),
                f"--pdf-engine={engine}",
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            except (subprocess.TimeoutExpired, OSError):
                continue
            if res.returncode == 0 and output_pdf_path.exists() and output_pdf_path.stat().st_size > 1000:
                if failures:
                    skipped = ", ".join(f.split(":", 1)[0] for f in failures)
                    print(f"Notice: PDF rendered with {engine} ({skipped} failed on this TeX installation).", file=sys.stderr)
                return True
            failures.append(f"{engine}: {res.stderr.strip()[-300:]}")
    finally:
        temp_md.unlink(missing_ok=True)
    for failure in failures:
        print(f"Notice: pandoc/{failure}", file=sys.stderr)
    return False


def _strip_front_matter(markdown_content: str) -> str:
    """Remove a leading YAML front-matter block (it is LaTeX metadata, not report content)."""
    m = re.match(r"\A---\s*\n.*?\n---\s*\n", markdown_content, re.DOTALL)
    return markdown_content[m.end():] if m else markdown_content


def _inline_markup(text: str) -> str:
    """Escape text for ReportLab's mini-HTML and translate **bold**, *italic* and `code`."""
    out = xml_escape(text)
    # The closing "**" may not be followed by "*", so "**Fit with *Journal***" nests <i> inside <b>.
    out = re.sub(r"\*\*(.+?)\*\*(?!\*)", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", out)
    out = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', out)
    return out


def render_with_reportlab(markdown_content: str, output_pdf_path: Path, results: dict[str, Any]) -> bool:
    """Render PDF using reportlab as an autonomous fallback."""
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            HRFlowable,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        return False

    margin = 54
    portrait_size, landscape_size = letter, landscape(letter)
    doc = BaseDocTemplate(str(output_pdf_path), pagesize=portrait_size)
    # Wide tables move to a landscape page; everything else stays portrait.
    doc.addPageTemplates([
        PageTemplate(id=name, pagesize=size, frames=[Frame(margin, margin, size[0] - 2 * margin, size[1] - 2 * margin, id=name)])
        for name, size in (("portrait", portrait_size), ("landscape", landscape_size))
    ])
    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = HexColor("#1A365D")
    dark_text = HexColor("#2D3748")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=HexColor("#4A5568"),
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=dark_text,
    )

    story = [
        Paragraph("ACADEMIC PEER REVIEW & EDITORIAL REPORT", title_style),
        Paragraph("Confidential Blind Panel Evaluation & Scientific Integrity Audit", subtitle_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14),
    ]

    def para(markup: str, style: ParagraphStyle) -> Paragraph:
        # One malformed line must not abort the whole report: fall back to its plain text.
        try:
            return Paragraph(markup, style)
        except ValueError:
            return Paragraph(xml_escape(re.sub(r"<[^>]+>", "", markup)), style)

    def table(rows: list[list[str]], wide: bool) -> Table:
        size = landscape_size if wide else portrait_size
        width = size[0] - 2 * margin
        cell_style = ParagraphStyle("Cell", parent=body_style, fontSize=7.5 if wide else 8.5, leading=10 if wide else 11)
        ncols = max(len(r) for r in rows)
        rows = [r + [""] * (ncols - len(r)) for r in rows]
        weights = _column_weights(rows)
        col_widths = [width * w / sum(weights) for w in weights]
        data = [[para(f"<b>{_inline_markup(c)}</b>" if i == 0 else _inline_markup(c), cell_style) for c in r]
                for i, r in enumerate(rows)]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#EDF2F7")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, primary_color),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, HexColor("#CBD5E0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    for kind, lines in _markdown_blocks(_strip_front_matter(markdown_content)):
        if kind == "table":
            rows = [_table_cells(ln) for ln in lines if not _TABLE_SEPARATOR.fullmatch(ln.strip())]
            if not rows:
                continue
            if _is_wide_table(rows):
                story.extend([NextPageTemplate("landscape"), PageBreak(), table(rows, True),
                              NextPageTemplate("portrait"), PageBreak()])
            else:
                story.extend([table(rows, False), Spacer(1, 6)])
            continue
        for line_s in lines:
            line_s = line_s.strip()
            if not line_s or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", line_s):
                continue
            heading = re.match(r"(#{1,6})\s+(.*)", line_s)
            if heading:
                level, title = len(heading.group(1)), _inline_markup(heading.group(2))
                if level == 1:
                    story.extend([Spacer(1, 8), para(title, h1_style)])
                elif level == 2:
                    story.extend([Spacer(1, 6), para(title, h2_style)])
                else:
                    story.extend([Spacer(1, 4), para(f"<b>{title}</b>", body_style)])
            elif line_s.startswith(("- ", "* ", "+ ")):
                story.append(para(f"• {_inline_markup(line_s[2:].strip())}", body_style))
            else:
                story.extend([para(_inline_markup(line_s), body_style), Spacer(1, 3)])

    doc.build(story)
    return output_pdf_path.exists() and output_pdf_path.stat().st_size > 1000


def generate_pdf_report(
    output_dir: str | Path, output_pdf: str | Path | None = None, ai_disclosure: bool = True
) -> Path:
    """Generate standardized PDF peer review report from review artifacts."""
    out_dir = Path(output_dir).resolve()
    pdf_path = Path(output_pdf).resolve() if output_pdf else out_dir / "editorial_peer_review_report.pdf"

    markdown_content, results = assemble_consolidated_markdown(out_dir, ai_disclosure=ai_disclosure)
    consolidated_md_path = out_dir / "consolidated_editorial_report.md"
    consolidated_md_path.write_text(markdown_content, encoding="utf-8")

    # 1. Try Pandoc + LaTeX
    success = render_with_pandoc(markdown_content, pdf_path)

    # 2. Try ReportLab fallback
    if not success:
        success = render_with_reportlab(markdown_content, pdf_path, results)

    if success:
        print(f"✔ Standardized PDF review report generated: {pdf_path}")
    else:
        print(f"Notice: Pandoc/ReportLab PDF rendering skipped. Consolidated report available at {consolidated_md_path}")

    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate standardized PDF academic peer review report.")
    parser.add_argument("--output-dir", required=True, help="Directory containing review artifacts.")
    parser.add_argument("--output-pdf", help="Optional output PDF path (defaults to editorial_peer_review_report.pdf).")
    parser.add_argument(
        "--no-ai-disclosure",
        action="store_true",
        help="Omit the AI-assistance disclosure from the report (the referee handles disclosure).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    if not out_dir.exists():
        print(f"Error: Output directory not found: {out_dir}", file=sys.stderr)
        return 1

    generate_pdf_report(out_dir, args.output_pdf, ai_disclosure=not args.no_ai_disclosure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
