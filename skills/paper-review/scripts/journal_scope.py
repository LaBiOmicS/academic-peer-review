#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Target Journal Scope & Desk-Reject Risk Auditor for academic-peer-review.

Performs aims & scope alignment analysis, desk-reject risk evaluation,
author guidelines compliance checks, and cascading journal recommendations.
Works both with a curated knowledge base of major academic journals and
dynamically via the OpenAlex Sources API.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "academic-peer-review/1.0.0 (LaBiOmicS - UMC; mailto:fabianomenegidio@umc.br; https://github.com/LaBiOmicS/academic-peer-review)"

MAX_JOURNAL_NAME_LEN = 120
_JOURNAL_NAME_ALLOWED = re.compile(r"[^\w\s&:,.()'/+-]")

REFERENCES_HEADING_REGEX = re.compile(
    r"(?im)^\s*(?:#+\s*|\d+\.?\s*)?(?:references|bibliography|literature\s+cited|works\s+cited|"
    r"referências(?:\s+bibliográficas)?|referencias(?:\s+bibliográficas)?|bibliografía|bibliografia)\s*:?\s*$"
)
PAGE_MARKER_REGEX = re.compile(r"^--- \[Page \d+\] ---$", re.MULTILINE)


def clean_journal_name(name: str | None) -> str:
    """Normalize a user- or manuscript-supplied journal name into a short, inert string.

    The name may come from untrusted manuscript text, so only typical journal-title
    characters are kept and the length is capped before it reaches prompts or URLs.
    """
    if not name:
        return ""
    cleaned = _JOURNAL_NAME_ALLOWED.sub(" ", unicodedata.normalize("NFC", name))
    cleaned = " ".join(cleaned.split())
    return cleaned[:MAX_JOURNAL_NAME_LEN].strip(" .,:;-")


def _normalize_key(name: str) -> str:
    """Accent-, case- and punctuation-insensitive key used for curated lookups."""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    key = re.sub(r"[^\w\s]", " ", ascii_only.lower().replace("&", " and "))
    key = " ".join(key.split())
    key = key.removeprefix("the ")
    return key


def estimate_body_word_count(text: str) -> int:
    """Count words in the main text, excluding the reference list and page markers."""
    body = PAGE_MARKER_REGEX.sub("", text)
    headings = list(REFERENCES_HEADING_REGEX.finditer(body))
    if headings:
        last = headings[-1]
        # Ignore a heading in the first fifth of the text (e.g. a table-of-contents entry).
        if last.start() > len(body) * 0.2:
            body = body[: last.start()]
    return len(re.findall(r"\b\w+\b", body))

# ==============================================================================
# CURATED KNOWLEDGE BASE OF NOTABLE JOURNALS ACROSS ALL 5 SCIENTIFIC AREAS
# ==============================================================================

CURATED_JOURNALS: dict[str, dict[str, Any]] = {
    "bioinformatics": {
        "display_name": "Bioinformatics",
        "publisher": "Oxford University Press",
        "issn": "1367-4803",
        "area": "biologicas",
        "domain": "Bioinformatics, Computational Biology, Genomics",
        "scope_summary": "Publishes highest quality research on novel computational methods, algorithms, databases, and software tools in molecular biology and genomics.",
        "desk_reject_pitfalls": [
            "Pure routine application of existing software/pipelines without developing new computational methodologies or algorithmic advances.",
            "Lack of accessible, open-source code repository (GitHub/GitLab) with clear install instructions or containers.",
            "Missing benchmark comparison against existing state-of-the-art tools on gold-standard datasets.",
            "Submitting application notes without functional standalone tool, web server, or package.",
        ],
        "mandatory_requirements": ["Open Source Code Repository", "Data Availability Statement", "Benchmark vs SOTA"],
        "max_words_original": 7000,
        "max_words_app_note": 1500,
        "alternative_journals": [
            {"name": "BMC Bioinformatics", "focus": "More permissive of standard methodological applications and software implementations."},
            {"name": "PLOS Computational Biology", "focus": "Prioritizes significant biological insights derived through computational methods."},
            {"name": "Database: The Journal of Biological Databases and Curation", "focus": "Ideal for biological database resources and curations."},
        ],
    },
    "briefings in bioinformatics": {
        "display_name": "Briefings in Bioinformatics",
        "publisher": "Oxford University Press",
        "issn": "1467-5463",
        "area": "biologicas",
        "domain": "Bioinformatics, Reviews, Methodological Benchmarks",
        "scope_summary": "Publishes reviews, comprehensive evaluations, and benchmarks of bioinformatics tools and databases.",
        "desk_reject_pitfalls": [
            "Submitting primary experimental research or single-tool applications instead of a comprehensive benchmark, review, or protocol evaluation.",
            "Superficial review without extensive systematic comparison, taxonomy, or forward-looking perspective.",
        ],
        "mandatory_requirements": ["Benchmark or Review Focus", "Comparative Table of Tools", "Data Availability Statement"],
        "alternative_journals": [
            {"name": "Bioinformatics", "focus": "For original tool or algorithmic development."},
            {"name": "WIREs Computational Molecular Science", "focus": "For specialized computational biology overviews."},
        ],
    },
    "nucleic acids research": {
        "display_name": "Nucleic Acids Research",
        "publisher": "Oxford University Press",
        "issn": "0305-1048",
        "area": "biologicas",
        "domain": "Molecular Biology, Nucleic Acids, Genomics, Structural Biology",
        "scope_summary": "Publishes top-tier research on the physical, chemical, biochemical and biological aspects of nucleic acids and proteins interacting with them.",
        "desk_reject_pitfalls": [
            "Studies lacking direct mechanism, molecular insight, or functional connection to nucleic acid biology.",
            "Web servers / Database submissions that fail to meet strict annual NAR issue guidelines (e.g. missing long-term maintenance commitment).",
            "Incremental bioinformatic analyses lacking experimental functional validation.",
        ],
        "mandatory_requirements": ["Direct Nucleic Acid Focus", "Functional/Experimental Validation", "Mandatory Deposition (PDB/SRA/GEO)"],
        "alternative_journals": [
            {"name": "RNA", "focus": "Specialized in RNA structure, function, and processing."},
            {"name": "Molecular Biology Reports", "focus": "For broader molecular studies with less stringent breakthrough thresholds."},
        ],
    },
    "nature": {
        "display_name": "Nature",
        "publisher": "Springer Nature",
        "issn": "0028-0836",
        "area": "multidisciplinary",
        "domain": "Multidisciplinary Science",
        "scope_summary": "Publishes weekly outstanding scientific breakthroughs of broad general interest and definitive novelty across all disciplines.",
        "desk_reject_pitfalls": [
            "Incremental progress or narrow interest confined to a single sub-discipline without broad scientific paradigm shift.",
            "Lack of decisive mechanistic insight, overwhelming orthogonal validation, or generalizability.",
            "Format non-compliance (word count far exceeding article or letter formats).",
        ],
        "mandatory_requirements": ["Transformative Scientific Impact", "Broad Cross-Disciplinary Appeal", "Strict Format Limits", "FAIR Data & Code"],
        "max_words_original": 3500,
        "alternative_journals": [
            {"name": "Nature Communications", "focus": "For specialized, highly rigorous advances within a specific field without needing cross-discipline appeal."},
            {"name": "Scientific Reports", "focus": "Sound science without subjective importance thresholds."},
        ],
    },
    "science": {
        "display_name": "Science",
        "publisher": "American Association for the Advancement of Science (AAAS)",
        "issn": "0036-8075",
        "area": "multidisciplinary",
        "domain": "Multidisciplinary Science",
        "scope_summary": "Publishes cutting-edge research, scientific news, and commentary with broad interdisciplinary significance.",
        "desk_reject_pitfalls": [
            "Specialized technical work lacking broad appeal to the wider scientific community.",
            "Lack of definitive conclusive evidence or missing crucial controls.",
        ],
        "mandatory_requirements": ["Transformative Discovery", "Cross-Disciplinary Appeal", "Strict Data/Code Deposition"],
        "max_words_original": 4000,
        "alternative_journals": [
            {"name": "Science Advances", "focus": "High-impact open access outlet for robust advances in specific domains."},
            {"name": "PLOS ONE", "focus": "For technically valid studies without general interest filter."},
        ],
    },
    "nature communications": {
        "display_name": "Nature Communications",
        "publisher": "Springer Nature",
        "issn": "2041-1723",
        "area": "multidisciplinary",
        "domain": "Multidisciplinary Natural & Technical Sciences",
        "scope_summary": "Publishes high-quality research that represents important advances of significance to specialists within each field.",
        "desk_reject_pitfalls": [
            "Marginal or incremental advances relative to existing publications.",
            "Incomplete mechanistic explanation or lack of statistical/reproducibility rigor.",
            "Missing raw data or code availability statements.",
        ],
        "mandatory_requirements": ["Significant Field Advance", "Exhaustive Validation", "Open Data/Code Availability Statement"],
        "max_words_original": 5000,
        "alternative_journals": [
            {"name": "Communications Biology", "focus": "For biology-specific advances."},
            {"name": "Scientific Reports", "focus": "For valid studies with modest conceptual novelty."},
        ],
    },
    "plos computational biology": {
        "display_name": "PLOS Computational Biology",
        "publisher": "Public Library of Science (PLOS)",
        "issn": "1553-7358",
        "area": "biologicas",
        "domain": "Computational Biology, Systems Biology",
        "scope_summary": "Publishes works of exceptional importance that further our understanding of living systems through the application of computational methods.",
        "desk_reject_pitfalls": [
            "Pure method or algorithm paper that provides no new biological insight or biological discovery.",
            "Application of standard bioinformatic tools to new data without substantial computational innovation or deep biological interpretation.",
            "Failure to make software, code, and models open and freely accessible.",
        ],
        "mandatory_requirements": ["Clear Biological Insight", "Computational Rigor", "Open Source Code (OSI-approved)"],
        "alternative_journals": [
            {"name": "Bioinformatics", "focus": "Focuses heavily on algorithmic and software innovations even when biological discovery is secondary."},
            {"name": "PLOS ONE", "focus": "Accepts computational biology papers without requiring exceptional novel biological insight."},
        ],
    },
    "plos one": {
        "display_name": "PLOS ONE",
        "publisher": "Public Library of Science (PLOS)",
        "issn": "1932-6203",
        "area": "multidisciplinary",
        "domain": "Multidisciplinary Science & Engineering",
        "scope_summary": "Publishes primary research from any scientific discipline evaluated exclusively on methodological and ethical rigor, rather than perceived impact.",
        "desk_reject_pitfalls": [
            "Refusal to share data publicly or using evasive 'data available upon request' without ethical/legal justification.",
            "Fatal methodological flaws, improper controls, or inadequate sample sizes.",
            "Missing ethical approval (IRB/IACUC/CEP) for human or animal subjects.",
        ],
        "mandatory_requirements": ["Methodological Rigor", "Public Data Sharing (FAIR)", "Full Ethics Statement"],
        "alternative_journals": [
            {"name": "Scientific Reports", "focus": "Equivalent sound-science scope under Springer Nature."},
            {"name": "PeerJ", "focus": "Similar sound-science model in biological and medical sciences."},
        ],
    },
    "the lancet": {
        "display_name": "The Lancet",
        "publisher": "Elsevier",
        "issn": "0140-6736",
        "area": "saude",
        "domain": "Clinical Medicine, Global Health",
        "scope_summary": "Publishes clinical trials, global health assessments, and landmark clinical research that alter clinical practice or medical policy.",
        "desk_reject_pitfalls": [
            "Preclinical, animal, or in vitro studies (The Lancet publishes human clinical and population research).",
            "Single-center observational studies with small sample sizes or convenience samples.",
            "Unregistered clinical trials or trials failing CONSORT / EQUATOR guidelines.",
            "Studies lacking measurable impact on clinical practice or health policy.",
        ],
        "mandatory_requirements": ["Prospective Trial Registration", "CONSORT/EQUATOR", "Clinical Practice Impact", "Human Ethics Approval"],
        "alternative_journals": [
            {"name": "The Lancet Infectious Diseases / Regional Health", "focus": "For specialized disease or regional health investigations."},
            {"name": "BMC Medicine", "focus": "Broad medical interest with slightly more flexible scope."},
        ],
    },
    "jama": {
        "display_name": "JAMA: The Journal of the American Medical Association",
        "publisher": "American Medical Association",
        "issn": "0098-7484",
        "area": "saude",
        "domain": "Clinical Medicine, Public Health, Health Policy",
        "scope_summary": "Publishes original clinical trials, large epidemiologic cohorts, and meta-analyses advancing clinical practice.",
        "desk_reject_pitfalls": [
            "Basic or animal science studies without direct human clinical application.",
            "Lack of prospective registration in ClinicalTrials.gov or equivalent ICMJE registry.",
            "Unadjusted observational comparisons prone to confounding by indication.",
        ],
        "mandatory_requirements": ["ICMJE Prospective Registration", "Structured Abstract", "Statistical Analysis Plan", "Conflict of Interest"],
        "alternative_journals": [
            {"name": "JAMA Network Open", "focus": "Broad open access medical journal for high quality clinical studies."},
            {"name": "Annals of Internal Medicine", "focus": "Internal medicine focus with high clinical impact."},
        ],
    },
    "ieee transactions on pattern analysis and machine intelligence": {
        "display_name": "IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)",
        "publisher": "IEEE Computer Society",
        "issn": "0162-8828",
        "area": "exatas",
        "domain": "Computer Vision, Pattern Recognition, Machine Learning, AI",
        "scope_summary": "Publishes top-tier theoretical and experimental contributions to computer vision, pattern analysis, and machine learning.",
        "desk_reject_pitfalls": [
            "Superficial empirical applications of standard ML models (e.g. training a standard CNN on a private dataset) without theoretical or algorithmic novelty.",
            "Inadequate evaluation: missing comparison against current state-of-the-art methods or lacking standard benchmark datasets.",
            "Missing ablation studies or failure to explain theoretical grounding.",
        ],
        "mandatory_requirements": ["Algorithmic/Theoretical Novelty", "State-of-the-Art Benchmarks", "Ablation Studies", "Reproducible Code"],
        "alternative_journals": [
            {"name": "Pattern Recognition (Elsevier)", "focus": "Broad pattern recognition applications and methods."},
            {"name": "IEEE Transactions on Image Processing (TIP)", "focus": "Specialized in image processing techniques."},
            {"name": "Machine Learning (Springer)", "focus": "Core ML algorithms and theory."},
        ],
    },
    "acm computing surveys": {
        "display_name": "ACM Computing Surveys",
        "publisher": "Association for Computing Machinery (ACM)",
        "issn": "0360-0300",
        "area": "exatas",
        "domain": "Computer Science, Surveys, Taxonomies",
        "scope_summary": "Publishes comprehensive, readable tutorials and surveys that guide researchers through a computing subfield.",
        "desk_reject_pitfalls": [
            "Submitting primary research or a single algorithmic contribution instead of a comprehensive survey or taxonomy.",
            "Ad-hoc literature summary lacking systematic search methodology, formal taxonomy, or comparative analysis.",
        ],
        "mandatory_requirements": ["Comprehensive Taxonomy", "Systematic Literature Coverage", "Future Research Challenges"],
        "alternative_journals": [
            {"name": "IEEE Access", "focus": "Accepts both surveys and primary research across computing and electrical engineering."},
            {"name": "Computer Science Review", "focus": "Elsevier counterpart for in-depth computing reviews."},
        ],
    },
    "memorias do instituto oswaldo cruz": {
        "display_name": "Memórias do Instituto Oswaldo Cruz",
        "publisher": "Fundação Oswaldo Cruz (Fiocruz) / SciELO",
        "issn": "0074-0276",
        "area": "saude",
        "domain": "Tropical Medicine, Parasitology, Infectious Diseases, Microbiology",
        "scope_summary": "Diamond Open Access journal publishing research on infectious and parasitic diseases, vectors, microbiology, and tropical medicine.",
        "desk_reject_pitfalls": [
            "Studies disconnected from infectious diseases, medical parasitology, or public health relevance in tropical/endemic settings.",
            "Studies without proper taxonomic identification or lacking voucher/accession references.",
            "Missing local ethics approval (CEP/CONEP/CEUA or equivalent) for endemic human/animal samples.",
        ],
        "mandatory_requirements": ["Infectious/Parasitic Focus", "Open Access Compliance", "Ethics/Sample Permits (SisGen/CEUA/CEP)"],
        "alternative_journals": [
            {"name": "Revista da Sociedade Brasileira de Medicina Tropical", "focus": "Clinical and epidemiological tropical medicine in Brazil/Latin America."},
            {"name": "Acta Tropica", "focus": "International tropical biomedical research."},
        ],
    },
    "revista de saude publica": {
        "display_name": "Revista de Saúde Pública",
        "publisher": "Faculdade de Saúde Pública da USP / SciELO",
        "issn": "0034-8910",
        "area": "saude",
        "domain": "Public Health, Epidemiology, Health Services",
        "scope_summary": "Publishes original scientific articles in public health, epidemiology, healthcare policies, and health surveillance.",
        "desk_reject_pitfalls": [
            "Clinical or bench experimental studies lacking public health relevance or population-level framing.",
            "Local descriptive data without epidemiological analysis or analytical comparison.",
            "Failure to use STROBE or applicable EQUATOR guideline.",
        ],
        "mandatory_requirements": ["Public Health Relevance", "Epidemiological Rigor", "STROBE Guidelines"],
        "alternative_journals": [
            {"name": "Cadernos de Saúde Pública", "focus": "Fiocruz public health journal with strong qualitative, socio-cultural, and epidemiological scope."},
            {"name": "Ciência & Saúde Coletiva", "focus": "Broad public health, health policy, and social science in health."},
        ],
    },
}

# Exact-match aliases (normalized with `_normalize_key`). Substring matching is deliberately
# avoided: "Briefings in Bioinformatics" must never resolve to "Bioinformatics".
JOURNAL_ALIASES: dict[str, list[str]] = {
    "bioinformatics": ["bioinformatics oxford", "oxford bioinformatics"],
    "briefings in bioinformatics": ["brief bioinform"],
    "nucleic acids research": ["nar", "nucleic acids res"],
    "nature": ["nature london"],
    "nature communications": ["nat commun", "nature comms"],
    "plos computational biology": ["plos comput biol", "plos comp bio", "plos comp biol", "ploscb"],
    "plos one": ["plosone"],
    "the lancet": ["lancet", "lancet london"],
    "jama": [
        "journal of the american medical association",
        "jama the journal of the american medical association",
    ],
    "ieee transactions on pattern analysis and machine intelligence": [
        "tpami",
        "ieee tpami",
        "ieee trans pattern anal mach intell",
    ],
    "acm computing surveys": ["acm comput surv", "csur"],
    "memorias do instituto oswaldo cruz": ["mem inst oswaldo cruz"],
    "revista de saude publica": ["rev saude publica"],
}


def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for key, data in CURATED_JOURNALS.items():
        lookup[_normalize_key(key)] = key
        lookup[_normalize_key(data["display_name"])] = key
        if data.get("issn"):
            lookup[data["issn"]] = key
        for alias in JOURNAL_ALIASES.get(key, []):
            lookup[_normalize_key(alias)] = key
    return lookup


_CURATED_LOOKUP = _build_lookup()


def find_curated_journal(journal_name: str) -> str | None:
    """Return the curated key for an exact name, alias, or ISSN match (never a substring match)."""
    issn = re.search(r"\b\d{4}-\d{3}[\dXx]\b", journal_name)
    if issn and issn.group(0).upper() in _CURATED_LOOKUP:
        return _CURATED_LOOKUP[issn.group(0).upper()]
    norm = _normalize_key(journal_name)
    if not norm:
        return None
    return _CURATED_LOOKUP.get(norm)


# ==============================================================================
# OPENALEX API QUERY FOR DYNAMIC JOURNAL METADATA
# ==============================================================================

def query_openalex_journal(journal_name: str, timeout: float = 8.0) -> dict[str, Any] | None:
    """Fetch live metadata, concepts, and topics for a target journal from OpenAlex Sources API."""
    clean_name = re.sub(r"[^\w\s-]", " ", journal_name).strip()
    if not clean_name:
        return None

    params = urllib.parse.urlencode({
        "search": clean_name,
        "per-page": 5,
        "select": "id,display_name,issn_l,issn,host_organization_name,homepage_url,is_oa,"
                  "is_in_doaj,apc_usd,works_count,cited_by_count,topics",
    })
    url = f"https://api.openalex.org/sources?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read(1_048_576).decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    results = data.get("results") or []
    if not results:
        return None

    # Prefer an exact (normalized) title match over OpenAlex's relevance ranking.
    wanted = _normalize_key(journal_name)
    best = next((r for r in results if _normalize_key(r.get("display_name") or "") == wanted), results[0])

    topics_data = []
    for t in (best.get("topics") or [])[:10]:
        topics_data.append({
            "name": t.get("display_name", ""),
            "subfield": t.get("subfield", {}).get("display_name", "") if isinstance(t.get("subfield"), dict) else "",
            "field": t.get("field", {}).get("display_name", "") if isinstance(t.get("field"), dict) else "",
            "domain": t.get("domain", {}).get("display_name", "") if isinstance(t.get("domain"), dict) else "",
        })

    return {
        "id": best.get("id"),
        "display_name": best.get("display_name"),
        "issn": best.get("issn_l") or (best.get("issn") or [None])[0],
        "publisher": best.get("host_organization_name") or "Unknown Publisher",
        "homepage_url": best.get("homepage_url"),
        "is_oa": bool(best.get("is_oa", False)),
        "is_in_doaj": bool(best.get("is_in_doaj", False)),
        "apc_usd": best.get("apc_usd"),
        "works_count": best.get("works_count", 0),
        "cited_by_count": best.get("cited_by_count", 0),
        "topics": topics_data,
        "exact_title_match": _normalize_key(best.get("display_name") or "") == wanted,
        "source": "OpenAlex Sources API",
    }


def resolve_journal(journal_name: str, *, online: bool = True) -> dict[str, Any]:
    """Resolve target journal from curated database or fall back to OpenAlex API.

    With ``online=False`` no network request is made (curated data or generic fallback only).
    """
    journal_name = clean_journal_name(journal_name)

    # 1. Exact name / alias / ISSN match in curated knowledge base
    curated_key = find_curated_journal(journal_name) if journal_name else None
    if curated_key:
        merged = dict(CURATED_JOURNALS[curated_key])
        merged["curated_key"] = curated_key
        merged["source"] = "Curated Knowledge Base"
        if online:
            api_data = query_openalex_journal(merged["display_name"], timeout=5.0)
            if api_data and api_data.get("exact_title_match"):
                merged["openalex_topics"] = api_data.get("topics", [])
                merged["homepage_url"] = api_data.get("homepage_url")
                merged["apc_usd"] = api_data.get("apc_usd")
                merged["is_oa"] = api_data.get("is_oa", False)
                merged["is_in_doaj"] = api_data.get("is_in_doaj", False)
        return merged

    # 2. Query OpenAlex API live
    api_res = query_openalex_journal(journal_name) if (online and journal_name) else None
    if api_res:
        api_res["scope_summary"] = f"Academic journal indexed in OpenAlex with {api_res.get('works_count', 0):,} published works."
        if not api_res.get("exact_title_match"):
            api_res["scope_summary"] += (
                f" Note: OpenAlex returned the closest match for '{journal_name}'; confirm this is the intended journal."
            )
        api_res["desk_reject_pitfalls"] = [
            "Lack of fit with primary indexed journal topics and audience expectations.",
            "Failure to meet standard reporting and reproducibility guidelines for this discipline.",
        ]
        api_res["mandatory_requirements"] = ["Data Availability Statement", "Ethics & Conflict of Interest Declaration"]
        return api_res

    # 3. Fallback generic placeholder
    return {
        "display_name": journal_name or "Unspecified journal",
        "publisher": "Unknown / Unresolved",
        "issn": None,
        "scope_summary": f"Target journal '{journal_name}' specified by user (not found in curated base or OpenAlex).",
        "desk_reject_pitfalls": [
            "Out-of-scope submission relative to journal's editorial statement and reader profile.",
            "Inadequate methodology or failure to state data availability.",
        ],
        "mandatory_requirements": ["Data Availability Statement", "Ethics Statement"],
        "source": "Generic Resolution",
    }


# ==============================================================================
# SCOPE ADHERENCE & DESK-REJECT AUDITING ENGINE
# ==============================================================================

NOT_ASSESSED_RISK = "Not assessed (insufficient data on the journal's scope)"

_TOPIC_STOPWORDS = {
    "and", "the", "for", "with", "from", "their", "based", "studies", "study", "research",
    "analysis", "applications", "methods", "techniques", "approaches", "related", "various",
}

# OpenAlex topic domains -> manuscript areas (Physical Sciences covers both exact sciences and engineering).
OPENALEX_DOMAIN_AREAS = {
    "Life Sciences": ("biologicas",),
    "Health Sciences": ("saude",),
    "Physical Sciences": ("exatas", "engenharias"),
    "Social Sciences": ("humanas",),
}


def _topic_in_text(topic: str, text_lower: str) -> bool:
    """OpenAlex topic names are phrases ("Gut microbiota and health"): match them by content words."""
    topic_l = topic.lower()
    if re.search(rf"\b{re.escape(topic_l)}\b", text_lower):
        return True
    words = [w for w in re.findall(r"[a-z][a-z-]{3,}", topic_l) if w not in _TOPIC_STOPWORDS]
    if len(words) < 2:
        return False
    hits = sum(1 for w in words if re.search(rf"\b{re.escape(w.rstrip('s'))}", text_lower))
    return hits >= max(2, -(-2 * len(words) // 3))


def _infer_journal_areas(topics: list[dict[str, Any]]) -> tuple[set[str], float]:
    """Areas covering >= 30% of a journal's OpenAlex topics, and the share of the dominant domain."""
    domains = [t.get("domain") for t in topics if t.get("domain") in OPENALEX_DOMAIN_AREAS]
    if not domains:
        return set(), 0.0
    shares = {d: domains.count(d) / len(domains) for d in set(domains)}
    areas = {a for d, share in shares.items() if share >= 0.3 for a in OPENALEX_DOMAIN_AREAS[d]}
    return areas, max(shares.values())

def audit_journal_scope(
    manuscript_text: str,
    target_journal_input: str,
    scientific_area_meta: dict[str, Any] | None = None,
    word_count: int = 0,
    figure_count: int = 0,
    table_count: int = 0,
    *,
    online: bool = True,
) -> dict[str, Any]:
    """Analyze scope adherence, calculate desk-reject risk, check guidelines, and suggest alternatives.

    ``word_count`` should be the main-text count (see ``estimate_body_word_count``); when omitted
    it is estimated from ``manuscript_text`` excluding the reference list.
    """
    journal = resolve_journal(target_journal_input, online=online)
    curated_key = journal.get("curated_key")
    text_lower = manuscript_text.lower()
    if word_count <= 0:
        word_count = estimate_body_word_count(manuscript_text)

    area_code = scientific_area_meta.get("area_code", "unknown") if scientific_area_meta else "unknown"
    article_type_code = (
        scientific_area_meta.get("article_type", {}).get("type_code", "original_research")
        if scientific_area_meta
        else "original_research"
    )
    research_approach_code = (
        scientific_area_meta.get("research_approach", {}).get("approach_code", "unknown")
        if scientific_area_meta
        else "unknown"
    )

    desk_reject_flags: list[str] = []
    adherence_points = 50  # Baseline neutral
    # Without curated data or a topic/area signal the score would only reflect the baseline,
    # so the risk is reported as not assessed instead of guessed.
    has_scope_evidence = bool(curated_key)

    # --- 1. Topic & Keyword Matching ---
    matched_topics: list[str] = []
    all_topics = journal.get("topics", []) or journal.get("openalex_topics", [])
    for top in all_topics:
        tname = top.get("name", "")
        if len(tname) > 3 and _topic_in_text(tname, text_lower):
            matched_topics.append(tname)
            adherence_points += 6
    if matched_topics:
        has_scope_evidence = True

    # Match curated keywords/domain if present
    journal_domain = journal.get("domain", "").lower()
    if journal_domain:
        domain_tokens = [t.strip() for t in journal_domain.split(",") if len(t.strip()) > 3]
        for dt in domain_tokens:
            if re.search(rf"\b{re.escape(dt)}\b", text_lower):
                adherence_points += 8

    # --- 2. Area Alignment Check ---
    journal_area = journal.get("area")
    if journal_area == "multidisciplinary":
        adherence_points += 10  # Broad journals accept all fields
    elif journal_area and area_code != "unknown":
        if area_code != journal_area:
            desk_reject_flags.append(
                f"Severe Area Mismatch: The manuscript is classified under '{area_code}', whereas {journal['display_name']} publishes in '{journal_area}'."
            )
            adherence_points -= 40
        else:
            adherence_points += 15
    elif not journal_area and area_code != "unknown":
        inferred_areas, dominant_share = _infer_journal_areas(all_topics)
        if area_code in inferred_areas:
            adherence_points += 15
            has_scope_evidence = True
        elif inferred_areas and dominant_share >= 0.8:
            desk_reject_flags.append(
                f"Probable Area Mismatch: the manuscript is classified under '{area_code}', but "
                f"{journal['display_name']}'s indexed topics fall almost entirely outside it (inferred from OpenAlex)."
            )
            adherence_points -= 25
            has_scope_evidence = True

    # --- 3. Article Type & Pitfall Evaluation ---
    j_name_lower = journal["display_name"].lower()

    # Bioinformatics (OUP): tool/method journal, routine applications are desk-rejected
    if curated_key == "bioinformatics":
        is_routine_app = bool(
            re.search(r"\b(?:we\s+applied|using\s+default\s+parameters|using\s+standard\s+pipeline)\b", text_lower)
            and not re.search(r"(?:we\s+developed\s+a\s+new\s+algorithm|novel\s+method|github\.com/|gitlab\.com/)", text_lower)
        )
        if is_routine_app:
            desk_reject_flags.append(
                "Potential Desk-Reject Risk at Bioinformatics: The manuscript appears to apply standard pipelines rather than proposing a new computational algorithm, software tool, or novel bioinformatic method."
            )
            adherence_points -= 25

    # Briefings in Bioinformatics checks
    if curated_key == "briefings in bioinformatics":
        if article_type_code not in (
            "systematic_review", "meta_analysis", "scoping_review", "narrative_review",
            "integrative_review", "methods_or_protocol_paper",
        ):
            desk_reject_flags.append(
                "Article Type Mismatch for Briefings in Bioinformatics: This journal primarily publishes comprehensive reviews, benchmark comparisons, and protocol evaluations. Primary empirical research is routinely desk-rejected."
            )
            adherence_points -= 35

    # PLOS Computational Biology checks
    if curated_key == "plos computational biology":
        has_bio_insight = bool(
            re.search(r"\b(?:biological\s+insight|mechanism|in\s+vivo|phenotype|disease|pathway|function)\b", text_lower)
        )
        if not has_bio_insight:
            desk_reject_flags.append(
                "PLOS Computational Biology Scope Warning: Journal requires that computational methods lead to significant, novel biological understanding. Pure computational benchmarks without biological insight face desk-reject."
            )
            adherence_points -= 20

    # Clinical journals checks (The Lancet family, JAMA family, NEJM)
    if curated_key in ("the lancet", "jama") or any(
        cj in j_name_lower for cj in ("lancet", "jama", "new england journal")
    ):
        if research_approach_code in ("computational_in_silico", "field_ecological_agronomic", "experimental_lab") or (
            area_code not in ("saude", "unknown")
        ):
            desk_reject_flags.append(
                f"Severe Scope Mismatch for {journal['display_name']}: Top-tier clinical journal requires human clinical studies, randomized trials, or landmark population health research. Pre-clinical or purely computational studies are desk-rejected."
            )
            adherence_points -= 50

    # ACM Computing Surveys
    if curated_key == "acm computing surveys":
        if article_type_code not in (
            "systematic_review", "narrative_review", "scoping_review", "bibliometric_review", "integrative_review",
        ):
            desk_reject_flags.append(
                "ACM Computing Surveys Article Type Mismatch: ACM Computing Surveys exclusively publishes in-depth surveys, tutorials, and taxonomies. Original empirical studies are out of scope."
            )
            adherence_points -= 45

    # --- 4. Length & Author Guidelines Compliance ---
    guideline_warnings: list[str] = []
    max_words = journal.get("max_words_original")
    if max_words and article_type_code == "original_research" and word_count > (max_words * 1.25):
        guideline_warnings.append(
            f"Word Count Exceeded: Main text contains ~{word_count:,} words (references excluded), exceeding the typical limit for {journal['display_name']} (~{max_words:,} words). Trim text before submission to avoid administrative desk-return."
        )
        adherence_points -= 10

    # Mandatory data / code / registration checks. Only curated requirements are known to be the
    # journal's own; the generic ones are reported as typical and do not lower the score.
    is_trial = research_approach_code == "clinical_interventional"
    requirements_verified = bool(curated_key)
    req_penalty = 1 if requirements_verified else 0
    req_label = "mandatory" if requirements_verified else "typical (not verified for this journal)"
    for req in journal.get("mandatory_requirements", []):
        req_l = req.lower()
        if "data availability" in req_l and not re.search(
            r"\bdata\s+availability\b|\bdisponibilidade\s+de\s+dados\b|\bdata\s+(?:sharing|access)\s+statement\b", text_lower
        ):
            guideline_warnings.append(f"Missing {req_label} section for {journal['display_name']}: 'Data Availability Statement'.")
            adherence_points -= 8 * req_penalty
        if "code repository" in req_l and not re.search(
            r"(?:github\.com|gitlab\.com|bitbucket\.org|zenodo\.org|code\s+availability|software\s+availability)", text_lower
        ):
            guideline_warnings.append(f"Missing {req_label} open code requirement for {journal['display_name']}: Code repository link not detected.")
            adherence_points -= 10 * req_penalty
        if "registration" in req_l and is_trial and not re.search(
            r"\b(?:NCT\d{8}|RBR-[a-z0-9]{5,10}|ISRCTN\d{8}|ACTRN\d{14}|EUCTR\d{4}-\d{6}-\d{2}|CTRI/\d{4}/\d{2,3}/\d{6}|DRKS\d{8}|ChiCTR[\w-]{6,})\b",
            manuscript_text,
            re.IGNORECASE,
        ):
            desk_reject_flags.append(f"Fatal Reporting Omission for {journal['display_name']}: Prospective clinical trial registration ID (e.g. ClinicalTrials.gov NCT) not found.")
            adherence_points -= 30

    # --- 5. Adherence Score & Risk Level Calculation ---
    final_score: int | None = max(5, min(98, adherence_points))

    if not has_scope_evidence and not desk_reject_flags:
        final_score = None
        fit_category = "Indeterminate (no curated profile and no topic/area match for this journal)"
        desk_reject_risk = NOT_ASSESSED_RISK
    elif final_score >= 75 and not desk_reject_flags:
        fit_category = "High Adherence (Strong Aims & Scope Fit)"
        desk_reject_risk = "Low Risk"
    elif final_score >= 55 and len(desk_reject_flags) <= 1:
        fit_category = "Moderate Adherence (Acceptable Fit with Reservations)"
        desk_reject_risk = "Moderate Risk"
    elif final_score >= 35:
        fit_category = "Borderline / Questionable Scope Adherence"
        desk_reject_risk = "High Risk of Desk Reject"
    else:
        fit_category = "Out of Scope / Severe Editorial Mismatch"
        desk_reject_risk = "Critical Desk-Reject Risk"

    # --- 6. Alternative Journal Suggestions (only when the fit is actually poor) ---
    poor_fit = desk_reject_risk in ("High Risk of Desk Reject", "Critical Desk-Reject Risk")
    alternatives = journal.get("alternative_journals", []) if poor_fit else []
    if poor_fit and not alternatives and area_code != "unknown":
        if area_code == "biologicas" and research_approach_code != "computational_in_silico":
            alternatives = [
                {"name": "PeerJ (Life & Environment)", "focus": "Broad life-science research judged on scientific soundness."},
                {"name": "PLOS ONE", "focus": "Methodologically rigorous studies without subjective impact thresholds."},
                {"name": "Scientific Reports", "focus": "Sound-science multidisciplinary natural sciences journal."},
            ]
        elif area_code == "biologicas":
            alternatives = [
                {"name": "BMC Bioinformatics", "focus": "Broad bioinformatic applications and software tools."},
                {"name": "PLOS ONE", "focus": "Methodologically rigorous studies without subjective impact thresholds."},
                {"name": "Frontiers in Genetics / Bioinformatics", "focus": "Rapid peer-review for computational genomics."},
            ]
        elif area_code == "saude":
            alternatives = [
                {"name": "BMC Medicine / BMC Public Health", "focus": "High quality biomedical, clinical and population health research."},
                {"name": "PLOS ONE", "focus": "Clinical and epidemiological studies evaluated on technical validity."},
                {"name": "BMJ Open", "focus": "Open access clinical and medical study protocols and papers."},
            ]
        elif area_code == "exatas":
            alternatives = [
                {"name": "IEEE Access", "focus": "Rapid open access for computer science, engineering, and mathematics."},
                {"name": "Pattern Recognition Letters", "focus": "Concise methodological advances in pattern analysis."},
                {"name": "Applied Soft Computing", "focus": "Applied AI and computational intelligence."},
            ]
        else:
            alternatives = [
                {"name": "PLOS ONE", "focus": "Multidisciplinary open access based purely on methodological rigor."},
                {"name": "Scientific Reports", "focus": "Springer Nature sound-science multidisciplinary journal."},
            ]

    return {
        "target_journal": journal["display_name"],
        "publisher": journal.get("publisher", "Unknown Publisher"),
        "issn": journal.get("issn"),
        "homepage_url": journal.get("homepage_url"),
        "is_oa": journal.get("is_oa", False),
        "is_in_doaj": journal.get("is_in_doaj", False),
        "apc_usd": journal.get("apc_usd"),
        "scope_summary": journal.get("scope_summary", ""),
        "adherence_score_pct": final_score,
        "fit_category": fit_category,
        "desk_reject_risk": desk_reject_risk,
        "matched_topics": matched_topics[:6],
        "desk_reject_flags": desk_reject_flags,
        "guideline_warnings": guideline_warnings,
        "common_pitfalls_to_avoid": journal.get("desk_reject_pitfalls", []),
        "alternative_journal_recommendations": alternatives[:4],
        "word_count": word_count,
        "source": journal.get("source", "Auditor"),
    }


def format_scope_markdown(scope: dict[str, Any]) -> str:
    """Format the journal scope and desk-reject audit into clean Markdown."""
    lines: list[str] = [
        "## Target Journal Scope Adherence & Desk-Reject Risk Audit",
        f"- **Target Journal**: **{scope['target_journal']}** ({scope.get('publisher', 'Unknown Publisher')})",
        f"- **Resolution Source**: {scope.get('source', 'Auditor')}",
    ]
    if scope.get("scope_summary"):
        lines.append(f"- **Scope Summary**: {scope['scope_summary']}")
    if scope.get("issn"):
        lines.append(f"- **ISSN**: `{scope['issn']}`" + (f" | **Homepage**: [{scope['target_journal']}]({scope['homepage_url']})" if scope.get("homepage_url") else ""))
    if scope.get("apc_usd") is not None or scope.get("is_oa"):
        if scope.get("is_in_doaj"):
            access = "Fully Open Access (indexed in DOAJ)"
        elif scope.get("is_oa"):
            access = "Open Access"
        else:
            access = "Subscription / Hybrid"
        apc = f" | **APC**: ${scope['apc_usd']:,} USD" if scope.get("apc_usd") is not None else ""
        lines.append(f"- **Access Model**: {access}{apc}")

    score = scope.get("adherence_score_pct")
    score_txt = f"{score}%" if score is not None else "n/a"
    lines.extend([
        f"- **Aims & Scope Adherence Score**: **{score_txt}** (`{scope['fit_category']}`)",
        f"- **Desk-Reject Risk Assessment**: **{scope['desk_reject_risk']}**",
    ])

    if scope.get("matched_topics"):
        lines.append(f"- **Matched Journal Topics/Keywords**: {', '.join(f'`{t}`' for t in scope['matched_topics'])}")

    if scope.get("desk_reject_flags"):
        lines.append("\n### ⚠️ Critical Desk-Reject Red Flags")
        for flag in scope["desk_reject_flags"]:
            lines.append(f"- 🔴 **{flag}**")

    if scope.get("guideline_warnings"):
        lines.append("\n### 📋 Author Guidelines & Formal Submission Warnings")
        for warn in scope["guideline_warnings"]:
            lines.append(f"- 🟡 {warn}")

    if scope.get("common_pitfalls_to_avoid"):
        lines.append(f"\n### 💡 Editorial Nuances & Desk Pitfalls for {scope['target_journal']}")
        for pit in scope["common_pitfalls_to_avoid"]:
            lines.append(f"- {pit}")

    if scope.get("alternative_journal_recommendations"):
        lines.append("\n### 🔄 Recommended Alternative / Cascading Journals")
        for alt in scope["alternative_journal_recommendations"]:
            lines.append(f"- **{alt['name']}**: {alt.get('focus', 'Good scope match for this profile.')}")

    return "\n".join(lines) + "\n"
