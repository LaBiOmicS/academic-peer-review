# Gemini Peer Review — 3-Axis Matrix Reference (`5 Areas × 15 Article Types × 13 Research Approaches`)

## 1. Axis 1: 5 Major Scientific Areas (`--area`)

| Area Code | Major Scientific Area | Area-Specific Audit & Reviewer Focus | Routed Databases |
|---|---|---|---|
| `biologicas` | **Ciências Biológicas, Ômicas, Bioinformática & Agrárias** | Biological vs. technical replicates (pseudoreplication), batch effects, FDR control, raw data accessions (`NCBI SRA/GEO/BioProject`, `ENA`, `PRIDE`, `PDB`), `FAIR/MIAME/MINSEQE`, `CEUA/ARRIVE` & `SisGen`. | OpenAlex, PubMed/EuropePMC, Crossref, arXiv |
| `saude` | **Ciências da Saúde, Medicina Clínica, Epidemiologia & Saúde Coletiva** | EQUATOR Network guidelines (`CONSORT`, `STROBE`, `PRISMA`, `STARD`, `TRIPOD`, `CARE`), clinical registries (`ClinicalTrials.gov NCT`, `ReBEC`, `PROSPERO`), human ethics (`CEP/CONEP/CAAE/IRB`, `TCLE`), clinical effect sizes (`OR/RR/HR`, `95% CI`, `NNT`, `MCID`), `RoB 2` & `GRADE`. | PubMed/EuropePMC, OpenAlex, Crossref |
| `exatas` | **Ciências Exatas e da Terra** *(Matemática, Física, Química, Estatística, Computação & IA)* | **Math/Theory**: proof validity, lemmas, boundary conditions, counterexamples.<br>**Physics/Chemistry**: dimensional/SI consistency, error propagation, `IUPAC/NMR/HRMS/XRD/CIF`.<br>**CS/AI**: complexity, baselines, ablations, data leakage, seed variance. | arXiv, OpenAlex, Crossref |
| `engenharias` | **Engenharias** *(Civil, Elétrica, Mecânica, Química, Materiais, Produção, Biomédica)* | Technical standards (`ISO`, `ASTM`, `IEEE`, `IEC`, `ASME`, `ABNT`), metrological calibration & uncertainty propagation, `FEM/CFD` mesh/grid independence, energy/cost/safety trade-offs (`FMEA`), physical validation. | OpenAlex, Crossref, arXiv |
| `humanas` | **Ciências Humanas, Sociais Aplicadas, Direito, Educação, Linguística, Letras & Artes** | Epistemological coherence, theoretical framework fidelity, qualitative/documentary rigor (`COREQ`, `SRQR`, corpus construction, theoretical saturation, discourse/content analysis, primary/archival source criticism), reflexivity, `CEP-CHS` ethics & anonymization. | OpenAlex, Crossref (including SciELO & Humanities journals) |

---

## 2. Axis 2: 15 Academic Article Types (`--article-type`)

| Type Code | Article Type | International Guidelines & Audit Criteria |
|---|---|---|
| `original_research` | **Artigo Original** *(Empírico, Experimental, Observacional, Computacional ou Teórico)* | Hypothesis/question alignment, experimental/analytical design, controls/baselines, statistical/formal validity, and full reproducibility. |
| `systematic_review` | **Revisão Sistemática (sem Metanálise)** | **PRISMA 2020** & **SWiM**: protocol registration (`PROSPERO`/`OSF`), `PICO/PECO/SPIDER`, boolean strings in $\ge 3$ databases, dual screening, formal Risk of Bias (`RoB 2`, `ROBINS-I`, `NOS`, `QUADAS-2`, `JBI`), and **GRADE** — avoiding vote-counting fallacy. |
| `meta_analysis` | **Revisão Sistemática com Metanálise** *(Tradicional, NMA ou IPD)* | **PRISMA 2020 / MOOSE / PRISMA-NMA**: pooling model justification (REML/Hartung-Knapp vs DerSimonian-Laird), forest plots, heterogeneity ($I^2, \tau^2, Q$, prediction intervals), sensitivity/subgroup analysis, funnel plot / Egger's test, and **GRADE**. |
| `umbrella_review` | **Umbrella Review / Overview of Reviews** *(Revisão Guarda-Chuva)* | **PRIOR Guideline**: quality appraisal of included reviews via **AMSTAR-2** or **ROBIS**, citation matrix & primary study overlap quantification via **Corrected Covered Area (CCA)**. |
| `scoping_review` | **Revisão de Escopo (*Scoping Review*)** | **PRISMA-ScR** & **JBI / Arksey & O'Malley**: **PCC** (*Population, Concept, Context*) framework, protocol registration, grey literature search, evidence charting matrix, and gap identification *(exempt from pooled meta-analysis)*. |
| `integrative_review` | **Revisão Integrativa (*Integrative Review*)** | **Whittemore & Knafl (5 stages) / TORR**: explicit guiding question (*questão norteadora*), integration of empirical and theoretical designs, data reduction matrix, and thematic synthesis. |
| `narrative_review` | **Revisão Narrativa / Crítica / *State-of-the-Art*** | **SANRA** (*Scale for the Assessment of Narrative Review Articles*): importance justification, concrete aims, search/selection transparency to mitigate citation bias, balanced treatment of controversies, and primary-source grounding. |
| `bibliometric_review` | **Revisão Bibliométrica / Cienciométrica / Patentométrica** | **BIBLIO Guideline & Donthu et al.**: databases (`WoS`, `Scopus`, `OpenAlex`, `Dimensions`, `Lens`), retrieval date & search string, **thesaurus disambiguation**, performance analysis + science mapping (`bibliometrix`, `VOSviewer`, `CiteSpace`), and critical intellectual synthesis. |
| `consensus_or_guideline` | **Diretriz Clínica (*Clinical Practice Guideline*) ou Consenso Delphi** | **AGREE II / RIGHT / ACCORD / CREDES**: multidisciplinary panel & COI disclosure, Delphi rounds, pre-specified mathematical consensus threshold, anonymity between rounds, and **GRADE** strength of recommendations. |
| `case_study` | **Relato de Caso Clínico / Série de Casos (`CARE`) ou Estudo de Caso (`Yin / Stake`)** | **Clinical (`CARE`/`PROCESS`)**: timeline, differential diagnosis, intervention, follow-up, signed `TCLE`/consent & de-identification.<br>**Empirical (`Yin/Stake/Eisenhardt`)**: case selection justification, multi-source triangulation, chain of evidence, and analytical generalization. |
| `data_paper` | **Data Paper / Data Descriptor / Genome Announcement** | **FAIR Principles** (*Scientific Data, Data in Brief, MRA*): permanent public accession (`SRA/GEO/BioProject/GenBank/Zenodo/Dryad/PRIDE/GBIF`), **Technical Validation & QC** (`BUSCO`, `CheckM`, `FastQC`, `N50`, coverage, calibration), and metadata dictionary (`MIxS`, `Darwin Core`) — **forbids demanding novel hypothesis testing**. |
| `software_paper` | **Anúncio de Software, Pacote, Pipeline ou Banco de Dados** | **JOSS / FAIR4RS** (*Bioinformatics, SoftwareX, NAR*): OSI open-source license, GitHub/GitLab + Zenodo archive, package manager/container (`bioconda`, `pip`, `CRAN`, `Docker`, `Nextflow`), automated tests/CI, reproducible tutorial, and runtime/memory benchmark. |
| `methods_or_protocol_paper` | **Protocolo Experimental (*STAR/Nature Protocols*) ou Protocolo de Estudo (*SPIRIT/PRISMA-P*)** | **Bench/Lab**: reagent/RRID table, critical steps, timing, **Troubleshooting Table**, controls.<br>**Prospective Study (`SPIRIT`/`PRISMA-P`)**: registry ID, sample size calculation, randomization/blinding, and Statistical Analysis Plan (SAP). |
| `theoretical_essay_perspective` | **Ensaio Teórico, Filosófico, Jurídico, *Perspective*, *Opinion* ou *Commentary*** | Conceptual precision, internal logical/epistemological coherence, *steelman* engagement with counter-arguments, and testable or normative implications *(exempt from empirical dataset demands)*. |
| `short_communication` | **Short Communication, Brief Report, *Matters Arising* ou Nota Científica** | Evaluated proportionally to concise format constraints while requiring full statistical/methodological rigor on the core finding. |

---

## 3. Axis 3: 13 Research Approaches (`--research-approach`)

| Approach Code | Research Approach / Study Design | Methodological Guidelines & Focus |
|---|---|---|
| `clinical_interventional` | **Ensaio Clínico / Intervenção em Humanos** *(RCT, Crossover, Fase I–IV, Quasi-Experimental)* | **CONSORT / TREND**: prospective registry (`NCT`/`ReBEC`), randomization & allocation concealment, blinding, `ITT` vs `Per-Protocol` analysis, participant flow & `CONSORT Harms`. |
| `diagnostic_prognostic_biomarker` | **Acurácia Diagnóstica, Prognóstica ou Validação de Biomarcadores** | **STARD / TRIPOD / REMARK**: reference standard blindness, `ROC-AUC`, `PR-AUC`, sensitivity/specificity/PPV/NPV, calibration curves, and independent external validation cohort. |
| `epidemiological_observational` | **Epidemiológica / Observacional** *(Coorte, Caso-Controle, Transversal, Ecológica, Farmacoepidemiologia)* | **STROBE / RECORD / MOOSE**: source population & selection/recall bias, confounding adjustment (`DAGs`, propensity score, multivariable models), missing data/attrition, `OR/RR/HR/PR` (`95% CI`). |
| `field_ecological_agronomic` | **Pesquisa de Campo, Ecológica, Agronômica, Taxonômica ou Geociências** | **ICZN / ICN / ICTV / Darwin Core**: spatial/seasonal design (`DBC/DIC`, split-plot, transects), spatial pseudoreplication control, voucher specimens & coordinates, taxonomic nomenclature codes. |
| `experimental_lab` | **Experimental de Bancada / *In Vitro* / *In Vivo* Pré-Clínico / Físico-Químico** | **ARRIVE 2.0 / MDAR**: positive, negative & vehicle/sham controls, biological ($n$ independent units) vs technical replicates, cell-line authentication/mycoplasma, randomization & blinding. |
| `computational_in_silico` | **Computacional, *In Silico*, Bioinformática, Simulação (`FEM/CFD/MD`) ou *Machine Learning*** | **TRIPOD+AI / CLAIM / DOME**: data leakage prevention (patient/family/scaffold-level splits), SOTA baselines, ablation studies, hyperparameter sensitivity, random seeds, containers & runtime/memory scaling. |
| `quantitative_statistical` | **Quantitativa, Levantamento (*Survey*), Psicometria ou Econometria** | **COSMIN / APA JARS-Quant**: sampling frame, power calculation, construct validity & reliability ($\alpha, \omega$, `CFA/IRT`), identification strategy (`DiD`, `IV`, `RDD`), `statcheck` & effect sizes. |
| `qualitative` | **Pesquisa Qualitativa** *(Entrevistas, Grupos Focais, Etnografia, Análise de Conteúdo/Discurso)* | **COREQ / SRQR**: purposeful sampling, theoretical/thematic saturation, coding & analytical method (`Bardin`, `Braun & Clarke`, `Grounded Theory`), triangulation, thick description & reflexivity. |
| `mixed_methods` | **Métodos Mistos (*Mixed Methods* — Quali-Quanti)** | **GRAMMS / Creswell & Plano Clark**: explicit design typology (convergent parallel, explanatory/exploratory sequential), parity of rigor in both strands, and *joint displays* / meta-inferences. |
| `action_or_design_science` | **Pesquisa-Ação / Participante (`CBPR`) ou *Design Science Research* (`DSR`)** | **Hevner / Peffers DSR & Thiollent**: problem relevance, iterative build-evaluate or diagnose-act-reflect cycles, stakeholder co-participation, and naturalistic artifact validation. |
| `documentary_archival_historical` | **Pesquisa Documental, Arquivística, Histórica, Filológica ou Jurisprudencial** | **Archival & Source Criticism**: corpus delimitation, primary sources / archives / case-law repositories, internal & external source criticism, historical contextualization & anti-anachronism. |
| `bibliometric_scientometric` | **Pesquisa Bibliométrica / Cienciométrica (Metadados Bibliográficos)** *(set automatically for `bibliometric_review`)* | **BIBLIO / Leiden Manifesto**: query and filters vs. the claimed field, author vs. indexer-assigned keywords, counting and country-attribution rules, citation windows & normalization, Lotka/Bradford informativeness at the corpus size, map sensitivity to thresholds/parameters. Area primary-study checks (replicates, batch effects, accessions, power, FDR) are not applied, and the panel draws its lenses and red-team axes from the article type instead of the area. |
| `theoretical_formal_deductive` | **Teórica, Formal-Dedutiva, Matemática, Filosófica ou Dogmático-Normativa** | **Formal / Epistemic Rigor**: explicit axioms/definitions/premises, step-by-step formal or normative derivation, edge-case & counterexample analysis, and internal consistency. |

---

## 4. Transversal Triggers (Auto-Detected)

1. **`SAGER Guidelines` (Sex and Gender Equity in Research)**: Triggered in biological, preclinical, clinical, and human studies to verify whether biological sex/gender of cells, animals, or human participants is reported and analyzed without unjustified single-sex bias.
2. **`Clinical/Bio-AI` (`TRIPOD+AI`, `CONSORT-AI`, `DECIDE-AI`, `CLAIM`)**: Triggered at the intersection of Health/Biology and Machine Learning/AI to audit patient-level cohort splitting, calibration, subgroup fairness, and external clinical validation.

---

## 5. Panel Composition & Severity Calibration

**Panel slots** are filled in priority order and then shuffled, so codenames do not reveal roles:

| Priority | Role | Template | Disable with |
|---|---|---|---|
| 1 | Epistemic red-team critic | `reviewer_alignment_forum.md` | `--no-alignment-critic` |
| 2 | Author advocate (the critic's counterweight) | `reviewer_author_advocate.md` | `--no-author-advocate` |
| 3 | Methodology & statistics auditor | `reviewer_methodology_stats.md` | `--no-specialist-panel` |
| 4 | Reproducibility & integrity inspector | `reviewer_reproducibility_integrity.md` | `--no-specialist-panel` |
| 5+ | Domain reviewers | `reviewer.md` | — |

The default panel has 5 reviewers, one per role. With `--num-reviewers 3`, the panel keeps the critic, the advocate and the statistics auditor.

**Severity tiers** (shared by every template through `{severity_rubric}`, defined in `spawn_reviewers.py`):

| Tier | Meaning | Test |
|---|---|---|
| `Blocking` | A stated conclusion is wrong or unsupported without the fix | The reviewer must quote the conclusion that fails. At most 5 per report. |
| `Essential` | Reporting, transparency or clarity below the article type's standard | The conclusions may stand. |
| `Optional` | New data, analyses beyond the stated question, scope expansions | The authors may decline with a one-line justification. |

Reviewers must also check what the authors already wrote, verify the direction of any bias they allege, and treat their seeded lens or axis as a hypothesis to test rather than a finding.

**Meta-review safeguards**:
- Reviewer agreement is attribution, not evidence: all reviewers run on the same model.
- Every candidate `Blocking` concern goes through the `## Blocking-concern verification` table before it reaches the roadmap.
- The concerns matrix records each concern's tier and, per reviewer, `major` (in `Major concerns`), `minor` (passing mention) or blank.
- `compile_results.py` inserts the audit figures into the meta-review from `pre_review_audit.json`, stores the audit's SHA-256 in `results.json` (`audit_provenance`), warns when the meta-review contradicts or predates the audit, and writes `author_letter.md` with only the Blocking and Essential items.
