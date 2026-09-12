# Build-from-Scratch Research Compendium
## Edge-Native Renewable Asset Intelligence Platform
### Every dataset, paper, method, model, and tool needed to build the system

**Purpose:** This document is the research foundation for building the Renewable Asset Intelligence platform from zero. For every component of the architecture, it lists (1) the research that validates the approach, (2) the concrete methods to implement, (3) the datasets to train/evaluate on, and (4) the open-source tools to use.

**Research cutoff:** September 2026. All URLs verified during research.

---

# PART 1 — RESEARCH LANDSCAPE: WHAT THE FIELD HAS ALREADY PROVEN

Before building anything, understand what the research literature already establishes — because a hackathon judge who knows this domain will check whether you know it too.

## 1.1 Wind turbine anomaly detection is a mature, benchmarked field

The single most important dataset for our wind layer is **CARE to Compare** (Müller et al., 2024, MDPI Data). It is the largest real-world wind SCADA benchmark for early fault detection:

- **95 sub-datasets, 36 turbines, 3 wind farms (Portugal onshore + 2 German offshore)**
- **89 years of SCADA time series total, 10-minute resolution**
- **44 datasets contain labeled anomaly events; 51 contain only normal behavior** (this balance matters — it lets you measure false-alarm rate, not just detection)
- Every anomaly has an annotated start timestamp; the "anomaly" period ends where the turbine fault begins
- Up to 957 features on wind farm C (SCADA tags)
- Paper: https://www.mdpi.com/2306-5729/9/12/138
- Data: https://zenodo.org/records/15846963
- Kaggle mirror: https://www.kaggle.com/datasets/azizkasimov/wind-turbine-scada-data-for-early-fault-detection

### Critical benchmark result that shapes our architecture

The CARE paper ran a mini-benchmark. The results are one of the most valuable pieces of intelligence for our design:

| Approach | CARE score |
|---|---|
| Random baseline | 0.50 |
| **Autoencoder (AE)** | **0.66 (best)** |
| Isolation Forest | **0.14 (worse than random)** |

Key lesson: **Isolation Forest alone fails badly on real SCADA data** — it cannot recognize normal behavior over long periods. A reconstruction-based model (autoencoder) trained on normal data is the correct MVP backbone for anomaly detection on turbine SCADA. This validates our report's choice of residual + AE approaches over naive IF.

The CARE score itself (Coverage, Accuracy, Reliability, Earliness) is a 4-part composite:
- **Coverage** — detect as many real anomalies as possible
- **Accuracy** — recognize normal behavior correctly (long normal periods dominate)
- **Reliability** — few false alarm *events* (an event requires ≥72 consecutive anomalous 10-min points, i.e., ~12h sustained, before an alarm fires)
- **Earliness** — detect before the fault becomes critical (later detections within an event are weighted down linearly)

We should adopt the CARE score verbatim as our wind anomaly evaluation metric. The 72-consecutive-points alarm rule is also a free "alert storm suppression" mechanism for our system.

### Hybrid ensembles are the SOTA on wind SCADA

Aslam et al. (2025, ACM) benchmarked a hybrid of Autoencoder + Isolation Forest + XGBoost + Random Forest + LSTM on a Wind Turbine SCADA dataset:

- **Precision 0.9832, Recall 0.9360, F1 0.9590, Accuracy 0.9461**
- Paper: https://dl.acm.org/doi/full/10.1145/3709021.3737669

Their ablation is instructive: standalone RF got F1 0.9201, standalone IF 0.9331 — but the hybrid stacked model hit 0.9590. Lesson: ensemble > single model, and the AE/IF/XGB/RF/LSTM combo is a proven, implementable configuration (no exotic architecture needed).

## 1.2 Normal Behavior Models (NBM) are the established paradigm for condition monitoring

The wind condition-monitoring literature converges on one paradigm: **Normal Behavior Modeling** — train a model on fault-free data to predict a target signal (usually power, or drivetrain temperatures) from operating conditions, then monitor the **residual** (actual − predicted).

- Review (Wind Energy Science, 2023): "Overview of normal behavior modeling approaches for wind turbine time series data" — https://wes.copernicus.org/articles/8/893/2023/
- Power curve review (Energies, 2022): https://www.mdpi.com/1996-1073/16/1/180

Key established techniques from these reviews:

1. **Power-curve NBM**: P = f(v) estimated via binning, LOESS, SVR, GP regression, neural nets from 10-min SCADA. Residuals tracked with a control chart.
2. **Drivetrain temperature NBM**: predict gearbox/generator oil temperature from power + ambient temperature (Schlechtingen & Santos 2013/2014 — the canonical two-part paper series).
3. **Data cleaning before modeling is essential**: the literature's recommended pipeline is **DBSCAN (remove anomalies) → LOESS (robust power curve) → upper/lower envelope → keep only inliers**. A combination of methods beats any single cleaner.
4. **Documented power-curve anomaly taxonomy** (7 types we can map to causes in our diagnostic layer):
   - Type 1: Lower stacked data (power ≈ 0 above cut-in) → sensor/communication fault
   - Type 2: Down-rating (flat middle band) → curtailment or load-sensor failure
   - Type 3: Wind-speed under-reading (vertical stack) → anemometer fault
   - Type 4: Dispersive data → turbulence/wake/sensor noise
   - Type 5: Cluster shift below curve → blade icing or debris
   - Type 6: Negative power → grid draw at cut-in
   - Type 7: Overrated points above rated power → sensor malfunction

This taxonomy is directly usable: our diagnostic engine can classify the residual/power-curve signature into these 7 types and hand that label to the agent as structured evidence.

5. A Cardiff study shows a hybrid state-space + dynamic correlation approach (rolling 24h Pearson between sensor and power, flag decoupling at ρ<0.3, z-score>3σ, wavelet energy) achieving AUC 0.92 on labeled subsets — a cheap, interpretable statistical layer worth implementing before deep learning: https://orca.cardiff.ac.uk/id/eprint/186460/1/Draft_Sanchez_Pinedo_367888328-5507-document.pdf

6. Vibration residual modeling via SVR (predict nacelle acceleration from power, wind speed, pitch, temperatures) + Mahalanobis distance on residuals achieved AUC 0.95 and MA <2% with FA <10% in a Politecnico di Torino thesis on CARE data — evidence that physics-informed residuals on the CARE dataset work well: https://webthesis.biblio.polito.it/36705/1/tesi.pdf

## 1.3 Solar PV anomaly detection has strong published baselines

- **Statistical degradation + anomaly estimation** (Sensors 2021, AIT Austria): regression models predict expected per-inverter output; anomalies detected from residual statistics. Includes a method that works **without environmental sensors** and one that avoids seasonal decomposition. Directly matches our "expected vs actual" solar twin: https://www.mdpi.com/1424-8220/21/11/3733
- **Unsupervised deep learning on PV power time series** (2025, Applied Energy): an unsupervised model significantly beats One-SVM, Isolation Forest, GMM, LOF, Birch; achieves **recall 92.45%, F1 95.38%** on balanced test and **recall 81.82%, F1 85.71%** on imbalanced test — comparable to supervised XGBoost/MLP/CNN/LSTM. Validates that unsupervised expected-output + residual works for PV even with limited labels: https://www.sciencedirect.com/science/article/pii/S2352467725001511
- **PVDAQ** (NREL): the standard public PV dataset — system metadata + performance time series, multiple systems, some with irradiance/temperature/precipitation; designed for degradation and soiling analysis: https://data.openei.org/submissions/4568

## 1.4 Soiling is a quantified science — with standard metrics and extraction algorithms

Bessa et al. (2021, Progress in Photovoltaics, cited 126+): https://pmc.ncbi.nlm.nih.gov/articles/PMC7960939/

Key takeaways to implement:

1. **Soiling Ratio (SR)** = actual output / expected clean output (IEC 61724-1 standard definition). Soiling loss = 1 − SR. This is our soiling metric.
2. **Soiling rate** = slope of SR profile (%/day), computed over dry periods via least-squares or **Theil–Sen estimator** (robust to outliers and unrecorded cleaning events — Deceglie et al. 2018 recommendation).
3. Compute SR only within **±2h of solar noon** (IEC recommendation) to avoid angle-of-incidence and shading effects.
4. **Sensorless soiling extraction algorithms** — we do NOT need soiling stations:
   - **FRP (Fixed Rate Precipitation, Kimber 2007)**: performance metric + rainfall → single soiling loss profile.
   - **SRR (Stochastic Rate and Recovery, Deceglie 2018)**: needs ONLY the performance metric — no weather data, no cleaning logs. Running median → detect cleanings as positive shifts > Q3+1.5·IQR → Theil–Sen slopes per dry period → Monte Carlo over 1000 candidate profiles → median SR profile. Validated against 11 US soiling stations with lower error than FRP. **This is the algorithm to implement for our "soiling score without soiling sensors" feature.**
5. Cleaning-schedule optimization is published: SARIMAX performance-ratio forecasting achieved R² = 92% for optimizing cleaning timing; empirical models accounting for dust events + rainfall + manual cleaning achieved 0.71% MAE (Energies 2024 review of cleaning optimization: https://www.mdpi.com/1996-1073/17/20/5238).
6. Machine-learned SR prediction from environmental data (PM10, aerosol, MERRA-2) using RF/MLP/LSTM is validated (UGR study, 762 days of data): https://digibug.ugr.es/bitstream/handle/10481/107145/soiling.pdf
7. Solargis's physics soiling model (Coello & Boyle): SR = 1 − 0.3437·erf(0.17·m^0.8473) from deposited particle mass — a physics prior we can use as a feature or sanity check: https://kb.solargis.com/docs/soiling-losses

## 1.5 Time-series anomaly detection: the method menu, benchmarked

The TAB benchmark (PVLDB 2025) evaluates 40 multivariate + 46 univariate TSAD methods across 29 multivariate and 1,635 univariate datasets, with code: https://arxiv.org/html/2506.18046v1 · repo: https://github.com/decisionintelligence/TAB

Practical menu for our platform (ordered by MVP suitability):

| Method | Type | Why for us |
|---|---|---|
| Residual on NBM (regression) | Prediction | Primary. Physics-aligned, interpretable |
| LSTM/GRU Encoder-Decoder (LSTM-ED) | Reconstruction | Proven best baseline on CARE (AE family) |
| Autoencoder / VAE | Reconstruction | Simple, fast, trainable on normal-only data |
| Isolation Forest / LOF | Distance/density | Feature-space backup ONLY, never alone (CARE score 0.14!) |
| Anomaly Transformer | Reconstruction | Association-discrepancy; strong on multivariate |
| DCdetector / CARLA | Contrastive | Self-supervised, good point+subsequence |
| TranAD | Adversarial | Self-conditioning transformer |
| PatchTST / DLinear / NLinear | Prediction | Cheap, surprisingly strong linear/transformer forecasters for residual models |
| Chronos / TimesFM / Moment (pretrained) | Foundation | Zero-shot option for sites with no history |
| GPT4TS / UniTime (LLM-based TS) | Foundation | Research-stage; evaluate, don't depend |

Survey with categorized list + code links: Zamanzadeh Darban et al. (ACM Computing Surveys 2024) — https://github.com/zamanzadeh/ts-anomaly-benchmark

Also: a 2025 study shows **bandpass filtering before AE** improves detection up to 20% — cheap preprocessing win for vibration channels: https://www.mdpi.com/2076-3417/15/11/6254

## 1.6 RUL / degradation prediction: proven architectures we can reuse

Survey (Sensors 2024): https://www.mdpi.com/1424-8220/24/11/3454

- LSTM as sequence-to-one RUL regressor; GRU variants (MDGRU)
- AE-BLSTM hybrids; stacked denoising AE + SVM
- Multi-scale CNN on time-frequency representations (STFT → CNN)
- **LSTM-GAN adversarial framework** (LSTM predicts degradation trajectory; AE discriminator refines it) — solves multi-step prediction error accumulation; tested on bearing run-to-failure + IEEE PHM 2012 PRONOSTIA dataset: https://eprints.whiterose.ac.uk/id/eprint/176599/1/Final%20Accepted%20Manuscript%20-%20A%20Deep%20Adversarial%20Learning%20Prognostics%20Model%20for%20RUL%20Prediction%20of%20Rolling%20Bearing.pdf

For our MVP, we do NOT need full RUL. Degradation trend + risk window (as our report says) using gradient-boosted hazard-style classification or a simple LSTM on residual trajectories is enough; cite RUL literature as the research roadmap.

## 1.7 Case-Based Reasoning (CBR) is the established academic foundation for our "historical failure trajectory memory"

Our "historical failure-trajectory retrieval" feature has a 40-year research lineage. CBR cycle: **Retrieve → Reuse → Revise → Retain**:

- Weighted similarity retrieval: Similarity(N,R) = Σ wᵢ · f(Nᵢ, Rᵢ) with per-attribute weights; k-NN retrieval; normalized Euclidean distance
- Published CBR fault-diagnosis systems achieve 88–96% retrieval/classification accuracy even with sparsely populated case libraries, and improve as cases are retained (Royal Institute of Technology thesis survey): https://www.diva-portal.org/smash/get/diva2:226846/FULLTEXT01.pdf
- A 2026 CBR condition-monitoring study: weighted-similarity CBR reached 89.7% accuracy / 87.5% precision / 91.2% recall for early fault detection; k=5, distance-weighted, Euclidean was optimal (69%→89% after tuning): https://ojs.unimal.ac.id/sisfo/article/view/27001/11058
- Tsai et al. (2009, Proc. IMechE, cited 34): web-based CBR fault diagnosis for industrial machines: https://journals.sagepub.com/doi/10.1243/09544062JMES1588

Modern upgrade over classical CBR: embed each pre-failure trajectory window into a vector (via a self-supervised time-series encoder such as TS2Vec) and retrieve by cosine similarity in a vector DB — this is "CBR with learned similarity." Classical weighted k-NN on engineered features remains the explainable fallback and the right MVP choice.

## 1.8 RAG + LLM for predictive maintenance: the research directly validates our agent layer

This is the most directly transferable research area. Key papers:

1. **LLM-R** (arXiv:2411.04476, 2024): framework for domain-adaptive maintenance scheme generation combining **hierarchical agents and RAG** — cited in the manufacturing GenAI survey (2026): https://www.sciencedirect.com/science/article/pii/S2212827125009643
2. **Intelligent Predictive Maintenance RAG framework for Power Plants** (Hong et al., EMNLP 2024 Industry Track, pp. 805–820): QA over power-plant maintenance with **StyleDFS and domain-specific instruction tuning** — the closest published analog to our system: referenced in https://odr.chalmers.se/bitstreams/5f979de4-1e26-4ba0-8d5d-ffa7fad5b260/download
3. **RAAD-LLM** (arXiv:2503.02800, 2025): adaptive anomaly detection with LLMs + RAG integration
4. **FD-LLM** (arXiv:2412.01218, 2024): encodes vibration time series as tokens/strings for fine-tuned LLM fault classification — evidence LLMs can ingest sensor data when properly encoded (but we keep this research-stage; our design keeps numbers out of the LLM)
5. **Chalmers thesis (2025)**: full LLM+RAG (and KAG) predictive-maintenance assistant built on a Siemens Tecnomatix digital twin; unified knowledge base from sensor data + event logs + manuals; validated with real CNC technicians on 12 troubleshooting scenarios; explicit finding that RAG mitigates hallucination and unsupported claims; also finds KAG (knowledge-graph RAG) gives higher traceability than plain RAG: https://odr.chalmers.se/bitstreams/5f979de4-1e26-4ba0-8d5d-ffa7fad5b260/download
6. **LLM multimodal anomaly detection** (Palma et al. 2025, Electronics, cited 31): LLM as "multimodal integrator" combining structured time series + weather with manuals via prompt engineering + RAG + inference tuning — validates our "environment + telemetry + docs" fusion: https://www.mdpi.com/2079-9292/14/10/2061
7. **Agentic RAG survey** (arXiv:2501.09136, 2025) — for the agent layer design: https://arxiv.org/html/2504.05527v1 (refs)
8. **LLM+RAG real-time PdM with monitoring/reasoning/communication agents** (Univ. of Liverpool, 2025): LSTM monitoring agent → RAG-enabled LLM reasoning core → alert agent; uses synthetic time series + technical docs: https://lab.tt/wp-content/uploads/2025/12/m86293-soechit-paper.pdf

Key design lessons from this literature:
- RAG over manuals/logs demonstrably reduces hallucination — we must cite this when judges ask "why not just an LLM?"
- KAG > plain RAG for traceability (numbered diagnostic trees, component-level links) — supports our Appendix "failure knowledge graph" idea
- Hierarchical agents (monitor → reason → communicate) map 1:1 onto our ML layer → Needle → dashboard design
- LLM should receive **structured/statistical features**, not raw sensor streams (the Chalmers and FD-LLM work both confirm raw-token approaches are fragile)

## 1.9 Knowledge graphs for fault diagnosis (our advanced RAG layer)

- **LLM + domain-ontology constrained KG construction**: prompt engineering + ontology constraints to extract triples from maintenance docs/manuals, with semantic matching + conflict detection, loaded into Neo4j (Springer 2025): https://link.springer.com/10.1007/978-981-95-2748-9_13
- **KG-driven fault diagnosis** (Sensors 2025): top-down ontology + bottom-up data extraction; entities = components, failure modes, symptoms, causes, maintenance strategies; KG continuously updated as failures are resolved: https://www.mdpi.com/1424-8220/25/13/3912
- **FDRKG-LLM** (Xi'an Jiaotong): KG-enhanced LLM fault-diagnostic reasoning pipeline, outperforms retrieval-augmented generation baselines: https://scholar.xjtu.edu.cn/en/publications/a-knowledge-graph-enhanced-large-language-model-based-fault-diagn/
- **Ontology-guided FMEA graph + LLM** (arXiv:2510.15428, 2025): FMEA KGs combined with RAG for retrieving semantically related fault causes with higher reusability than worksheet search: https://arxiv.org/html/2510.15428v1

For the MVP: schema-lite JSON case store + vector retrieval. KG/Neo4j is Phase-2 differentiation (and a strong "future work" slide).

## 1.10 Edge small language models: the enabling tech is real and surveyed

- **Comprehensive SLM survey** (ACM Computing Surveys, 2025): SLMs fine-tuned for domains match/exceed LLMs in specialty; extensive coverage of mobile/edge deployment, quantization (AWQ, PTQ/QAT), KV-cache compression, NPU offload: https://dl.acm.org/doi/10.1145/3768165
- **Demystifying SLMs for Edge Deployment** (ACL 2025 long): benchmarks 68 SLMs + on-device cost; develops mobile SLM evaluation suite: https://aclanthology.org/2025.acl-long.718.pdf
- **Edge-efficient LLM survey** (Computer Science Review, 2025): SLMs, compression, inference optimization, edge frameworks: https://www.sciencedirect.com/science/article/abs/pii/S1574013725000310

Model menu for the local agent (in addition to Needle 2):

| Model | Size | Notes |
|---|---|---|
| **Needle 2 (Cactus Compute)** | 45M / 14MB | Purpose-built tool-calling + structured output; our primary |
| Qwen3 0.6B | 0.6B | thinking/non-thinking modes, 100+ languages |
| Gemma 3 270M | 270M | ultra-compact QA/summarization fallback |
| SmolLM3 3B | 3B | reasoning + tool calls if edge hardware allows |
| Phi-4-mini-instruct | 3.8B | 128K context, strong factual QA |
| Qwen2.5 0.5B–1.5B | — | Apache 2.0, GGUF 4-bit, llama.cpp/Ollama |

Deployment stack: llama.cpp / Ollama / MLC for on-device inference; AWQ or GGUF Q4 quantization; Jetson-class hardware or any x86/ARM box for the gateway.

## 1.11 Embedding models for local RAG: benchmarked, with latency numbers

- **BGE-M3** (BAAI, MIT license): 568M params, 2.27GB, 100+ languages, 8192-token context, dense+sparse+multi-vector retrieval in one model. Best open multilingual production default: https://huggingface.co/BAAI/bge-m3 · toolkit: https://github.com/flagopen/flagembedding
- **multilingual-E5-large**: 31ms median CPU query latency, within 0.003 nDCG of a hosted API model on Italian RAG — preferred when sub-100ms SLAs matter: https://arxiv.org/html/2605.23618v1
- Chunking research: all models saturate at ~32-token chunks; **semantic chunking gives measurable gains at 16 tokens** (+0.075 nDCG for mE5-L); 8-token chunks destroy retrieval: https://arxiv.org/html/2605.23618v1
- Practical 2026 decision matrix: BGE-M3 for multilingual production; bge-small-en (33M) for absolute minimum footprint; hybrid retrieval + reranker recommended (BGE pipeline: dense → bge-reranker-v2-m3): https://futureagi.com/blog/best-embedding-models-2025/

For India-first multilingual (English + Hindi technician notes), BGE-M3 is the right default. For time-series state embeddings (our historical-trajectory memory), use a time-series encoder (TS2Vec) for the vectors and BGE-M3 only for text (manuals/SOPs/case narratives).

---

# PART 2 — DATASETS: THE COMPLETE INVENTORY

## 2.1 Wind SCADA datasets

| Dataset | Turbines | Resolution | Span | Labels | License | Link |
|---|---|---|---|---|---|---|
| **CARE to Compare** ⭐ primary | 36 (3 farms: PT onshore, 2 DE offshore) | 10 min | 1y train + 4–98d prediction per sub-dataset | ✅ event start/end + fault descriptions | CC | https://zenodo.org/records/15846963 |
| **Kelmarsh** | 6 Senvion MM92, 12.3MW, UK | 10 min | 2016–mid 2021 + 2022 update | ✅ event/status logs (no fault labels) | CC-BY-4.0 | https://zenodo.org/records/5841834 |
| **Penmanshiel** | 14 Senvion, UK | 10 min | ~5y | ✅ logs | CC-BY-4.0 | (linked from Kelmarsh Zenodo) |
| **EDP open data** | 4 of 16 turbines, 32MW, Portugal | 10 min | 2016–2017 | ✅ failure logbook + status | CC BY-SA | https://data.mendeley.com/datasets/zjxjnjp3xs |
| WinJi Gearbox Challenge | 5 | 10 min | 3y | ✅ gearbox labels | registration | via WinJi |
| La Haute Borne | 4 Senvion MM82, France | 10 min | 2013–2018 | ❌ | Open License v2 | (Zenodo) |
| Kaggle WT SCADA (T09) | 1 | 10 min | 2017–2020 | ❌ | CC0 | Kaggle |
| Kaggle WT SCADA #2 | 1 | 10 min | 2014–2015 | ✅ fault + status | unknown | Kaggle |
| **Ørsted Anholt / Westermost Rough** | 111 / 35 offshore | 10 min | 2y | application/NDA | restricted | via Ørsted |

Curated index with loader notebooks: https://github.com/sltzgs/OpenWindSCADA
Collection & categorization paper (Wind Energy, 2022): https://onlinelibrary.wiley.com/doi/10.1002/we.2766
IEA Wind Task 43 open data portal index: https://iea-wind.org/task43/task-43-open-data/

**India-specific:** NIWE (National Institute of Wind Energy) Kayathar, Tamil Nadu offshore LiDAR + 120m mast: 10-min data, Dec 2017–Nov 2019, 33GB, direct download — useful for Indian wind-site environmental baselines: https://iea-wind.org/task43/task-43-open-data/

## 2.2 Solar datasets

| Dataset | Content | Link |
|---|---|---|
| **NREL PVDAQ** ⭐ primary | 40+ PV systems, metadata + time series; some with irradiance/temp/wind/precip; degradation + soiling analysis ready | https://data.openei.org/submissions/4568 |
| NREL PVSoiling | soiling station measurements (SR time series) | via openei.org search |
| NREL OEDI | broader energy datasets index | https://data.openei.org |
| Stanford PV fault datasets (various) | labeled PV fault I-V / power data | various on Zenodo |
| UGR soiling dataset (Jaén, Spain) | 762 days daily SR + PM10 + MERRA-2 aerosols | https://digibug.ugr.es/bitstream/handle/10481/107145/soiling.pdf |

## 2.3 Weather & environmental data

| Source | What | Access |
|---|---|---|
| **NASA POWER** | hourly solar + meteorological time series (irradiance, temp, wind, precip, humidity) | free API: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ |
| **CAMS (Copernicus)** | global atmospheric composition forecasts incl. **desert dust**, multi-day horizon | free API: https://ads.atmosphere.copernicus.eu/stac-browser/collections/cams-global-atmospheric-composition-forecasts |
| ERA5 (Copernicus CDS) | reanalysis, hourly, global | free API |
| MERRA-2 (NASA) | aerosol assimilation (PM10 proxies for soiling ML) | free |
| Open-Meteo | free forecast API (no key) — great for hackathon | https://open-meteo.com |

## 2.4 Time-series anomaly detection benchmarks (for method validation)

- **TAB** benchmark: 29 multivariate + 1,635 univariate datasets, unified pipeline, leaderboard: https://github.com/decisionintelligence/TAB
- **TSB-UAD** (VLDB 2022): univariate suite
- SWaT / SMD / SMAP / MSL: standard multivariate sets used in wind SCADA papers

## 2.5 Prognostics run-to-failure datasets (for RUL research track)

- IEEE PHM 2012 PRONOSTIA bearing dataset (standard RUL benchmark)
- NASA IMS bearing run-to-failure
- Both used by the LSTM-GAN RUL paper above

---

# PART 3 — METHOD BLUEPRINT: RESEARCH → IMPLEMENTATION MAPPING

For every component, what to build and which research backs it.

## 3.1 Canonical data schema

Merge all datasets into one schema (from report §4.2). Research grounding: CARE provides per-turbine CSV with status IDs 0–5 (0 normal, 1 derated, 2 idling, 3 service, 4 down/fault, 5 other) — adopt this status taxonomy directly; it handles the "curtailment vs fault" distinction our environment-vs-equipment engine needs.

## 3.2 Solar expected-output twin (digital twin lite)

- **MVP**: Gradient boosting (XGBoost/LightGBM) predicting power from irradiance, module temp, hour, season + peer identity. Residual = actual − expected.
- **Grounding**: Sensors 2021 per-inverter regression anomalies; Applied Energy 2025 unsupervised deep PV (F1 95.4%).
- **Data**: PVDAQ systems with irradiance.
- **Upgrade path**: quantile regression (pinball loss) → prediction intervals; conformal calibration for the confidence display.

## 3.3 Wind NBM layer

- **Power-curve NBM**: clean with DBSCAN→LOESS→envelope; fit GP or GBM P=f(v, ρ, direction); residual control chart with 3σ + persistence rule.
- **Temperature NBM**: GBM predicting gearbox/generator oil temp from power + ambient; thermal residual.
- **Vibration residual**: SVR on (power, wind, pitch, temperatures) → nacelle acceleration residual; Mahalanobis distance across residuals (AUC 0.95 evidence).
- **Grounding**: WES 2023 NBM overview; Energies 2022 power-curve review; Politecnico thesis.

## 3.4 Anomaly detection layer

- **MVP**: LSTM autoencoder on normal-only windows (CARE-best approach), plus statistical z-score/wavelet/correlation layer (Cardiff hybrid).
- **Ensemble v2**: AE + IF + XGB + RF + LSTM hybrid stack (F1 0.959 published).
- **Alarm rule**: CARE event logic — ≥72 consecutive anomalous 10-min points = one alarm event (built-in storm suppression).
- **Metric**: CARE score, never raw accuracy.

## 3.5 Soiling engine

1. Daily performance metric (performance ratio, solar-noon window ±2h).
2. **SRR algorithm** (no sensors, no weather): cleaning detection via Q3+1.5·IQR positive shifts; Theil–Sen slopes; Monte Carlo 1000 profiles → median SR + CI.
3. **SR forecaster**: GBM/MLP/LSTM on SR history + PM10/aerosols + rain + CAMS dust forecast (UGR method).
4. **Cleaning optimizer**: counterfactual cost model — clean now vs wait vs clean-after-dust-event (SARIMAX PR forecasting, R² 0.92 published; empirical dust-event models 0.71% MAE).
5. Rain-as-cleaning: learned post-rain recovery probability (SRR naturally captures this via positive shifts).

## 3.6 Degradation & risk layer

- Trend features: rolling slope, persistence, change-point detection (BOCPD or CUSUM), multi-signal agreement score.
- Risk model: GBM classifier on trajectory features → failure probability + calibrated risk window (Platt/isotonic calibration; report Brier score).
- RUL research track: LSTM-GAN (published architecture) on PRONOSTIA for the "research roadmap" slide.

## 3.7 Historical failure-trajectory memory (case-based retrieval)

- **MVP (explainable)**: engineered trajectory features (residual means/slopes per channel, duration, status mix) → attribute-weighted k-NN (k=5, distance-weighted, Euclidean) over labeled CARE/EDP fault episodes → retrieve top cases with outcomes. (Published: 89–96% retrieval accuracy.)
- **v2**: TS2Vec-style self-supervised window embeddings → cosine retrieval in FAISS/Qdrant; hybrid score = 0.5·learned + 0.5·weighted-kNN for explainability.
- Case schema: report §92 + CBR retain loop (technician feedback closes the loop).

## 3.8 Local agent layer (Needle 2)

- Tool registry: report Appendix C.
- Structured output with confidence gating (Needle 2 native capability).
- Evidence chain: every claim cites tool + timestamp + value + baseline (grounding: Chalmers thesis finding that traceability is the weak point of LLM maintenance assistants; KAG fixes it).

## 3.9 RAG layer

- Text corpus: manuals, SOPs, maintenance records, case narratives.
- Embedding: **BGE-M3** (MIT, multilingual, 8K context) + bge-reranker-v2-m3; chunk semantically ~16–64 tokens with structure awareness (headers/steps preserved); FAISS/Qdrant HNSW index.
- Time-series RAG separate: TS2Vec embeddings in a second vector space — do NOT mix text and telemetry vectors.
- Grounding: LLM-R, EMNLP 2024 power-plant RAG, RAAD-LLM, agentic RAG survey.

## 3.10 Economic engine

- No published "revenue-at-risk" standard — this is our differentiator. Method: expected loss = P(failure in window) × E[energy loss | failure] × tariff + escalation of repair cost; counterfactual scenarios A/B/C (repair now / delay / wait for window). Publish assumptions; sensitivity analysis.

## 3.11 Evaluation protocol (research-grade, judge-proof)

1. **Time-ordered splits** (train < validation < test); **leave-one-turbine-out** and **leave-one-farm-out** tests to prove generalization (domain-shift defense).
2. **CARE score** for wind early detection.
3. **Point-adjusted + event-wise F1** for solar anomaly (and report both — TAB shows metric choice changes rankings).
4. **Calibration**: Brier score, reliability plots for risk outputs.
5. **Business metrics**: lead time (days detected before fault), false alarms per turbine-month, energy loss avoided (vs no-action baseline), revenue protected.
6. **Agent metrics**: tool-selection accuracy, JSON validity, evidence coverage %, hallucination rate (claims without tool citation = auto-fail in eval).
7. Never report accuracy on imbalanced SCADA — judges in this domain will call it out (10M normal vs 1K fault rows).

---

# PART 4 — KNOWN FAILURE MODES FROM THE LITERATURE (design defenses now)

| Failure mode | Evidence | Our defense |
|---|---|---|
| Isolation Forest collapses on real SCADA | CARE benchmark 0.14 < random | AE/residual backbone; IF only in ensemble |
| Domain shift across turbines/farms | CARE (3 farms, different sensor sets 86→957 features); Politecnico negative-R² test results | Global → site → asset hierarchical adaptation; leave-one-farm-out eval |
| Class imbalance makes accuracy meaningless | CARE/TSB literature | CARE score, PR curves, event-wise metrics |
| Raw sensor values in LLM = fragility | FD-LLM/Chalmers | Structured evidence only into agent |
| LLM hallucination in maintenance QA | Chalmers thesis (explicit finding) | RAG with citation, KAG later, confidence gating |
| Unrecorded cleanings corrupt soiling rate | Deceglie 2018 | Theil–Sen + SRR Monte Carlo |
| Curtailment looks like degradation | Power-curve taxonomy Type 2 | Status-ID filter (CARE taxonomy) before residual analysis |
| Data leakage from future | TSB/TAB protocols | Strict temporal splits; feature timestamp audit |
| Concept drift with asset aging | Degradation literature | Age-aware baselines, rolling re-fit |
| Embedding chunk too small kills retrieval | 2026 chunking benchmark | ≥32-token semantic chunks |

---

# PART 5 — OPEN-SOURCE TOOL STACK (final)

```
Ingestion:    pandas · polars · tsfresh (feature extraction) · tsmoothie
Protocols:    pymodbus · asyncua (OPC-UA) · paho-mqtt · Apache NiFi (optional)
Storage:      TimescaleDB/PostgreSQL · DuckDB (hackathon) · Parquet · Redis streams
ML:           scikit-learn · XGBoost/LightGBM · PyTorch · tslearn · stumpy (matrix profile)
TSAD:         LSTM-ED, Anomaly Transformer, DCdetector (official repos via TAB list)
Soiling:      pvlib (solar physics: SR, PR, AOI corrections — the standard library)
              + custom SRR implementation (papers above)
Wind:         OpenOA (NREL operational analysis lib!) · wfdb
Embeddings:   FlagEmbedding (BGE-M3) · sentence-transformers · FAISS · Qdrant
Agent:        Needle 2 (Cactus Compute) · fallback: llama.cpp/Ollama + Qwen3-0.6B-GGUF
Orchestration:LangGraph or plain FastAPI tool router (keep it simple)
Backend:      FastAPI · Pydantic (tool I/O contracts)
Frontend:     React · Plotly/Dash (hackathon-fast) · Grafana (optional fleet view)
Sim:          custom telemetry simulator (report §112-113)
Eval:         CARE score impl · ADRepository/TSB pipelines · scikit-learn metrics
```

Notable finds in the stack:
- **OpenOA** (NREL): open-source operational analysis for wind farms — power curve QC, energy yield, long-term loss analysis. Free, battle-tested, citeable. https://github.com/NREL/OpenOA
- **pvlib** (standard): IEC-compliant SR/PR/POA calculations — use it rather than hand-rolling soiling math: https://pvlib-python.readthedocs.io
- **stumpy**: matrix-profile-based anomaly/discord detection — a strong classical baseline for change-point detection on residuals.

---

# PART 6 — WHAT THIS RESEARCH CHANGES vs. THE ORIGINAL REPORT

1. **Anomaly backbone**: explicit switch from "Isolation Forest first" to "**LSTM-AE on normal data first, IF only in ensemble**" — because the CARE benchmark shows IF alone is worse than random on real wind SCADA. This is a judge-proof, citation-backed design decision.
2. **Evaluation**: adopt the **CARE score** + 72-point event alarm rule verbatim; add leave-one-farm-out tests. This makes our evaluation protocol stronger than most published papers.
3. **Soiling engine**: replace vague "soiling score" with the **SRR algorithm + Theil–Sen + IEC 61724-1 solar-noon SR** — a named, published, sensorless method.
4. **Wind diagnostics**: add the **7-type power-curve anomaly taxonomy** as a classifier output feeding the agent (structured, interpretable).
5. **Status filtering**: adopt CARE status IDs 0–5 so curtailment/derating never generates false degradation alerts.
6. **Case retrieval**: anchor the "historical trajectory memory" feature in **CBR (retrieve-reuse-revise-retain)** literature + k=5 distance-weighted kNN evidence, with TS2Vec embeddings as the v2 upgrade.
7. **RAG layer**: name the exact stack (BGE-M3 + reranker + semantic chunking ≥32 tokens + separate text/telemetry vector spaces) with published latency numbers.
8. **Power-curve cleaning pipeline**: DBSCAN→LOESS→envelope before any NBM training (the literature's consensus preprocessing).
9. **Added OpenOA + pvlib + stumpy + tsfresh** to the stack — production-grade libraries that cut build time dramatically.
10. **Added India-relevant source**: NIWE Kayathar LiDAR/mast data for Indian site baselines.

---

# APPENDIX — MASTER REFERENCE LIST (clickable)

**Datasets**
- CARE to Compare: https://www.mdpi.com/2306-5729/9/12/138 · https://zenodo.org/records/15846963
- Kelmarsh: https://zenodo.org/records/5841834 · curated index: https://github.com/sltzgs/OpenWindSCADA
- EDP: https://data.mendeley.com/datasets/zjxjnjp3xs
- Dataset collection paper: https://onlinelibrary.wiley.com/doi/10.1002/we.2766
- IEA Wind Task 43 open data: https://iea-wind.org/task43/task-43-open-data/
- NREL PVDAQ: https://data.openei.org/submissions/4568
- NASA POWER: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/
- CAMS: https://ads.atmosphere.copernicus.eu/stac-browser/collections/cams-global-atmospheric-composition-forecasts

**Wind anomaly / NBM**
- CARE benchmark + score: https://www.mdpi.com/2306-5729/9/12/138
- Hybrid AE/IF/XGB/RF/LSTM: https://dl.acm.org/doi/full/10.1145/3709021.3737669
- NBM overview (WES 2023): https://wes.copernicus.org/articles/8/893/2023/
- Power curve review: https://www.mdpi.com/1996-1073/16/1/180
- Hybrid state-space detection: https://orca.cardiff.ac.uk/id/eprint/186460/1/Draft_Sanchez_Pinedo_367888328-5507-document.pdf
- Vibration residual + Mahalanobis (CARE): https://webthesis.biblio.polito.it/36705/1/tesi.pdf

**Solar / soiling**
- PV anomaly + degradation (Sensors 2021): https://www.mdpi.com/1424-8220/21/11/3733
- Unsupervised deep PV anomaly (2025): https://www.sciencedirect.com/science/article/pii/S2352467725001511
- Soiling review (Bessa 2021): https://pmc.ncbi.nlm.nih.gov/articles/PMC7960939/
- Soiling imaging ML: https://www.mdpi.com/1996-1073/17/20/5238
- ML SR prediction (UGR): https://digibug.ugr.es/bitstream/handle/10481/107145/soiling.pdf
- Solargis soiling model: https://kb.solargis.com/docs/soiling-losses

**TSAD / RUL**
- TAB benchmark: https://arxiv.org/html/2506.18046v1 · https://github.com/decisionintelligence/TAB
- DL-TSAD survey: https://github.com/zamanzadeh/ts-anomaly-benchmark
- Reconstruction TSAD survey (Springer 2025): https://link.springer.com/article/10.1007/s10462-025-11401-9
- Signal processing + AE: https://www.mdpi.com/2076-3417/15/11/6254
- RUL survey: https://www.mdpi.com/1424-8220/24/11/3454
- LSTM-GAN RUL: https://eprints.whiterose.ac.uk/id/eprint/176599/

**CBR**
- CBR fault diagnosis thesis (KTH): https://www.diva-portal.org/smash/get/diva2:226846/FULLTEXT01.pdf
- CBR condition monitoring (2026): https://ojs.unimal.ac.id/sisfo/article/view/27001/11058
- CBR industrial FDS: https://journals.sagepub.com/doi/10.1243/09544062JMES1588

**LLM/RAG/KG for maintenance**
- GenAI PdM survey: https://www.sciencedirect.com/science/article/pii/S2212827125009643
- Chalmers LLM+RAG thesis: https://odr.chalmers.se/bitstreams/5f979de4-1e26-4ba0-8d5d-ffa7fad5b260/download
- Agentic RAG survey: https://arxiv.org/html/2504.05527v1
- LLM multimodal PdM: https://www.mdpi.com/2079-9292/14/10/2061
- Agent RAG PdM: https://lab.tt/wp-content/uploads/2025/12/m86293-soechit-paper.pdf
- LLM KG construction: https://link.springer.com/10.1007/978-981-95-2748-9_13
- KG fault diagnosis: https://www.mdpi.com/1424-8220/25/13/3912
- FDRKG-LLM: https://scholar.xjtu.edu.cn/en/publications/a-knowledge-graph-enhanced-large-language-model-based-fault-diagn/
- FMEA KG + RAG: https://arxiv.org/html/2510.15428v1

**Edge / SLMs / embeddings**
- SLM survey (ACM CSUR 2025): https://dl.acm.org/doi/10.1145/3768165
- SLM edge deployment (ACL 2025): https://aclanthology.org/2025.acl-long.718.pdf
- Edge LLM survey: https://www.sciencedirect.com/science/article/abs/pii/S1574013725000310
- BGE-M3: https://huggingface.co/BAAI/bge-m3 · https://github.com/flagopen/flagembedding
- Embedding benchmark + chunking: https://arxiv.org/html/2605.23618v1
- Needle 2: https://huggingface.co/Cactus-Compute/needle2

**Libraries**
- OpenOA: https://github.com/NREL/OpenOA
- pvlib: https://pvlib-python.readthedocs.io
- stumpy: https://stumpy.readthedocs.io
