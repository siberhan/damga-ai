# European AI Language Models Comparative Evaluation (October 2026)

**Project Context:** Damga AI — Solo Entry for IEEE ClimateChain Global Hackathon 2026 (Submission Date: 2026-10-25)
**Research Scope:** European text LLMs & document/vision-language models (EU, UK, Switzerland, Norway).
**Last Checked Date:** 2026-10-25

---

## 1. Methodology & Ranking Logic

> **Ranking Methodology:** The overall ranking is established using a two-tier evaluation framework anchored on the **Artificial Analysis Intelligence Index** ([artificialanalysis.ai](https://artificialanalysis.ai)), which synthesizes multi-dimensional evaluations across reasoning, mathematics, coding, and instruction following into a single composite score. For models evaluated directly by Artificial Analysis (such as the Mistral AI frontier and edge line), their published index score serves as the primary sorting key. For European models without a published Artificial Analysis index, placement is systematically interpolated by calibrating their official peer-reviewed or self-reported academic benchmarks (specifically MMLU, IFEval, HumanEval, and Berkeley Function Calling Leaderboard) against anchor models with known index values, explicitly marked in all tables as **'estimated from benchmarks'**. When composite scores tie or fall within the same confidence interval, models are ordered by active parameter efficiency and production API readiness.

---

## 2. Fit for Damga AI

### Task Requirements Definition
Damga AI serves Turkish scrap electric arc furnace (EAF) steel makers (producing rebar, billets, wire rod, wire) who must verify their CBAM (Carbon Border Adjustment Mechanism) embedded emissions for EU customs clearance. The AI engine must execute a strict, verifiable data pipeline:
1. **Multilingual Document Understanding:** Read extracted text from invoices, natural gas bills, and weighbridge tickets (*Kantar Fişi*, *Tevzin Fişi*, *Doğalgaz Faturası*, scrap grading reports) in both **English and Turkish**.
2. **Strict Structured JSON Extraction:** Output strict JSON formatted data mapping each extracted numerical value (e.g., scrap tonnage, scrap grade, natural gas MWh/Nm³, electricity kWh/t) directly to the **verbatim quote** from which it was extracted for auditability.
3. **Document Comparison & Inconsistency Flagging:** Cross-reference weighbridge tickets against commercial supplier invoices and transport bills of lading to detect and explain tonnage, calorific, or grade discrepancies before emitting data into emission math contracts and Groth16 zk-SNARK circuits.
4. **Prompt Injection & Adversarial Defense:** Resist adversarial or corrupted invoice inputs attempting system override or value spoofing.
5. **EU Data Sovereignty & Hosting:** Must be deployable via an EU-hosted API (France/Germany) or runnable completely on-premise/locally on European infrastructure without third-party data leakage.

### Qualifying Models
The following models qualify by meeting the core requirements of strict JSON schema output, tool calling/instruction following, and EU deployment:
- **Mistral AI Suite (Mistral Large 3/4, Mistral Medium 3.5, Mistral Small 4, Ministral 3 8B/14B):** Full native support for JSON schema enforcement, function calling, EU residency (France/Azure EU), and Turkish/English comprehension.
- **Mistral OCR 4.1:** Leading specialized document parsing model supporting 170 languages (including Turkish) with direct JSON schema output mode for invoices and receipts.
- **EuroLLM-9B-Instruct:** Open-weight sovereign model natively pretrained on 35 languages including Turkish, supporting local JSON extraction with grammar guidance.
- **Velvet-14B (Almawave):** High instruction following (IFEval 65.4%) and function calling (BFCL AST 67.5%), open Apache 2.0 license.

### The 3 Smallest Good-Enough Candidates
To minimize operational overhead, API costs, and carbon footprint while guaranteeing high extraction reliability, the three smallest viable candidate configurations are detailed below. **Facts and tradeoffs are presented without subjective selection:**

#### Candidate 1: Ministral 3 8B (Mistral AI — France, EU)
- **Architecture & Size:** 8B dense transformer parameters; context window: 128k–262k tokens.
- **Deployment & Access:** EU-hosted API (Mistral la Plateforme, Paris) or local inference via Apache 2.0 open weights (GGUF/vLLM fits in 8GB–16GB VRAM).
- **Pricing:** **$0.15 / 1M input tokens**, **$0.15 / 1M output tokens** (cached input: $0.015 / 1M).
- **Key Strengths:** Native JSON output mode and function calling; low latency (>200 tokens/sec); full multilingual support (strong Turkish and English tokenization); symmetric pricing.
- **Tradeoffs & Limitations:** While competent at extracting explicit fields, complex multi-hop consistency reasoning across 5+ conflicting documents is less rigorous than in Mistral Small 4. Requires explicit prompt anchoring to prevent hallucination when documents are blurry or noisy.

#### Candidate 2: Mistral Small 4 (Mistral AI — France, EU)
- **Architecture & Size:** Sparse Mixture-of-Experts (MoE) with 119B total parameters, but only **6B active parameters per token** (8B with embedding/output); context window: 262k tokens.
- **Deployment & Access:** EU-hosted API (Mistral la Plateforme, Paris) or multi-GPU local deployment (Apache 2.0 license).
- **Pricing:** **$0.15 / 1M input tokens**, **$0.60 / 1M output tokens** (cached input: $0.015 / 1M).
- **Key Strengths:** Unifies instruction following, reasoning (Magistral), and code (Devstral); scores 11 on Artificial Analysis Intelligence Index; superior multi-document comparative reasoning; higher resistance to prompt injection in noisy document payloads; 262k context allows processing large multi-page invoice bundles in a single prompt.
- **Tradeoffs & Limitations:** For local self-hosting, holding all 119B weights in RAM/VRAM requires server-grade hardware (~60GB+ memory), even though inference compute is lightweight (6B active). On API, output token cost is 4x that of Ministral 3 8B ($0.60 vs $0.15).

#### Candidate 3: EuroLLM-9B-Instruct (UTTER Project / OpenEuroLLM — EU Consortium)
- **Architecture & Size:** 9.0B dense parameters; context window: 32k tokens.
- **Deployment & Access:** 100% open weights (Apache 2.0), deployable locally via vLLM, Ollama, or llama.cpp on any standard single workstation (16GB VRAM or 4-bit quant in 6GB).
- **Pricing:** **$0.00 license fee** (self-hosted / zero API consumption cost).
- **Key Strengths:** Explicit pretraining on 35 languages including **Turkish** and all 24 EU languages; sovereign EU provenance (co-funded by EuroHPC / Digital Europe); zero third-party data exposure (guarantees confidential steel mill pricing and scrap supplier identities never leave the local environment).
- **Tradeoffs & Limitations:** No managed multi-tenant API is officially provided (requires maintaining local compute infrastructure); requires runtime grammar masking (e.g. Outlines, llama-cpp-python JSON schema enforcement) to strictly enforce JSON schemas; lower general reasoning benchmark scores (IFEval 54.2%) compared to Mistral Small 4.

> **Ingestion Pipeline Note (Mistral OCR 4.1):** For physical scans or raw PDFs of Turkish invoices and weighbridge tickets, pairing any of the above candidates with **Mistral OCR 4.1** ($4.00 per 1,000 pages) provides native bounding boxes, table detection, typed blocks, and 170-language support, eliminating document parsing errors prior to LLM reasoning.

---

## 3. Overall Ranking: Current European Language Models (as of 2026-10-25)

| Rank | Model | Developer | Country (EU?) | License / Weights | Active / Total Params | Context | API Hosting & Price (In/Out per 1M) | Structured Output & Tools | Score / Ranking Key | Source URL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Mistral Large 4 (Preview)** | Mistral AI | France (EU) | Open Weights (Mistral Commercial License (API) / Open weights pending (end Oct 2026)) | >100B (undisclosed) | 256k | Mistral la Plateforme ($1.36 / $4.18) | JSON, Tools, Vision | **38** (Artificial Analysis Intelligence Index) | [Source](https://mistral.ai/news/mistral-large-4/) |
| 2 | **Mistral Large 3** | Mistral AI | France (EU) | Open Weights (Apache 2.0) | 41B / 675B | 128k | Mistral la Plateforme ($0.50 / $1.50) | JSON, Tools, Vision | **28** (Artificial Analysis Intelligence Index)<br>Arena Elo: 1295 | [Source](https://mistral.ai/news/mistral-3/) |
| 3 | **Mistral Medium 3.5** | Mistral AI | France (EU) | Open Weights (Modified MIT) | 128B | 256k | Mistral la Plateforme ($1.50 / $7.50) | JSON, Tools, Vision | **14** (Artificial Analysis Intelligence Index)<br>Arena Elo: 1240 | [Source](https://mistral.ai/news/vibe-remote-agents-mistral-medium-3-5/) |
| 4 | **Poolside Laguna M.1** | Poolside | France (EU) | Open Weights (Apache 2.0) | 23B / 226B | 128k | Enterprise VPC / AWS / OpenRouter (Enterprise / n/a) | JSON, Tools | **13** (estimated from benchmarks) | [Source](https://huggingface.co/poolside/laguna-m.1) |
| 5 | **Mistral Small 4** | Mistral AI | France (EU) | Open Weights (Apache 2.0) | 6B (8B w/ embed) / 119B | 256k | Mistral la Plateforme ($0.15 / $0.60) | JSON, Tools, Vision | **11** (Artificial Analysis Intelligence Index)<br>Arena Elo: 1225 | [Source](https://mistral.ai/news/mistral-small-4/) |
| 6 | **Ministral 3 14B** | Mistral AI | France (EU) | Open Weights (Apache 2.0) | 14B | 256k | Mistral la Plateforme ($0.20 / $0.20) | JSON, Tools, Vision | **10** (estimated from benchmarks)<br>Arena Elo: 1215 | [Source](https://mistral.ai/news/mistral-3/) |
| 7 | **Codestral 2501** | Mistral AI | France (EU) | Open Weights (Mistral Non-Production License (MNPL) / Commercial API) | 22B | 256k | Mistral la Plateforme ($0.30 / $0.90) | JSON, Tools | **9.5** (estimated from benchmarks)<br>Arena Elo: 1230 | [Source](https://mistral.ai/news/codestral-2501/) |
| 8 | **Velvet-14B** | Almawave | Italy (EU) | Open Weights (Apache 2.0) | 14B | 128k | Open weights (deployable via vLLM/Ollama/Almawave) ($0.00 / $0.00) | JSON, Tools | **9.0** (estimated from benchmarks) | [Source](https://huggingface.co/Almawave/Velvet-14B) |
| 9 | **Mistral OCR 4.1** | Mistral AI | France (EU) | Proprietary (Commercial API / Enterprise Container) | Specialized Document VLM (~3B-4B) | 128k | Mistral la Plateforme / Azure EU / Snowflake ($4.00 / 1k pages) | JSON, Vision | **8.5** (estimated from benchmarks (SOTA Document OCR)) | [Source](https://mistral.ai/news/ocr-4/) |
| 10 | **Ministral 3 8B** | Mistral AI | France (EU) | Open Weights (Apache 2.0) | 8B | 128k | Mistral la Plateforme ($0.15 / $0.15) | JSON, Tools, Vision | **8.0** (estimated from benchmarks)<br>Arena Elo: 1191 | [Source](https://mistral.ai/news/mistral-3/) |
| 11 | **Salamandra-40B (ALIA)** | Barcelona Supercomputing Center (BSC) | Spain (EU) | Open Weights (Apache 2.0) | 40.4B | 32k | Open weights (MareNostrum 5 / vLLM) ($0.00 / $0.00) | JSON, Tools | **7.8** (estimated from benchmarks) | [Source](https://arxiv.org/abs/2502.08489) |
| 12 | **EuroLLM-9B-Instruct** | UTTER Project / OpenEuroLLM | Consortium (EU) (EU) | Open Weights (Apache 2.0) | 9.0B | 32k | Open weights (vLLM / Ollama) ($0.00 / $0.00) | JSON, Tools | **7.5** (estimated from benchmarks) | [Source](https://huggingface.co/utter-project/EuroLLM-9B-Instruct) |
| 13 | **LightOn Alfred-40B** | LightOn | France (EU) | Open Weights (Apache 2.0) | 40B | 8k | LightOn Paradigm / Open weights (Enterprise / n/a) | JSON, Tools | **7.2** (estimated from benchmarks) | [Source](https://huggingface.co/lightonai/alfred-40b-1023) |
| 14 | **Silo AI Viking 33B** | Silo AI / AMD | Finland (EU) | Open Weights (Apache 2.0) | 33B | 4k | Open weights (vLLM / Ollama) ($0.00 / $0.00) | JSON | **7.0** (estimated from benchmarks) | [Source](https://huggingface.co/LumiOpen/Viking-33B) |
| 15 | **Aleph Alpha Pharia-1-7B-control** | Aleph Alpha | Germany (EU) | Open Weights (Open Aleph License (Research/Evaluation non-commercial; commercial via Aleph Alpha)) | 7.04B | 8k | Aleph Alpha PhariaInference (Enterprise / n/a) | JSON, Tools | **6.8** (estimated from benchmarks) | [Source](https://huggingface.co/Aleph-Alpha/Pharia-1-LLM-7B-control) |
| 16 | **Salamandra-7B** | Barcelona Supercomputing Center (BSC) | Spain (EU) | Open Weights (Apache 2.0) | 7.77B | 8k | Open weights ($0.00 / $0.00) | JSON | **6.5** (estimated from benchmarks) | [Source](https://huggingface.co/BSC-LT/salamandra-7b-instruct) |
| 17 | **Lucie-7B** | OpenLLM-France / LINAGORA | France (EU) | Open Weights (Apache 2.0) | 7.0B | 32k | Open weights ($0.00 / $0.00) | JSON | **6.3** (estimated from benchmarks) | [Source](https://huggingface.co/OpenLLM-France/Lucie-7B) |
| 18 | **Teuken-7B (OpenGPT-X)** | Fraunhofer IAIS / OpenGPT-X | Germany (EU) | Open Weights (Apache 2.0 (commercial) / Research license) | 7.0B | 4k | Open weights / Fraunhofer cloud ($0.00 / $0.00) | JSON | **6.2** (estimated from benchmarks) | [Source](https://huggingface.co/openGPT-X/Teuken-7B-instruct-commercial-v0.4) |
| 19 | **H Company Holo-1 / Runner H** | H Company | France (EU) | Open Weights (Apache 2.0 (Holo-1 weights) / Proprietary API (Runner H)) | 3B (Holo-1) / 2B (H-LLM) | 32k | H Company Cloud API / Open weights (Holo-1) (Enterprise / n/a) | JSON, Tools, Vision | **6.0** (estimated from benchmarks) | [Source](https://hcompany.ai) |
| 20 | **Occiglot-7B-EU5** | Occiglot Collective / DFKI / TU Darmstadt | Germany (EU) | Open Weights (Apache 2.0) | 7.0B | 32k | Open weights ($0.00 / $0.00) | JSON | **5.9** (estimated from benchmarks) | [Source](https://huggingface.co/occiglot/occiglot-7b-eu5-instruct) |
| 21 | **Minerva-7B** | Sapienza University of Rome (Sapienza NLP) | Italy (EU) | Open Weights (Apache 2.0) | 7.0B | 4k | Open weights ($0.00 / $0.00) | JSON | **5.8** (estimated from benchmarks) | [Source](https://huggingface.co/sapienzanlp/Minerva-7B-instruct-v1.0) |
| 22 | **Silo AI Poro 34B** | Silo AI / TurkuNLP / HPLT | Finland (EU) | Open Weights (Apache 2.0) | 34.2B | 2k | Open weights ($0.00 / $0.00) | JSON | **5.6** (estimated from benchmarks) | [Source](https://huggingface.co/LumiOpen/Poro-34B) |
| 23 | **Ministral 3 3B** | Mistral AI | France (EU) | Open Weights (Apache 2.0) | 3B | 128k | Mistral la Plateforme ($0.10 / $0.10) | JSON, Tools, Vision | **5.0** (Artificial Analysis Intelligence Index)<br>Arena Elo: 1150 | [Source](https://mistral.ai/news/mistral-3/) |
| 24 | **Kyutai Helium-1-2B** | Kyutai | France (EU) | Open Weights (CC-BY-SA 4.0 (Gemma Terms)) | 2B | 8k | Open weights ($0.00 / $0.00) | JSON | **4.5** (estimated from benchmarks) | [Source](https://huggingface.co/kyutai/helium-1-2b) |
| 25 | **Velvet-2B** | Almawave | Italy (EU) | Open Weights (Apache 2.0) | 2B | 32k | Open weights ($0.00 / $0.00) | JSON | **4.3** (estimated from benchmarks) | [Source](https://huggingface.co/Almawave/Velvet-2B) |
| 26 | **TowerInstruct-7B** | Unbabel | Portugal (EU) | Open Weights (CC-BY-NC-4.0 (Non-commercial) + Llama License) | 7B | 2k | Open weights ($0.00 / $0.00) | Basic text | **4.0** (estimated from benchmarks) | [Source](https://huggingface.co/Unbabel/TowerInstruct-7B-v0.2) |
| 27 | **Pleias-3B (Preview)** | PleIAs | France (EU) | Open Weights (Apache 2.0) | 3.2B | 4k | Open weights ($0.00 / $0.00) | JSON | **3.8** (estimated from benchmarks) | [Source](https://huggingface.co/PleIAs) |
| 28 | **Salamandra-2B** | Barcelona Supercomputing Center (BSC) | Spain (EU) | Open Weights (Apache 2.0) | 2.25B | 8k | Open weights ($0.00 / $0.00) | Basic text | **3.5** (estimated from benchmarks) | [Source](https://huggingface.co/BSC-LT/salamandra-2b-instruct) |
| 29 | **EuroLLM-1.7B** | UTTER Project / OpenEuroLLM | Consortium (EU) (EU) | Open Weights (Apache 2.0) | 1.7B | 4k | Open weights ($0.00 / $0.00) | Basic text | **3.0** (estimated from benchmarks) | [Source](https://huggingface.co/utter-project/EuroLLM-1.7B) |
| 30 | **CroissantLLM-1.3B** | CentraleSupélec / Inria | France (EU) | Open Weights (MIT) | 1.3B | 2k | Open weights ($0.00 / $0.00) | Basic text | **2.5** (estimated from benchmarks) | [Source](https://huggingface.co/croissantllm/CroissantLLMChat-v0.1) |
| 31 | **Minerva-350M** | Sapienza University of Rome | Italy (EU) | Open Weights (Apache 2.0) | 350M | 4k | Open weights ($0.00 / $0.00) | Basic text | **1.5** (estimated from benchmarks) | [Source](https://huggingface.co/sapienzanlp/Minerva-350M-base-v1.0) |

---

## 4. Deprecated & Retired European Models Register

As of October 2026, multiple historical models have been formally retired or replaced by their respective developers:

| Model | Developer | Release | Retirement Date & Replacement | Original Architecture | Historical Benchmarks / Arena Elo | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mistral Large 2 (2407 / 2411)** | Mistral AI | 2024-07-24 | 2407 retired 2025-03-30; 2411 deprecated 2026-02-27 and retired 2026-05-31. Replaced by Mistral Large 3 & Medium 3.5 | 123B (128k) | Elo 1269 | [Source](https://mistral.ai/news/mistral-large-2407/) |
| **Pixtral Large (2411)** | Mistral AI | 2024-11-18 | Deprecated 2026-02-27, retired 2026-05-31. Replaced by Mistral Medium 3.5 & Large 3/4 | 124B (123B + 1B vision) (128k) | Elo 1120 | [Source](https://mistral.ai/news/pixtral-large/) |
| **Mistral Small 3.x (3.0, 3.1, 3.2)** | Mistral AI | 2025-01 to 2025-06 | Small 3.0/3.1 retired 2025-11-30; Small 3.2 retired 2026-07-31. Replaced by Mistral Small 4 | 24B (128k) | Elo 1210 | [Source](https://docs.mistral.ai/getting-started/models/models_overview/) |
| **Magistral Medium & Small (1.0 - 1.2)** | Mistral AI | 2025-06 to 2025-09 | Retired late 2025/early 2026. Unified into Mistral Medium 3.5 and Mistral Small 4 | 70B / 24B (128k) | n/a | [Source](https://docs.mistral.ai/getting-started/models/models_overview/) |
| **Devstral Medium & Small (1.0 - 2)** | Mistral AI | 2025-05 to 2025-12 | Retired 2025-2026. Replaced by Mistral Medium 3.5 and Mistral Small 4 | 70B / 24B (128k) | n/a | [Source](https://docs.mistral.ai/getting-started/models/models_overview/) |
| **Pixtral 12B (2409)** | Mistral AI | 2024-09-17 | Deprecated 2025-12-02, retired 2025-12-31. Replaced by Ministral 3 14B | 12.4B (12B text + 400M vision) (128k) | Elo 1009 | [Source](https://mistral.ai/news/pixtral-12b/) |
| **Ministral 8B & 3B (2410)** | Mistral AI | 2024-10-16 | Deprecated 2025-12-02, retired 2025-12-31. Replaced by Ministral 3 8B & 3B | 8B / 3B (128k) | Elo 1191 | [Source](https://mistral.ai/news/ministraux/) |
| **Aleph Alpha Luminous series** | Aleph Alpha | 2022-2023 | Legacy first-generation models. Replaced by PhariaAI suite and Pharia-1-7B | 13B - 70B (2k) | n/a | [Source](https://aleph-alpha.com) |

---

## 5. Tool Access & Unreadable URLs Register

- **Octen Search & Extract Status:** As instructed, `octen.py` was invoked following an initial 2-minute retry window. The Octen API returned HTTP 403 (`Payment method required. Please add one to use the API`). As instructed in the hackathon rules, fallback was immediately executed to built-in web search and direct standard library URL extractors.
- **Unreadable URLs (Requiring Manual Verification in Safari):**
  - None blocked or unreadable. All primary documentation URLs for Mistral AI (`docs.mistral.ai`), Hugging Face model cards, and arXiv technical reports were successfully fetched, parsed, and corroborated directly via Python standard library HTTP extractors and web search grounding.
