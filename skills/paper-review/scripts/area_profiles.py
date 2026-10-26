#!/usr/bin/env python3
"""3-Axis Scientific Classification & Composable Micro-Rubric Engine for academic-peer-review.

Classifies any academic manuscript across three orthogonal dimensions:
- Axis 1 — 5 Major Scientific Areas (`--area`):
    `biologicas`, `saude`, `exatas`, `engenharias`, `humanas`
- Axis 2 — 15 Academic Article Types (`--article-type`):
    `original_research`, `systematic_review`, `meta_analysis`, `umbrella_review`,
    `scoping_review`, `integrative_review`, `narrative_review`, `bibliometric_review`,
    `case_study`, `data_paper`, `software_paper`, `methods_or_protocol_paper`,
    `consensus_or_guideline`, `theoretical_essay_perspective`, `short_communication`
- Axis 3 — 12 Research Approaches / Methodological Designs (`--research-approach`):
    `experimental_lab`, `clinical_interventional`, `epidemiological_observational`,
    `diagnostic_prognostic_biomarker`, `field_ecological_agronomic`,
    `quantitative_statistical`, `computational_in_silico`, `qualitative`,
    `mixed_methods`, `documentary_archival_historical`, `action_or_design_science`,
    `theoretical_formal_deductive`

Also detects transversal triggers (`SAGER` sex/gender equity and `Clinical/Bio-AI`
reporting guidelines: `TRIPOD+AI`, `CONSORT-AI`, `DECIDE-AI`, `CLAIM`) and composes
a concise, non-redundant micro-rubric (~12 lines) injected into reviewer prompts.
"""

from __future__ import annotations

import re
from functools import cache
from typing import Any

# `\bSEM\b`-style acronyms must stay case-sensitive inside otherwise case-insensitive
# patterns: with re.IGNORECASE, "SEM" matches the Portuguese word "sem", "OR" matches "or", etc.
_ACRONYM_TOKEN = re.compile(r"\\b([A-Z][A-Z0-9]{1,6})\\b")


@cache
def compile_signal_pattern(pat_str: str) -> re.Pattern[str]:
    """Compile a keyword pattern case-insensitively, keeping all-caps acronyms case-sensitive."""
    return re.compile(_ACRONYM_TOKEN.sub(r"(?-i:\\b\1\\b)", pat_str), re.IGNORECASE)


# ============================================================================
# AXIS 1: 5 MAJOR SCIENTIFIC AREAS (GRANDES ÁREAS)
# ============================================================================

AREA_DEFINITIONS: dict[str, dict[str, Any]] = {
    "biologicas": {
        "code": "biologicas",
        "name": "Ciências Biológicas, Ômicas, Bioinformática & Ciências Agrárias",
        "preferred_sources": ["openalex", "pubmed", "crossref", "arxiv"],
        "keywords": [
            r"\b(?:genom\w+|transcriptom\w+|proteom\w+|metabolom\w+|metagenom\w+|epigenom\w+|multi-?omics)\b",
            r"\b(?:RNA-seq|scRNA-seq|ChIP-seq|ATAC-seq|GWAS|WGS|amplicon|16S\s+rRNA|phylogen\w+|ortholog\w+|DESeq2|edgeR|limma|KEGG|Gene\s+Ontology)\b",
            r"\b(?:bioinformatics|biotechnology|molecular\s+biology|cell\s+biology|ecology|biodiversity|taxonom\w+|botan\w+|zoolog\w+|agronom\w+)\b",
            r"\b(?:CRISPR|PCR|qPCR|RT-qPCR|Western\s+blot|flow\s+cytometry|mass\s+spectrometry|BLAST|AlphaFold|UniProt|GenBank|NCBI|Ensembl|GSE\d+|PRJNA\d+|SRR\d+)\b",
            r"\b(?:genoma|genômica|transcriptômica|proteômica|bioinformática|biologia\s+molecular|ecologia|filogenia|biodiversidade)\b",
        ],
        "ssot_lenses": [
            "0 — Experimental design & biological vs. technical replication (pseudoreplication, controls, batch effects)",
            "1 — High-throughput statistical rigor (FDR/Benjamini-Hochberg control, dispersion, power, normalization)",
            "2 — Omics/Bioinformatics pipeline validity (database/tool versions, parameter justification, contamination filtering)",
            "3 — Open data & artifact availability (NCBI SRA/GEO/BioProject, ENA, PRIDE, PDB, GenBank; FAIR/MIAME/MINSEQE)",
            "4 — Functional validation & biological plausibility (orthogonal validation vs. correlational pathway storytelling)",
            "5 — Taxonomic, evolutionary, ecological & ethical compliance (CEUA/ARRIVE, SisGen/Nagoya, strain authentication)",
        ],
        "redteam_axes": [
            "0 — Batch effect or technical confounding masquerading as biological signal",
            "1 — Pseudoreplication (treating technical replicates or cells from one specimen as independent N)",
            "2 — Over-interpreted GO/KEGG enrichment without orthogonal functional validation",
            "3 — Arbitrary fold-change/p-value threshold cherry-picking or outdated database annotations",
            "4 — Missing negative/positive controls or contamination checks (kitome, host DNA, ambient RNA)",
            "5 — Overclaimed novelty or missing comparison against established biological/bioinformatics tools",
            "6 — Uncorrected multiple hypothesis testing across high-dimensional features",
            "7 — Missing raw sequence/mass-spec/structure accessions (SRA, GEO, PRIDE, PDB)",
        ],
        "micro_rubric": (
            "- **Area (`biologicas`)**: Audit biological vs. technical replicates (pseudoreplication), batch-effect control, "
            "FDR correction in high-dimensional assays, public data accessions (`NCBI SRA/GEO/BioProject/GenBank`, `ENA`, `PRIDE`, `PDB`), "
            "`FAIR/MIAME/MINSEQE`, and applicable ethics/biodiversity registries (`CEUA/ARRIVE`, `SisGen/Nagoya`)."
        ),
    },
    "saude": {
        "code": "saude",
        "name": "Ciências da Saúde, Medicina Clínica, Epidemiologia & Saúde Coletiva",
        "preferred_sources": ["pubmed", "openalex", "crossref"],
        "keywords": [
            r"\b(?:clinical\s+trial|randomized\s+controlled|placebo|cohort\s+study|case-control|cross-sectional|epidemiolog\w+|public\s+health|nursing)\b",
            r"\b(?:patient\w*|symptom\w*|diagnos\w+|prognos\w+|therap\w+|treatment|morbidity|mortality|prevalence|incidence|comorbidit\w+|hospital\w*)\b",
            r"\b(?:CONSORT|STROBE|PRISMA|STARD|TRIPOD|CARE|ClinicalTrials\.gov|PROSPERO|ReBEC|RoB\s*2|GRADE)\b",
            r"\b(?:odds\s+ratio|hazard\s+ratio|relative\s+risk|Kaplan-Meier|Cox\s+regression|logistic\s+regression|informed\s+consent|\bIRB\b)\b",
            r"\b(?:pacientes?|ensaio\s+clínico|coorte|caso-controle|epidemiol\w+|saúde\s+pública|saúde\s+coletiva|enferm\w+|clínic\w+|atenção\s+primária|\bSUS\b|CEP|CONEP|CAAE|TCLE|desfecho\s+clínico)\b",
        ],
        "ssot_lenses": [
            "0 — Study design & EQUATOR guideline compliance (CONSORT, STROBE, PRISMA, STARD, TRIPOD, CARE)",
            "1 — Biostatistical rigor & clinical relevance (power, OR/RR/HR with 95% CI, MCID/NNT vs. mere p-value)",
            "2 — Selection bias, clinical confounding, attrition, and internal validity",
            "3 — Prospective protocol registration & primary endpoint fidelity (ClinicalTrials.gov, ReBEC, PROSPERO)",
            "4 — Human research ethics, safety & demographic equity (IRB / CEP-CONEP / CAAE, TCLE, adverse events)",
            "5 — External multi-center clinical generalizability, calibration & decision-curve utility",
        ],
        "redteam_axes": [
            "0 — Unregistered primary outcome switching or post-hoc subgroup HARKing",
            "1 — Confounding by indication, immortal time bias, or unadjusted clinical covariates",
            "2 — Statistical significance without clinical relevance (below MCID)",
            "3 — Attrition / loss-to-follow-up bias or improper missing-data imputation",
            "4 — Single-center convenience sampling overclaimed as broadly generalizable",
            "5 — Lack of external validation cohort or calibration in clinical prediction/biomarker models",
            "6 — Missing or retrospective clinical registry ID (NCT / ReBEC / PROSPERO)",
            "7 — Incomplete human ethics disclosure (CEP/CONEP/IRB approval, TCLE, competing interests)",
        ],
        "micro_rubric": (
            "- **Area (`saude`)**: Enforce EQUATOR Network reporting standards, prospective registration (`ClinicalTrials.gov NCT`, `ReBEC`, `PROSPERO`), "
            "human ethics approval (`IRB / CEP-CONEP / CAAE` & `TCLE`), effect sizes with `95% CI` (`OR/RR/HR`, `NNT`, `MCID`), and confounding/attrition control."
        ),
    },
    "exatas": {
        "code": "exatas",
        "name": "Ciências Exatas e da Terra (Matemática, Física, Química, Estatística, Computação & IA)",
        "preferred_sources": ["arxiv", "openalex", "crossref"],
        "keywords": [
            r"\b(?:theorem|lemma|corollary|proposition|proof|banach|hilbert|manifold|topology|differential\s+equation|stochastic|markov)\b",
            r"\b(?:quantum|hamiltonian|lagrangian|thermodynamic\w+|spectroscop\w+|crystallograph\w+|catalys\w+|synthesis|DFT|molecular\s+dynamics)\b",
            r"\b(?:algorithm\w*|complexity|NP-hard|neural\s+network|transformer|deep\s+learning|reinforcement\s+learning|benchmark|ablation)\b",
            r"\b(?:teorema|lema|demonstração|algoritmo|aprendizado\s+de\s+máquina|física|química|espectroscopia|termodinâmica)\b",
        ],
        "ssot_lenses": [
            "0 — Formal & mathematical rigor (proofs, lemmas, regularity assumptions, boundary cases, counterexamples)",
            "1 — Empirical benchmark fairness & baseline parity (tuning budget, strong SOTA baselines, zero data leakage)",
            "2 — Ablation completeness & mechanistic attribution (isolating each proposed term/module/mechanism)",
            "3 — Physical/chemical consistency & uncertainty (SI units, conservation laws, error propagation, IUPAC/NMR/XRD/CIF)",
            "4 — Algorithmic & numerical reproducibility (asymptotic complexity, conditioning, random seeds, open code/weights)",
            "5 — Novelty attribution & out-of-distribution / scaling limits",
        ],
        "redteam_axes": [
            "0 — Distinguishing-test failure (experiments/derivations do not rule out simpler competing explanations)",
            "1 — Weak, untuned, or outdated baselines (unfair compute/hyperparameter budget)",
            "2 — Missing ablations (multi-component method without isolating individual contributions)",
            "3 — Unstated or unrealistic mathematical/physical assumptions or idealized regimes",
            "4 — Train/test data leakage, benchmark overfitting, or cherry-picked trajectories",
            "5 — Overclaimed novelty (known mathematical/physical/algorithmic method rebranded)",
            "6 — Missing error bars, multi-seed variance, or experimental uncertainty propagation",
            "7 — Reproducibility gap (omitted proof steps, hyperparameters, chemical characterization, or code)",
        ],
        "micro_rubric": (
            "- **Area (`exatas`)**: Audit formal proof validity and boundary conditions (for Math/Theory); dimensional/SI consistency, "
            "uncertainty propagation, and `IUPAC/NMR/HRMS/XRD/CIF` characterization (for Physics/Chemistry/Earth); or complexity, "
            "fair baselines, ablations, seed variance, and zero train/test leakage (for CS/Statistics/AI)."
        ),
    },
    "engenharias": {
        "code": "engenharias",
        "name": "Engenharias (Civil, Elétrica, Mecânica, Química, Materiais, Produção, Biomédica & Ambiental)",
        "preferred_sources": ["openalex", "crossref", "arxiv"],
        "keywords": [
            r"\b(?:finite\s+element|\bFEM\b|\bFEA\b|\bCFD\b|Reynolds|Navier-Stokes|microstructure|tensile\s+strength|fatigue|corrosion|tribolog\w+)\b",
            r"\b(?:IEEE|ASTM|ISO\s+\d+|ABNT|NBR|IEC\s+\d+|ASME|PID\s+controller|FPGA|ASIC|MOSFET|photovoltaic|smart\s+grid|power\s+electronics)\b",
            r"\b(?:heat\s+transfer|mass\s+transfer|chemical\s+reactor|supply\s+chain|ergonomics|structural\s+integrity|sensor\s+calibration|actuat\w+)\b",
            r"\b(?:engenharia|elementos\s+finitos|resistência\s+dos\s+materiais|usinagem|controle\s+e\s+automação|eficiência\s+energética|norma\s+técnica)\b",
        ],
        "ssot_lenses": [
            "0 — Normative & technical standard compliance (ISO, ASTM, IEEE, IEC, ASME, ABNT protocols)",
            "1 — Metrology, sensor calibration & measurement uncertainty propagation",
            "2 — Numerical simulation rigor (FEM/CFD mesh/grid independence, time-step convergence, physical validation)",
            "3 — System trade-offs & scalability (energy efficiency, latency, durability, thermal stability, cost)",
            "4 — Benchmarking against current industrial/engineering state-of-the-art under realistic disturbances",
            "5 — Safety factors, failure mode analysis (FMEA), environmental impact & TRL realism",
        ],
        "redteam_axes": [
            "0 — Unvalidated simulation-only claims lacking mesh-independence study or physical testbench verification",
            "1 — Idealized lab/boundary conditions that fail under realistic industrial loads, noise, or thermal drift",
            "2 — Missing metrological uncertainty propagation, sensor calibration, or repeatability metrics",
            "3 — Non-compliance with standard engineering test protocols (ASTM, ISO, IEEE, IEC, ABNT)",
            "4 — Unacknowledged engineering trade-offs (improving one metric while degrading power, cost, or safety)",
            "5 — Comparison against obsolete baselines instead of modern industrial/engineering standards",
            "6 — Scale-up blindness (extrapolating benchtop results without dimensional/similarity analysis)",
            "7 — Missing geometry, material property, schematic, or solver tolerance disclosure",
        ],
        "micro_rubric": (
            "- **Area (`engenharias`)**: Check compliance with technical standards (`ISO`, `ASTM`, `IEEE`, `IEC`, `ASME`, `ABNT`), "
            "instrument calibration and uncertainty propagation, `FEM/CFD` mesh-independence and experimental validation, "
            "and practical engineering trade-offs (energy, cost, scalability, `FMEA` safety factors)."
        ),
    },
    "humanas": {
        "code": "humanas",
        "name": "Ciências Humanas, Sociais Aplicadas, Direito, Educação, Linguística, Letras & Artes",
        "preferred_sources": ["openalex", "crossref"],
        "keywords": [
            r"\b(?:epistemolog\w+|hermeneutic\w+|phenomenolog\w+|ethnograph\w+|historiograph\w+|discourse\s+analysis)\b",
            r"\b(?:sociolog\w+|anthropolog\w+|pedagog\w+|curricul\w+|jurisprudence|constitutional|public\s+policy|political\s+science|semiotics|linguistics)\b",
            r"\b(?:Foucault|Bourdieu|Habermas|Vygotsky|Paulo\s+Freire|Weber|Durkheim|Marx|Heidegger|Kant|Bakhtin|Deleuze)\b",
            r"\b(?:epistemologia|hermenêutica|etnografia|historiografia|análise\s+do\s+discurso|ciências\s+sociais|ciências\s+humanas)\b",
            r"\b(?:educação|pedagogia|direito|jurisprudência|políticas\s+públicas|sociologia|antropologia|filosofia|linguística|literatura)\b",
        ],
        "ssot_lenses": [
            "0 — Epistemological coherence & theoretical framework fidelity (internal consistency of concepts and categories)",
            "1 — Methodological rigor in empirical/qualitative/documentary design (corpus selection, saturation, COREQ/SRQR, archival critique)",
            "2 — Argumentative structure & evidence-to-thesis grounding (avoiding leaps from isolated quotes to sweeping claims)",
            "3 — Dialogue with primary sources, canonical scholarship, and rival theoretical interpretations",
            "4 — Researcher reflexivity, positionality & human-subject ethics (CEP-CHS, TCLE, anonymization)",
            "5 — Historical, legal, institutional & socio-cultural contextualization (avoiding anachronism or normative fallacy)",
        ],
        "redteam_axes": [
            "0 — Theoretical eclecticism (combining incompatible epistemological traditions without conceptual mediation)",
            "1 — Anecdotalism / cherry-picked excerpts used merely to illustrate a pre-decided conclusion",
            "2 — Methodological opacity in corpus construction, fieldwork, coding categories, or saturation",
            "3 — Circular reasoning or normative leap (deriving 'ought' from 'is' or restating premises as findings)",
            "4 — Omission of rival interpretations, counter-archives, or foundational scholarship",
            "5 — Anachronism or over-generalization beyond the specific historical/cultural/legal context studied",
            "6 — Strawman portrayal of opposing theoretical schools or authors",
            "7 — Imprecise primary/archival source citation or missing human-ethics/anonymization safeguards (CEP-CHS)",
        ],
        "micro_rubric": (
            "- **Area (`humanas`)**: Audit epistemological coherence, conceptual precision, primary/archival source criticism or "
            "qualitative rigor (`COREQ/SRQR`, saturation, reflexivity, `CEP-CHS` ethics & anonymization). Do **not** demand frequentist "
            "$p$-values or ML baselines unless the paper itself makes quantitative/econometric/psychometric claims."
        ),
    },
}


# ============================================================================
# AXIS 2: 15 ACADEMIC ARTICLE TYPES (TIPOLOGIAS DE ARTIGO)
# ============================================================================

ARTICLE_TYPE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "meta_analysis": {
        "code": "meta_analysis",
        "name": "Revisão Sistemática com Metanálise (PRISMA 2020 / MOOSE / PRISMA-NMA)",
        "guidelines": ["PRISMA 2020", "MOOSE", "PRISMA-NMA", "GRADE"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:meta-analysis|meta-analytic|metanálise|meta-análise|forest\s+plot|funnel\s+plot|DerSimonian|random-effects\s+model|heterogeneity\s+I2|I\^2\s*=)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`meta_analysis` — PRISMA 2020 / MOOSE)**: Verify `PROSPERO/OSF` registration, `PICO/PECO` question, "
            "reproducible search in ≥ 3 databases, dual screening, Risk of Bias (`RoB 2/ROBINS-I/NOS/QUADAS-2`), pooling model justification "
            "(REML/Hartung-Knapp vs DerSimonian-Laird), heterogeneity ($I^2, \\tau^2, Q$, prediction intervals), sensitivity/subgroup analysis, "
            "publication bias (funnel plot/Egger), and `GRADE` certainty."
        ),
    },
    "umbrella_review": {
        "code": "umbrella_review",
        "name": "Umbrella Review / Overview of Reviews (PRIOR / AMSTAR-2 / ROBIS)",
        "guidelines": ["PRIOR", "AMSTAR-2", "ROBIS", "GRADE"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:umbrella\s+review|overview\s+of\s+systematic\s+reviews|meta-review\s+of\s+systematic\s+reviews|AMSTAR-?2|ROBIS|corrected\s+covered\s+area|\bCCA\b|revisão\s+guarda-chuva)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`umbrella_review` — PRIOR)**: Require methodological quality appraisal of included systematic reviews via "
            "`AMSTAR-2` or `ROBIS`, quantification of primary study overlap across reviews via citation matrix and **Corrected Covered Area (CCA)**, "
            "and reconciliation of discordant meta-analyses."
        ),
    },
    "scoping_review": {
        "code": "scoping_review",
        "name": "Revisão de Escopo / Scoping Review (PRISMA-ScR / JBI / PCC)",
        "guidelines": ["PRISMA-ScR", "JBI Scoping Review Methodology", "Arksey & O'Malley"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:scoping\s+review|PRISMA-ScR|Arksey\s+and\s+O'Malley|Joanna\s+Briggs\s+Institute\s+scoping|revisão\s+de\s+escopo)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`scoping_review` — PRISMA-ScR / JBI)**: Verify `PCC` (*Population, Concept, Context*) question, protocol registration, "
            "multi-database + grey literature search, standardized data charting table, and conceptual/gap mapping. Do **not** demand quantitative meta-analysis."
        ),
    },
    "bibliometric_review": {
        "code": "bibliometric_review",
        "name": "Revisão Bibliométrica / Cienciométrica / Patentométrica (BIBLIO / Donthu et al.)",
        "guidelines": ["BIBLIO Guideline", "Donthu et al. (2021)", "Aria & Cuccurullo (bibliometrix)"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:bibliometric\s+analysis|bibliometric\s+review|scientometric\w*|VOSviewer|bibliometrix|Biblioshiny|CiteSpace|co-citation\s+analysis|bibliographic\s+coupling|Bradford'?s\s+law|Lotka'?s\s+law|análise\s+bibliométrica|revisão\s+bibliométrica|cienciometria)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`bibliometric_review` — BIBLIO / Donthu et al.)**: Audit database selection (`WoS/Scopus/OpenAlex/Dimensions/Lens`), "
            "exact query/date/filters, **thesaurus disambiguation** (author/affiliation/keyword cleaning), performance metrics + science mapping "
            "(`bibliometrix/VOSviewer/CiteSpace` co-citation, coupling, co-word clusters), and penalize superficial 'button-pushing' descriptive lists."
        ),
    },
    "integrative_review": {
        "code": "integrative_review",
        "name": "Revisão Integrativa (Whittemore & Knafl / TORR)",
        "guidelines": ["Whittemore & Knafl (2005)", "TORR"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:integrative\s+review|integrative\s+literature\s+review|Whittemore\s+and\s+Knafl|revisão\s+integrativa)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`integrative_review` — Whittemore & Knafl / TORR)**: Audit explicit guiding question (*questão norteadora*), "
            "transparent search/selection, critical appraisal of diverse study designs (empirical + theoretical), data reduction matrix, "
            "and synthesis by thematic axes rather than chronological abstract-by-abstract summaries."
        ),
    },
    "systematic_review": {
        "code": "systematic_review",
        "name": "Revisão Sistemática sem Metanálise (PRISMA 2020 / SWiM)",
        "guidelines": ["PRISMA 2020", "SWiM", "PROSPERO", "GRADE"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:systematic\s+review|systematic\s+literature\s+review|\bSLR\b|PRISMA\s+2020|PROSPERO|Kitchenham|revisão\s+sistemática)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`systematic_review` — PRISMA 2020 / SWiM)**: Verify `PROSPERO/OSF` registration, `PICO/PECO/SPIDER/Kitchenham` question, "
            "boolean strings across ≥ 3 databases, PRISMA flow diagram, dual screening, formal Risk of Bias (`RoB 2/ROBINS-I/NOS/JBI/MMAT`), "
            "and `SWiM` structured synthesis (avoiding p-value vote-counting)."
        ),
    },
    "narrative_review": {
        "code": "narrative_review",
        "name": "Revisão Narrativa / Crítica / State-of-the-Art (SANRA)",
        "guidelines": ["SANRA (Scale for the Assessment of Narrative Review Articles)", "RAMESES"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:narrative\s+review|critical\s+review|state-of-the-art\s+review|mini-review|literature\s+review|SANRA|revisão\s+narrativa|revisão\s+de\s+literatura|revisão\s+crítica)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`narrative_review` — SANRA)**: Evaluate (1) justification of importance, (2) concrete aims/questions, "
            "(3) literature selection transparency to mitigate citation bias, (4) primary-source referencing quality, "
            "(5) balanced discussion of competing hypotheses/controversies, and (6) critical synthesis of future research directions."
        ),
    },
    "consensus_or_guideline": {
        "code": "consensus_or_guideline",
        "name": "Diretriz Clínica / Consenso de Especialistas / Painel Delphi (AGREE II / ACCORD / CREDES)",
        "guidelines": ["AGREE II", "RIGHT", "ACCORD (Delphi)", "CREDES", "GRADE"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:Delphi\s+consensus|Delphi\s+study|expert\s+consensus|clinical\s+practice\s+guideline|\bAGREE\s+II\b|\bACCORD\b|\bCREDES\b|consenso\s+de\s+especialistas|painel\s+Delphi|diretriz\s+clínica)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`consensus_or_guideline` — AGREE II / ACCORD / CREDES)**: Audit multidisciplinary panel selection, "
            "conflict-of-interest management, systematic evidence review preceding recommendations, Delphi round structure (response rates, "
            "anonymity, mathematical threshold for consensus, stability across rounds), and `GRADE` strength of recommendations."
        ),
    },
    "data_paper": {
        "code": "data_paper",
        "name": "Data Paper / Data Descriptor / Genome Announcement (FAIR / Scientific Data / MRA)",
        "guidelines": ["FAIR Principles", "MIxS / MIGS", "Darwin Core", "DataCite"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:data\s+descriptor|data\s+paper|dataset\s+paper|genome\s+announcement|draft\s+genome\s+sequence|complete\s+genome\s+sequence|genome\s+note|microbiology\s+resource\s+announcements|Scientific\s+Data|Data\s+in\s+Brief|BUSCO|CheckM|N50)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`data_paper` — FAIR / Data Descriptor)**: **Do NOT demand novel hypothesis testing!** Audit permanent public "
            "repository accessions (`NCBI SRA/GEO/BioProject/GenBank`, `ENA`, `PRIDE`, `Zenodo`, `Dryad`, `GBIF`), **Technical Validation & QC** "
            "(`FastQC/MultiQC`, `BUSCO`, `CheckM`, `N50`, coverage depth, sensor calibration), metadata dictionary (`MIxS/Darwin Core`), and reuse notes."
        ),
    },
    "software_paper": {
        "code": "software_paper",
        "name": "Anúncio de Software, Pacote, Pipeline ou Banco de Dados (JOSS / FAIR4RS / NAR)",
        "guidelines": ["FAIR4RS", "JOSS Review Criteria", "ELIXIR Software Best Practices"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:open-source\s+software|Python\s+package|R\s+package|Bioconductor\s+package|Bioconda|web\s+server|command-line\s+tool|Nextflow\s+pipeline|Snakemake\s+workflow|JOSS|SoftwareX|application\s+note)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`software_paper` — JOSS / FAIR4RS)**: Audit Statement of Need, public VCS repository (`GitHub/GitLab`) + "
            "archival DOI (`Zenodo`), OSI open-source license, standard installation (`bioconda/pip/CRAN/Docker/Nextflow`), automated tests/CI, "
            "reproducible tutorial with sample data, and accuracy/runtime/memory benchmarks against competing tools."
        ),
    },
    "case_study": {
        "code": "case_study",
        "name": "Relato de Caso Clínico / Série de Casos (CARE) ou Estudo de Caso (Yin / Stake)",
        "guidelines": ["CARE Guidelines", "PROCESS", "Yin / Stake / Eisenhardt"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:case\s+report|clinical\s+case|case\s+series|CARE\s+guidelines|CARE\s+checklist|relato\s+de\s+caso|série\s+de\s+casos|estudo\s+de\s+caso\s+único|multiple-case\s+study)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`case_study` — CARE / Yin & Stake)**: For clinical cases (`CARE`), require chronological timeline, differential "
            "diagnosis reasoning, intervention/follow-up, patient de-identification, and signed publication `TCLE`/consent. For empirical case studies "
            "(`Yin/Stake/Eisenhardt`), require case selection justification, multi-source triangulation, chain of evidence, and analytical generalization."
        ),
    },
    "methods_or_protocol_paper": {
        "code": "methods_or_protocol_paper",
        "name": "Protocolo Experimental (STAR/Nature Protocols) ou Protocolo Prospectivo (SPIRIT/PRISMA-P)",
        "guidelines": ["SPIRIT 2013", "PRISMA-P", "Nature Protocols / STAR Protocols"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:study\s+protocol|trial\s+protocol|SPIRIT\s+statement|SPIRIT\s+checklist|PRISMA-P|step-by-step\s+protocol|STAR\s+Protocols|Nature\s+Protocols|protocolo\s+de\s+estudo|protocolo\s+experimental)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`methods_or_protocol_paper` — SPIRIT / PRISMA-P / STAR Protocols)**: For prospective study protocols, audit registry ID, "
            "sample size calculation, blinding, and pre-specified Statistical Analysis Plan (`SAP`). For experimental protocols, audit reagent/RRID table, "
            "critical steps, timings, positive/negative controls, and a **Troubleshooting Table**."
        ),
    },
    "theoretical_essay_perspective": {
        "code": "theoretical_essay_perspective",
        "name": "Ensaio Teórico, Filosófico, Jurídico, Perspective, Opinion ou Commentary",
        "guidelines": ["Epistemological & Argumentative Coherence", "Steelmanning"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:theoretical\s+essay|perspective\s+article|opinion\s+piece|commentary|viewpoint|position\s+paper|ensaio\s+teórico|artigo\s+de\s+opinião|artigo\s+de\s+perspectiva)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`theoretical_essay_perspective`)**: Audit conceptual precision, internal logical/epistemological consistency, "
            "fair engagement with the strongest counter-arguments (*steelmanning*), and testable predictions or normative/policy implications."
        ),
    },
    "short_communication": {
        "code": "short_communication",
        "name": "Short Communication, Brief Report, Matters Arising ou Nota Científica",
        "guidelines": ["Concise Reporting Standards"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:short\s+communication|brief\s+report|brief\s+communication|rapid\s+communication|matters\s+arising|scientific\s+note|research\s+note|comunicação\s+breve|nota\s+científica|nota\s+prévia)\b",
        ],
        "micro_rubric": (
            "- **Article Type (`short_communication`)**: Evaluate proportionally to concise format constraints (do not demand multi-study expansion), "
            "while holding the core experiment, statistical analysis, and data availability to full rigor."
        ),
    },
    "original_research": {
        "code": "original_research",
        "name": "Artigo Original de Pesquisa",
        "guidelines": ["Area & Research-Approach Reporting Standards"],
        "exempt_from_inferential_stats": False,
        "patterns": [],
        "micro_rubric": (
            "- **Article Type (`original_research`)**: Verify hypothesis/question alignment, controls/baselines, analytical validity, "
            "and complete open-science reproducibility."
        ),
    },
}


# ============================================================================
# AXIS 3: 12 RESEARCH APPROACHES / METHODOLOGICAL DESIGNS (ABORDAGENS)
# ============================================================================

RESEARCH_APPROACH_DEFINITIONS: dict[str, dict[str, Any]] = {
    "clinical_interventional": {
        "code": "clinical_interventional",
        "name": "Ensaio Clínico / Estudo Intervencionista em Humanos (CONSORT / TREND)",
        "guidelines": ["CONSORT 2010", "TREND", "CONSORT Harms"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:randomi[sz]ed\s+(?:controlled\s+|clinical\s+|crossover\s+)?trial|\bRCT\b|double-blind|placebo-controlled|intention-to-treat|allocation\s+concealment|CONSORT|ensaio\s+clínico\s+randomizado)\b",
            r"\b(?:(?:were|was)\s+randomi[sz]ed\s+to|randomly\s+(?:assigned|allocated)|phase\s+(?:I{1,3}|IV|[1-4])\s+(?:clinical\s+)?trial|trial\s+registration|NCT\d{8}|ISRCTN\d{8}|RBR-[a-z0-9]{5,10}|ensaio\s+clínico|randomizad[oa]s?\s+(?:para|em)|alocad[oa]s?\s+aleatoriamente|ensayo\s+clínico\s+aleatorizado)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`clinical_interventional` — CONSORT / TREND)**: Audit randomization & allocation concealment, blinding, "
            "Intention-to-Treat (`ITT`) vs Per-Protocol analysis, prospective endpoint registration, baseline balance, and harms/adverse events."
        ),
    },
    "diagnostic_prognostic_biomarker": {
        "code": "diagnostic_prognostic_biomarker",
        "name": "Acurácia Diagnóstica, Modelo Prognóstico ou Validação de Biomarcador (STARD / TRIPOD / REMARK)",
        "guidelines": ["STARD 2015", "TRIPOD / TRIPOD+AI", "REMARK"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:diagnostic\s+accuracy|prognostic\s+model|biomarker\s+validation|ROC\s+curve|AUROC|AUC-ROC|sensitivity\s+and\s+specificity|calibration\s+curve|decision\s+curve\s+analysis|STARD|TRIPOD|REMARK)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`diagnostic_prognostic_biomarker` — STARD / TRIPOD / REMARK)**: Audit reference-standard blinding, "
            "sensitivity/specificity/PPV/NPV, `ROC-AUC` & `PR-AUC` with 95% CIs, model calibration curves, decision-curve clinical utility, "
            "and validation on an independent external cohort (preventing overfitted biomarker signatures)."
        ),
    },
    "epidemiological_observational": {
        "code": "epidemiological_observational",
        "name": "Pesquisa Epidemiológica / Observacional: Coorte, Caso-Controle, Transversal ou Ecológica (STROBE)",
        "guidelines": ["STROBE", "RECORD", "MOOSE"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:cohort\s+study|case-control\s+study|cross-sectional\s+study|ecological\s+study|STROBE|odds\s+ratio|hazard\s+ratio|incidence\s+rate|prevalence\s+ratio|estudo\s+de\s+coorte|caso-controle|estudo\s+transversal|epidemiológic\w+)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`epidemiological_observational` — STROBE)**: Audit eligibility & follow-up/response rates, multivariable "
            "confounding control (DAGs, propensity score, adjusted OR/RR/HR), reverse causality, ecological fallacy, and sensitivity to missing data."
        ),
    },
    "field_ecological_agronomic": {
        "code": "field_ecological_agronomic",
        "name": "Pesquisa de Campo, Ecológica, Taxonômica, Florestal, Geológica ou Agronômica",
        "guidelines": ["ICZN / ICN / ICTV / ICNP", "Darwin Core"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:field\s+experiment|randomized\s+complete\s+block|split-plot|transect\w*|quadrat\w*|voucher\s+specimen|herbarium|holotype|paratype|ICZN|delineamento\s+em\s+blocos\s+casualizados|\bDBC\b|inventário\s+florestal|amostragem\s+em\s+campo)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`field_ecological_agronomic`)**: Audit spatial/seasonal replication (avoiding site pseudoreplication), "
            "experimental layout (randomized blocks `DBC/DIC`, split-plot, transects), taxonomic nomenclature rules (`ICZN/ICN/ICTV/ICNP`), "
            "voucher specimen deposition in accredited collections, and geographic/environmental metadata."
        ),
    },
    "experimental_lab": {
        "code": "experimental_lab",
        "name": "Pesquisa Experimental de Bancada / Laboratorial (In Vitro, In Vivo, Físico-Química ou Materiais)",
        "guidelines": ["ARRIVE 2.0", "MDAR Framework"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:in\s+vitro|in\s+vivo|ex\s+vivo|cell\s+culture|western\s+blot|qPCR|RT-qPCR|flow\s+cytometry|mice|rats|zebrafish|ARRIVE|tensile\s+test|scanning\s+electron\s+microscopy|\bSEM\b|\bXRD\b)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`experimental_lab`)**: Audit positive/negative/vehicle controls, biological vs technical replication, "
            "blinding & randomization of experimental units, reagent/cell-line/strain authentication (`RRID`), and instrument calibration."
        ),
    },
    "computational_in_silico": {
        "code": "computational_in_silico",
        "name": "Pesquisa Computacional, Bioinformática, Simulação Numérica (FEM/CFD) ou Modelagem/IA",
        "guidelines": ["TRIPOD+AI / CLAIM", "DOME Recommendations"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:in\s+silico|bioinformatic\w+|molecular\s+docking|molecular\s+dynamics|finite\s+element|\bFEM\b|\bCFD\b|neural\s+network|machine\s+learning|deep\s+learning|cross-validation|ablation\s+study|RNA-seq|GWAS|metagenom\w+)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`computational_in_silico`)**: Audit pipeline/software/database versions, parameter & hyperparameter sensitivity, "
            "strict train/validation/test separation (zero leakage), baseline fairness, ablation or mesh-convergence verification, and code/seed availability."
        ),
    },
    "mixed_methods": {
        "code": "mixed_methods",
        "name": "Pesquisa de Métodos Mistos / Quanti-Quali (GRAMMS)",
        "guidelines": ["GRAMMS", "Creswell & Plano Clark Mixed-Methods Standards"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:mixed\s+methods|mixed-methods|quanti-quali|convergent\s+parallel|explanatory\s+sequential|exploratory\s+sequential|GRAMMS|métodos\s+mistos|pesquisa\s+quanti-qualitativa)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`mixed_methods` — GRAMMS)**: Audit justification for mixing quantitative and qualitative designs, "
            "sequence/priority of phases (convergent, sequential explanatory/exploratory), rigor of each individual strand, and genuine "
            "joint integration (*joint displays* / triangulation) rather than two disconnected mini-studies."
        ),
    },
    "action_or_design_science": {
        "code": "action_or_design_science",
        "name": "Pesquisa-Ação, Pesquisa Participante (CBPR) ou Design Science Research (DSR)",
        "guidelines": ["Hevner / Peffers DSR", "Thiollent / CBPR Action Research"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:design\s+science\s+research|\bDSR\b|action\s+research|participatory\s+action\s+research|\bCBPR\b|Hevner|Peffers|Thiollent|pesquisa-ação|pesquisa\s+participante)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`action_or_design_science` — DSR / Action Research)**: For `DSR` (*Hevner/Peffers*), audit problem relevance, "
            "artifact design cycle, rigorous evaluation in context, and design theory contribution. For *Action/Participatory Research* (*Thiollent/CBPR*), "
            "audit iterative diagnosis-action-reflection cycles, stakeholder co-participation, and ethical reflexivity."
        ),
    },
    "documentary_archival_historical": {
        "code": "documentary_archival_historical",
        "name": "Pesquisa Documental, Arquivística, Historiográfica, Exegética ou Jurisprudencial",
        "guidelines": ["Archival & Documentary Source Criticism", "Historiographical Standards"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:archival\s+research|historiograph\w+|primary\s+sources|documentary\s+research|jurisprudenc\w+|case\s+law|pesquisa\s+documental|fontes\s+primárias|acervo\s+histórico|análise\s+jurisprudencial)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`documentary_archival_historical`)**: Audit corpus delimitation and provenance, internal/external source criticism, "
            "contextualization of historical/legal documents (avoiding anachronism or selective cherry-picking of rulings/texts), and verifiable archival references."
        ),
    },
    "qualitative": {
        "code": "qualitative",
        "name": "Pesquisa Qualitativa Empírica: Entrevistas, Grupos Focais, Etnografia, Discurso/Conteúdo (COREQ / SRQR)",
        "guidelines": ["COREQ", "SRQR", "APA JARS-Qual"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:qualitative\s+study|qualitative\s+research|semi-structured\s+interview\w*|focus\s+group\w*|ethnograph\w+|discourse\s+analysis|content\s+analysis|thematic\s+analysis|COREQ|SRQR|Bardin|Braun\s+and\s+Clarke|pesquisa\s+qualitativa|análise\s+de\s+conteúdo|análise\s+do\s+discurso|grupos\s+focais)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`qualitative` — COREQ / SRQR)**: Audit participant selection & theoretical saturation, interview/fieldwork guide transparency, "
            "coding tree & inter-coder/interpretive rigor (e.g., Bardin, Braun & Clarke, discourse analysis), negative/deviant cases, researcher reflexivity, and `CEP/TCLE` anonymization."
        ),
    },
    "theoretical_formal_deductive": {
        "code": "theoretical_formal_deductive",
        "name": "Pesquisa Teórico-Formal, Matemática, Físico-Teórica, Filosófica ou Dogmático-Jurídica",
        "guidelines": ["Formal Deductive & Epistemic Consistency"],
        "exempt_from_inferential_stats": True,
        "patterns": [
            r"\b(?:Theorem\s+\d|Lemma\s+\d|Proposition\s+\d|Corollary\s+\d|Proof\.|Q\.E\.D\.|Teorema\s+\d|Demonstração|hermeneutic\w+|phenomenolog\w+|dogmática\s+jurídica|hermenêutica)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`theoretical_formal_deductive`)**: Audit axiom/premise explicitness, step-by-step deductive or mathematical proof validity, "
            "boundary/degenerate cases, conceptual precision, and engagement with counterexamples or rival theoretical schools."
        ),
    },
    "quantitative_statistical": {
        "code": "quantitative_statistical",
        "name": "Pesquisa Quantitativa, Survey, Psicometria, Econometria ou Modelagem Estatística",
        "guidelines": ["COSMIN", "APA JARS-Quant", "statcheck"],
        "exempt_from_inferential_stats": False,
        "patterns": [
            r"\b(?:Cronbach'?s\s+alpha|confirmatory\s+factor\s+analysis|\bCFA\b|structural\s+equation\s+modeling|\bSEM\b|Likert|panel\s+data|instrumental\s+variable\w*|difference-in-differences|ANOVA|linear\s+regression)\b",
        ],
        "micro_rubric": (
            "- **Research Approach (`quantitative_statistical`)**: Audit sampling frame & non-response bias, instrument validity/reliability "
            "(Cronbach's $\\alpha$, McDonald's $\\omega$, CFA), statistical test assumptions (normality, homoscedasticity, multicollinearity, endogeneity), "
            "`statcheck` p-value consistency, effect sizes, and multiple-testing correction."
        ),
    },
}


# ============================================================================
# ALIASES & CLASSIFICATION ENGINE
# ============================================================================

DOMAIN_HINT_ALIASES: dict[str, str] = {
    "biologicas": "biologicas", "biológicas": "biologicas", "biology": "biologicas",
    "bioinformatics": "biologicas", "bioinformática": "biologicas", "omics": "biologicas",
    "ômicas": "biologicas", "genomics": "biologicas", "ecology": "biologicas",
    "agronomy": "biologicas", "agrarias": "biologicas", "agrárias": "biologicas",
    "saude": "saude", "saúde": "saude", "health": "saude", "medicine": "saude",
    "medicina": "saude", "clinical": "saude", "epidemiology": "saude", "nursing": "saude",
    "dentistry": "saude", "public health": "saude", "neuroscience": "saude",
    "exatas": "exatas", "exact": "exatas", "mathematics": "exatas", "matemática": "exatas",
    "physics": "exatas", "física": "exatas", "chemistry": "exatas", "química": "exatas",
    "computer science": "exatas", "computação": "exatas", "machine learning": "exatas",
    "artificial intelligence": "exatas", "statistics": "exatas",
    "engenharias": "engenharias", "engenharia": "engenharias", "engineering": "engenharias",
    "electrical": "engenharias", "mechanical": "engenharias",
    "materials": "engenharias", "chemical engineering": "engenharias", "biomedical engineering": "engenharias",
    "humanas": "humanas", "humanities": "humanas", "social sciences": "humanas",
    "ciências sociais": "humanas", "sociology": "humanas", "anthropology": "humanas",
    "history": "humanas", "história": "humanas", "law": "humanas", "direito": "humanas",
    "education": "humanas", "educação": "humanas", "philosophy": "humanas",
    "filosofia": "humanas", "linguistics": "humanas", "letras": "humanas", "psychology": "humanas",
    "economics": "humanas", "economia": "humanas", "political science": "humanas", "ciência política": "humanas",
    "psicologia": "humanas", "geology": "exatas", "geologia": "exatas", "geosciences": "exatas", "geociências": "exatas",
    "astronomy": "exatas", "astronomia": "exatas", "veterinary": "saude", "veterinária": "saude",
    "pharmacy": "saude", "farmácia": "saude", "pharmacology": "saude", "farmacologia": "saude",
    "civil engineering": "engenharias", "engenharia civil": "engenharias",
}

ARTICLE_TYPE_ALIASES: dict[str, str] = {
    "original": "original_research", "original_research": "original_research", "artigo original": "original_research",
    "systematic_review": "systematic_review", "systematic review": "systematic_review", "revisao sistematica": "systematic_review", "revisão sistemática": "systematic_review",
    "meta_analysis": "meta_analysis", "meta-analysis": "meta_analysis", "metanalise": "meta_analysis", "metanálise": "meta_analysis",
    "umbrella_review": "umbrella_review", "umbrella review": "umbrella_review", "revisão guarda-chuva": "umbrella_review",
    "scoping_review": "scoping_review", "scoping review": "scoping_review", "revisao de escopo": "scoping_review", "revisão de escopo": "scoping_review",
    "integrative_review": "integrative_review", "integrative review": "integrative_review", "revisao integrativa": "integrative_review", "revisão integrativa": "integrative_review",
    "narrative_review": "narrative_review", "narrative review": "narrative_review", "revisao narrativa": "narrative_review", "revisão narrativa": "narrative_review",
    "bibliometric_review": "bibliometric_review", "bibliometric": "bibliometric_review", "bibliometria": "bibliometric_review", "revisao bibliometrica": "bibliometric_review", "revisão bibliométrica": "bibliometric_review",
    "consensus_or_guideline": "consensus_or_guideline", "consensus": "consensus_or_guideline", "delphi": "consensus_or_guideline", "guideline": "consensus_or_guideline", "diretriz": "consensus_or_guideline",
    "case_study": "case_study", "case report": "case_study", "estudo de caso": "case_study", "relato de caso": "case_study",
    "data_paper": "data_paper", "data paper": "data_paper", "data descriptor": "data_paper", "genome announcement": "data_paper", "genome note": "data_paper",
    "software_paper": "software_paper", "software": "software_paper", "anuncio de software": "software_paper", "anúncio de software": "software_paper", "application note": "software_paper",
    "methods_or_protocol_paper": "methods_or_protocol_paper", "protocol": "methods_or_protocol_paper", "protocolo": "methods_or_protocol_paper",
    "theoretical_essay_perspective": "theoretical_essay_perspective", "essay": "theoretical_essay_perspective", "ensaio": "theoretical_essay_perspective", "perspective": "theoretical_essay_perspective", "opinion": "theoretical_essay_perspective",
    "short_communication": "short_communication", "short communication": "short_communication", "brief report": "short_communication", "nota cientifica": "short_communication", "nota científica": "short_communication",
}

RESEARCH_APPROACH_ALIASES: dict[str, str] = {
    "clinical": "clinical_interventional", "rct": "clinical_interventional", "ensaio clinico": "clinical_interventional",
    "diagnostic": "diagnostic_prognostic_biomarker", "biomarker": "diagnostic_prognostic_biomarker", "prognostic": "diagnostic_prognostic_biomarker",
    "epidemiological": "epidemiological_observational", "epidemiologica": "epidemiological_observational", "observational": "epidemiological_observational", "coorte": "epidemiological_observational",
    "field": "field_ecological_agronomic", "ecological": "field_ecological_agronomic", "agronomic": "field_ecological_agronomic", "campo": "field_ecological_agronomic",
    "experimental": "experimental_lab", "lab": "experimental_lab", "in vitro": "experimental_lab", "in vivo": "experimental_lab",
    "computational": "computational_in_silico", "in silico": "computational_in_silico", "bioinformatics": "computational_in_silico", "simulation": "computational_in_silico",
    "mixed": "mixed_methods", "mixed_methods": "mixed_methods", "quanti-quali": "mixed_methods", "metodos mistos": "mixed_methods",
    "action": "action_or_design_science", "dsr": "action_or_design_science", "design science": "action_or_design_science", "pesquisa-acao": "action_or_design_science",
    "documentary": "documentary_archival_historical", "archival": "documentary_archival_historical", "documental": "documentary_archival_historical", "historiografica": "documentary_archival_historical",
    "qualitative": "qualitative", "qualitativa": "qualitative",
    "theoretical": "theoretical_formal_deductive", "teorica": "theoretical_formal_deductive", "formal": "theoretical_formal_deductive",
    "quantitative": "quantitative_statistical", "quantitativa": "quantitative_statistical", "survey": "quantitative_statistical",
}


def _resolve_alias(hint: str | None, definitions: dict[str, Any], aliases: dict[str, str]) -> str | None:
    """Map a free-text hint to a code by whole-word alias match, longest alias first.

    Whole-word matching avoids "economics" -> "omics" or "collaborative" -> "lab"; trying the
    longest alias first lets "chemical engineering" win over "chemistry"-like shorter aliases.
    """
    if not hint:
        return None
    clean = " ".join(hint.strip().lower().split())
    if clean in definitions:
        return clean
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(alias)}(?![\w-])", clean):
            return aliases[alias]
    return None


def resolve_area_code(area_or_domain: str | None) -> str | None:
    return _resolve_alias(area_or_domain, AREA_DEFINITIONS, DOMAIN_HINT_ALIASES)


def resolve_article_type_code(article_type_hint: str | None) -> str | None:
    return _resolve_alias(article_type_hint, ARTICLE_TYPE_DEFINITIONS, ARTICLE_TYPE_ALIASES)


def resolve_research_approach_code(approach_hint: str | None) -> str | None:
    return _resolve_alias(approach_hint, RESEARCH_APPROACH_DEFINITIONS, RESEARCH_APPROACH_ALIASES)


def classify_article_type(text: str, explicit_type: str = "auto") -> dict[str, Any]:
    if explicit_type and explicit_type != "auto":
        forced = resolve_article_type_code(explicit_type)
        if forced:
            spec = ARTICLE_TYPE_DEFINITIONS[forced]
            return {
                "type_code": forced,
                "type_name": spec["name"],
                "guidelines": spec["guidelines"],
                "exempt_from_inferential_stats": spec["exempt_from_inferential_stats"],
                "matched_signals": ["explicit_override"],
            }

    head_text = text[:6000]
    type_scores: dict[str, int] = {}
    matched_signals: dict[str, list[str]] = {}

    for code, spec in ARTICLE_TYPE_DEFINITIONS.items():
        if code == "original_research":
            continue
        score = 0
        matches: list[str] = []
        for pat_str in spec["patterns"]:
            pat = compile_signal_pattern(pat_str)
            head_hits = pat.findall(head_text)
            body_hits = pat.findall(text)
            score += len(head_hits) * 4 + len(body_hits)
            for h in body_hits:
                s = h if isinstance(h, str) else str(h)
                if s.lower() not in [m.lower() for m in matches]:
                    matches.append(s)
        if score > 0:
            type_scores[code] = score
            matched_signals[code] = matches[:8]

    if type_scores:
        if "meta_analysis" in type_scores and type_scores["meta_analysis"] >= 2:
            best_type = "meta_analysis"
        else:
            best_type = max(type_scores.items(), key=lambda kv: kv[1])[0]
    else:
        best_type = "original_research"

    spec = ARTICLE_TYPE_DEFINITIONS[best_type]
    return {
        "type_code": best_type,
        "type_name": spec["name"],
        "guidelines": spec["guidelines"],
        "exempt_from_inferential_stats": spec["exempt_from_inferential_stats"],
        "matched_signals": matched_signals.get(best_type, []),
    }


REFERENCES_HEADING_REGEX = re.compile(
    r"(?im)^\s*(?:#+\s*|\d+\.?\s*)?(?:references|bibliography|literature\s+cited|works\s+cited|"
    r"referências(?:\s+bibliográficas)?|referencias(?:\s+bibliográficas)?|bibliografía|bibliografia)\s*:?\s*$"
)
PAGE_MARKER_REGEX = re.compile(r"^--- \[Page \d+\] ---$", re.MULTILINE)


def strip_reference_list(text: str) -> str:
    """Main text without page markers and the trailing reference list."""
    body = PAGE_MARKER_REGEX.sub("", text)
    headings = list(REFERENCES_HEADING_REGEX.finditer(body))
    if headings:
        last = headings[-1]
        # Ignore a heading in the first fifth of the text (e.g. a table-of-contents entry).
        if last.start() > len(body) * 0.2:
            body = body[: last.start()]
    return body


# An explicit design statement ("a cross-sectional study", "randomised controlled trial") outweighs
# technique vocabulary (e.g. "metagenomic", "machine learning") that any design can mention.
DESIGN_DECLARATIONS = {
    "clinical_interventional": re.compile(
        r"\b(?:randomi[sz]ed\s+(?:controlled\s+|clinical\s+)?trial|ensaio\s+clínico\s+randomizado|ensayo\s+clínico\s+aleatorizado)\b",
        re.IGNORECASE,
    ),
    "epidemiological_observational": re.compile(
        r"\b(?:cohort|case-control|cross-sectional|ecological)\s+(?:study|design|survey)\b|"
        r"\bestudo\s+(?:de\s+coorte|caso-controle|transversal|ecológico)\b|"
        r"\bestudio\s+(?:de\s+cohorte|de\s+casos\s+y\s+controles|transversal)\b",
        re.IGNORECASE,
    ),
    "diagnostic_prognostic_biomarker": re.compile(
        r"\bdiagnostic\s+accuracy\s+study\b|\bestudo\s+de\s+acurácia\s+diagnóstica\b", re.IGNORECASE
    ),
    "qualitative": re.compile(
        r"\b(?:qualitative\s+(?:study|research|design)|estudo\s+qualitativo|pesquisa\s+qualitativa|estudio\s+cualitativo)\b",
        re.IGNORECASE,
    ),
    "mixed_methods": re.compile(r"\bmixed[\s-]methods?\s+(?:study|design|approach)\b|\bmétodos\s+mistos\b", re.IGNORECASE),
}
DESIGN_DECLARATION_WEIGHT = 25


def classify_research_approach(text: str, best_area: str, explicit_approach: str = "auto") -> dict[str, Any]:
    if explicit_approach and explicit_approach != "auto":
        forced = resolve_research_approach_code(explicit_approach)
        if forced:
            spec = RESEARCH_APPROACH_DEFINITIONS[forced]
            return {
                "approach_code": forced,
                "approach_name": spec["name"],
                "guidelines": spec.get("guidelines", ["Methodological Rigor Standards"]),
                "exempt_from_inferential_stats": spec["exempt_from_inferential_stats"],
                "confidence": 1.0,
            }

    # Cited titles describe other studies' designs, not this one.
    text = strip_reference_list(text)
    head_text = text[:6000]
    scores: dict[str, int] = {}
    for code, spec in RESEARCH_APPROACH_DEFINITIONS.items():
        score = 0
        for pat_str in spec["patterns"]:
            pat = compile_signal_pattern(pat_str)
            score += len(pat.findall(head_text)) * 3 + len(pat.findall(text))
        declaration = DESIGN_DECLARATIONS.get(code)
        if declaration:
            score += DESIGN_DECLARATION_WEIGHT * min(2, len(declaration.findall(text)))
        if score > 0:
            scores[code] = score

    if scores:
        best_approach = max(scores.items(), key=lambda kv: kv[1])[0]
        confidence = round(scores[best_approach] / sum(scores.values()), 2)
    else:
        confidence = 0.0  # no design signal at all: area default below
        default_by_area = {
            "biologicas": "experimental_lab",
            "saude": "epidemiological_observational",
            "exatas": "computational_in_silico",
            "engenharias": "computational_in_silico",
            "humanas": "qualitative",
        }
        best_approach = default_by_area.get(best_area, "quantitative_statistical")

    spec = RESEARCH_APPROACH_DEFINITIONS[best_approach]
    return {
        "approach_code": best_approach,
        "approach_name": spec["name"],
        "guidelines": spec.get("guidelines", ["Methodological Rigor Standards"]),
        "exempt_from_inferential_stats": spec["exempt_from_inferential_stats"],
        "confidence": confidence,
    }


def detect_transversal_flags(text: str, area_code: str, approach_code: str) -> dict[str, bool]:
    """Detect transversal reporting dimensions (SAGER sex/gender equity & Clinical/Bio-AI)."""
    involves_subjects_or_bio = area_code in ("biologicas", "saude") or bool(
        re.search(r"\b(?:patients|participants|mice|rats|animals|cohort|pacientes|participantes|camundongos)\b", text, re.IGNORECASE)
    )
    sex_or_gender_reported = bool(
        re.search(r"\b(?:male\s+and\s+female|sex-disaggregated|biological\s+sex|gender\s+distribution|SAGER|sexo\s+biológico|masculino\s+e\s+feminino)\b", text, re.IGNORECASE)
    )
    is_clinical_or_bio_ai = (
        area_code in ("saude", "biologicas")
        and (
            approach_code in ("computational_in_silico", "diagnostic_prognostic_biomarker")
            or bool(re.search(r"\b(?:machine\s+learning|deep\s+learning|neural\s+network|random\s+forest|XGBoost|TRIPOD\+AI|CONSORT-AI|DECIDE-AI|CLAIM)\b", text, re.IGNORECASE))
        )
    )
    return {
        "sager_applicable": involves_subjects_or_bio,
        "sager_sex_gender_reported": sex_or_gender_reported,
        "clinical_or_bio_ai_applicable": is_clinical_or_bio_ai,
    }


def compose_rubric(area_info: dict[str, Any]) -> str:
    """Compose a concise, non-redundant 3-axis micro-rubric (~10-12 lines total)."""
    area_spec = AREA_DEFINITIONS.get(area_info["area_code"], AREA_DEFINITIONS["exatas"])
    type_code = area_info["article_type"]["type_code"]
    type_spec = ARTICLE_TYPE_DEFINITIONS.get(type_code, ARTICLE_TYPE_DEFINITIONS["original_research"])
    app_code = area_info["research_approach"]["approach_code"]
    app_spec = RESEARCH_APPROACH_DEFINITIONS.get(app_code, RESEARCH_APPROACH_DEFINITIONS["quantitative_statistical"])
    tf = area_info.get("transversal_flags", {})

    lines = [
        "### Tailored 3-Axis Evaluation Rubric (Area × Article Type × Research Approach)",
        area_spec["micro_rubric"],
        type_spec["micro_rubric"],
        app_spec["micro_rubric"],
    ]
    if tf.get("sager_applicable"):
        lines.append(
            "- **Transversal (`SAGER Guidelines`)**: Verify whether biological sex and/or gender of human participants, animals, or cell lines are reported and whether sex-disaggregated analysis or single-sex justification is provided."
        )
    if tf.get("clinical_or_bio_ai_applicable"):
        lines.append(
            "- **Transversal (`Clinical/Bio-AI — TRIPOD+AI / CONSORT-AI / CLAIM`)**: Audit cohort partitioning (patient-level split to prevent data leakage), subgroup fairness/calibration, feature explainability caveats, and external validation."
        )
    return "\n".join(lines)


AREA_CONFIDENCE_THRESHOLD = 0.7
APPROACH_CONFIDENCE_THRESHOLD = 0.6


def classify_manuscript(
    text: str,
    domain_hint: str = "",
    explicit_area: str = "auto",
    explicit_article_type: str = "auto",
    explicit_research_approach: str = "auto",
) -> dict[str, Any]:
    """Classify manuscript across all 3 orthogonal axes + transversal flags."""
    forced_code = None
    if explicit_area and explicit_area != "auto":
        forced_code = resolve_area_code(explicit_area)
    if not forced_code and domain_hint:
        forced_code = resolve_area_code(domain_hint)

    head_text = text[:6000]
    scores: dict[str, int] = {code: 0 for code in AREA_DEFINITIONS}
    matched_terms: dict[str, list[str]] = {code: [] for code in AREA_DEFINITIONS}

    for code, spec in AREA_DEFINITIONS.items():
        for pat_str in spec["keywords"]:
            pat = compile_signal_pattern(pat_str)
            head_hits = pat.findall(head_text)
            body_hits = pat.findall(text)
            score = len(head_hits) * 3 + len(body_hits)
            scores[code] += score
            if body_hits:
                sample = body_hits[0] if isinstance(body_hits[0], str) else str(body_hits[0])
                if sample.lower() not in [m.lower() for m in matched_terms[code]]:
                    matched_terms[code].append(sample)

    if forced_code:
        best_code = forced_code
    else:
        best_code = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores[best_code] == 0:
            best_code = "exatas"

    article_type = classify_article_type(text, explicit_type=explicit_article_type)
    research_approach = classify_research_approach(text, best_code, explicit_approach=explicit_research_approach)
    transversal = detect_transversal_flags(text, best_code, research_approach["approach_code"])

    total_score = sum(scores.values()) or 1
    confidence = round(min(0.99, max(0.35, scores[best_code] / total_score)), 2) if not forced_code else 1.0

    # Keyword scores cannot settle a close call; the orchestrating agent confirms these axes
    # from the abstract and methods (or asks the user) before the panel is prepared.
    low_confidence_axes = []
    if confidence < AREA_CONFIDENCE_THRESHOLD:
        low_confidence_axes.append("area")
    if research_approach["confidence"] < APPROACH_CONFIDENCE_THRESHOLD:
        low_confidence_axes.append("research_approach")

    profile = AREA_DEFINITIONS[best_code]
    return {
        "area_code": best_code,
        "area_name": profile["name"],
        "study_design": research_approach["approach_code"],
        "research_approach": research_approach,
        "article_type": article_type,
        "transversal_flags": transversal,
        "confidence": confidence,
        "needs_confirmation": bool(low_confidence_axes),
        "low_confidence_axes": low_confidence_axes,
        "area_scores": scores,
        "matched_signals": matched_terms[best_code][:10],
        "preferred_sources": profile["preferred_sources"],
    }


def get_area_profile(area_code: str) -> dict[str, Any]:
    return AREA_DEFINITIONS.get(area_code, AREA_DEFINITIONS["exatas"])


def get_article_type_profile(type_code: str) -> dict[str, Any]:
    return ARTICLE_TYPE_DEFINITIONS.get(type_code, ARTICLE_TYPE_DEFINITIONS["original_research"])


def get_research_approach_profile(approach_code: str) -> dict[str, Any]:
    return RESEARCH_APPROACH_DEFINITIONS.get(approach_code, RESEARCH_APPROACH_DEFINITIONS["quantitative_statistical"])


# ============================================================================
# INFORMATION SECURITY: UNICODE SANITIZATION & PROMPT-INJECTION SCANNER
# ============================================================================

INVISIBLE_AND_BIDI_REGEX = re.compile(
    # Zero-width/bidi controls, C0 controls, and Unicode "tag" characters (U+E0000-E007F),
    # which can smuggle invisible ASCII instructions into text.
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\x00-\x08\x0b\x0c\x0e-\x1f\x7f\U000e0000-\U000e007f]"
)

PROMPT_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore\s+(?:all\s+)?(?:previous|prior|above|system)\s+instructions|disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions|forget\s+all\s+previous\s+instructions|"
            r"ignor[ea]\s+(?:todas\s+)?as\s+instruções\s+(?:anteriores|acima)|desconsidere\s+(?:todas\s+)?as\s+instruções|"
            r"ignora\s+(?:todas\s+)?las\s+instrucciones\s+(?:anteriores|previas))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "reviewer_verdict_manipulation",
        re.compile(
            r"\b(?:if\s+you\s+are\s+an?\s+(?:AI|LLM|language\s+model|automated)\s+reviewer|as\s+an?\s+(?:AI|LLM)\s+reviewer\s*,?\s*you\s+must|give\s+this\s+paper\s+a\s+strong\s+accept|output\s+only\s+the\s+verdict\s+accept|do\s+not\s+mention\s+any\s+weaknesses\s+or\s+flaws|"
            r"give\s+(?:a\s+)?positive\s+review(?:\s+only)?|do\s+not\s+highlight\s+any\s+negatives|"
            r"(?:dê|faça)\s+(?:uma\s+)?(?:avaliação|revisão|parecer)\s+positiv[ao]|"
            r"(?:da|haz)\s+(?:una\s+)?(?:evaluación|revisión)\s+positiva)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hidden_text_latex_or_css",
        re.compile(
            r"(?:\\textcolor\s*\{\s*white\s*\}|\\color\s*\{\s*white\s*\}|font-size\s*:\s*0(?:\.0+)?(?:px|pt|em)|opacity\s*:\s*0(?:\.0+)?\b|display\s*:\s*none)",
            re.IGNORECASE,
        ),
    ),
    (
        "delimiter_or_system_tag_spoofing",
        re.compile(
            r"(?:<\s*/?\s*UNTRUSTED_MANUSCRIPT_CONTENT\s*/?\s*>|<\s*/?\s*SYSTEM_INSTRUCTION\s*>|<\s*\|im_start\|\s*>|<\s*\|endoftext\|\s*>)",
            re.IGNORECASE,
        ),
    ),
]


def sanitize_and_scan_manuscript(text: str) -> tuple[str, dict[str, Any]]:
    """Strip invisible/bidi control characters, neutralize delimiter spoofing, and scan for prompt injection."""
    invisible_hits = INVISIBLE_AND_BIDI_REGEX.findall(text)
    cleaned = INVISIBLE_AND_BIDI_REGEX.sub("", text)

    # Neutralize any attempt to break out of the untrusted manuscript XML delimiter
    cleaned = re.sub(
        r"<\s*/?\s*UNTRUSTED_MANUSCRIPT_CONTENT\s*/?\s*>",
        "[REDACTED_DELIMITER_TAG]",
        cleaned,
        flags=re.IGNORECASE,
    )

    findings: list[dict[str, str]] = []
    # Unicode tag characters mirror ASCII (U+E0020 = " "); decode them so hidden payloads are reported.
    smuggled = "".join(chr(ord(ch) - 0xE0000) for ch in invisible_hits if 0xE0020 <= ord(ch) <= 0xE007E)
    if smuggled.strip():
        findings.append({"category": "unicode_tag_smuggling", "matched_text": " ".join(smuggled.split())[:120]})
    for category, pat in PROMPT_INJECTION_PATTERNS:
        for m in pat.finditer(text):
            snippet = " ".join(m.group(0).split())[:120]
            findings.append({"category": category, "matched_text": snippet})

    security_report = {
        "invisible_or_bidi_chars_stripped": len(invisible_hits),
        "suspicious_prompt_injection_count": len(findings),
        "suspicious_patterns": findings[:15],
        "is_clean": len(findings) == 0 and len(invisible_hits) < 20,
    }
    return cleaned, security_report

