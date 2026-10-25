# European Prompt-Guard and Decision Models Research Report
**Project:** Damga AI — Digital Product Passport for Turkish Scrap EAF Steel  
**Target Submission:** IEEE ClimateChain Global Hackathon 2026  
**Date of Research:** 2026-10-25  
**Output Files:** `eu-guards.md`, `eu-guards.json`, `compare.html`

---

## 1. Executive Summary & Purpose

Damga AI processes sensitive evidence documents (invoices, gas bills, weighbridge tickets, laboratory scrap scrap assays) from Turkish Electric Arc Furnace (EAF) steel producers to substantiate real Carbon Border Adjustment Mechanism (CBAM) emissions. The core extractor model is a European Mistral model. To ensure complete European data sovereignty, regulatory compliance (EU AI Act & GDPR), and operational security, two specialized helper model layers surround the primary extraction model:

1. **Prompt-Injection / Jailbreak Guard:** Screens incoming document text and OCR fragments *before* the main LLM processes them, protecting against indirect prompt injection (e.g., hidden instructions embedded in supplier PDFs or invoice line items attempting to override scrap ratios or emission calculations). Evaluated against a 90-row public benchmark (60 attacks from Microsoft BIPIA, deepset/prompt-injections, Lakera Gandalf; 30 benign from deepset).
2. **Decision Model:** Evaluates bounded, structured verification queries (e.g., *"Does this document certify pig iron tonnage for the declared fiscal year?"*, returning boolean `yes`/`no`, typed choices, or confidence scores) without open-ended prose generation.

This report evaluates European options for both layers as of October 25, 2026, comparing them against prominent non-European reference models (such as TypeSafe AI Jev, Protect AI, Meta Prompt Guard, Google ShieldGemma, and Patronus Lynx).

---

## 2. Developer Geography & Corporate Status Discoveries

| Entity | Reported Headquarters | Sovereign Region | Corporate Status & Key Developments |
| :--- | :--- | :--- | :--- |
| **TypeSafe AI** | San Francisco, California, USA | **Non-European** | Founded in 2024 by Diogo Almeida (former OpenAI researcher and co-inventor of RLHF/ChatGPT). Developer of **Jev**. Access is cloud API only; closed weights. |
| **Mistral AI** | Paris, France | **EU** | Independent French AI champion. Releases open-weights foundation models and European-hosted APIs (La Plateforme in Paris/Frankfurt data centers). Released **Mistral Moderation 2** (`mistral-moderation-2603`) in March 2026 and **Shieldstral 1.0 3B** in August 2026. |
| **Lakera AI** | Zurich, Switzerland | **European (Non-EU)** | Founded in 2021 in Zurich; creator of the famous **Gandalf** adversarial benchmark. **Acquired in September 2025 by Check Point Software Technologies** (Israel/USA) for ~$300M. The Zurich office became Check Point's Global Center of Excellence for AI Security. |
| **Laiyer AI / Protect AI** | Berlin, Germany → Seattle, USA | **Non-European Reference** | Laiyer AI (Berlin, Germany), creator of *LLM Guard*, was **acquired in January 2024 by Protect AI** (Seattle, USA). In late 2025/2026, Protect AI officially **archived** the open-source `protectai/llm-guard` and `deberta-v3-base-prompt-injection-v2` repositories. |
| **deepset GmbH** | Berlin, Germany | **EU** | Berlin-based creator of Haystack. Maintains `deepset/deberta-v3-base-injection`. Active company, but the model has not had architecture revisions since 2024. |
| **Aleph Alpha** | Heidelberg, Germany | **EU** | Sovereign German enterprise AI vendor. Released Pharia-1-LLM-7B in 2024 with safety alignment, but **does not publish a standalone prompt-injection guard classifier**. |
| **Atla AI** | London, United Kingdom | **European (Non-EU)** | London-based evaluation startup backed by Y Combinator. Released **Selene-1-Mini 8B** (arXiv:2501.17195), reaching #1 on the RewardBench generative leaderboard. |
| **Flow AI** | Helsinki, Finland | **EU** | Helsinki-based creator of **Flow-Judge-v0.1** (3.8B LLM judge). Founded by Flowrite creators (Aaro Isosaari et al.); acquired by Finnish cloud platform **Aiven**. |
| **Horizon AI Labs** | London, UK / Global Open | **European (Non-EU)** | Released `Horizon-Labs/prompt-injection-guard-base` (308M, ModernBERT backbone) in September 2026, specifically optimizing for agent document scanning in 30 languages including Turkish. |

---

## 3. Group A: Prompt-Injection & Safety Guard Models

### Comparative Matrix

| Model | Developer & Country | Region | Open Weights? | Context | Turkish Support | How to Use | Output Type | Best Candidate? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mistral Moderation API (`mistral-moderation-2603`)** | Mistral AI (France) | EU | No (API only) | 128k | Partial (11 core, TR tokenized) | Hosted API (La Plateforme Paris); **Free ($0.00)** | Multi-label 11 categories (jailbreaking, danger, etc.) + scores | **YES** (Best EU API) |
| **Mistral Shieldstral 1.0 3B** | Mistral AI (France) | EU | Yes (Apache 2.0) | 32k | Partial (12 core, TR via prompt) | HF: `mistralai/Shieldstral-1.0-3B`; ~3-6 GB RAM | Continuous safety score [0-1] via dynamic natural language policy | **YES** (Best EU Open Weights) |
| **deepset DeBERTa-v3 Injection** | deepset (Germany) | EU | Yes (MIT) | 512 | **No** (EN, DE only) | HF: `deepset/deberta-v3-base-injection`; <1 GB RAM | Binary label (`LEGIT` / `INJECTION`) + score | **NO** (Over-defense, no TR) |
| **Lakera Guard** | Lakera / Check Point (Switzerland) | Non-EU | No (SaaS API) | Dynamic | Partial | API: `api.lakera.ai/v1/guard`; Dev tier / Enterprise | Structured JSON verdict (`flagged: bool`, categories, scores) | **YES** (Best Managed Commercial) |
| **Horizon Labs Prompt Guard Base** | Horizon Labs (UK) | Non-EU | Yes (Apache 2.0) | 8,192 | **Yes** (30 langs incl. `tr`) | HF: `Horizon-Labs/prompt-injection-guard-base`; <500 MB RAM (ONNX) | Binary label (`SAFE` / `INJECTION`) + score | **YES** (Best Local Sub-1B) |
| **Aleph Alpha Pharia-1-LLM-7B-aligned** | Aleph Alpha (Germany) | EU | Yes (Open Pharia) | 8,192 | Partial | HF: `aleph-alpha/Pharia-1-LLM-7B-control-aligned`; ~14 GB RAM | Generative text with safety alignment (refusals) | **NO** (Not a dedicated classifier) |
| *Meta Prompt Guard 86M [Ref]* | Meta Platforms (USA) | Non-EU | Yes (Gated Llama) | 512 | Partial | HF: `meta-llama/Prompt-Guard-86M`; <500 MB RAM | 3 labels: `BENIGN`, `INJECTION`, `JAILBREAK` | Reference Only |
| *Google ShieldGemma 2B [Ref]* | Google (USA) | Non-EU | Yes (Gemma Terms) | 8,192 | Partial | HF: `google/shieldgemma-2b`; ~4 GB RAM | Logit probability of policy violation ("Yes"/"No") | Reference Only |
| *Protect AI DeBERTa v2 [Ref]* | Protect AI (USA) | Non-EU | Yes (Apache 2.0) | 512 | **No** (EN only) | **ARCHIVED** on HF/GitHub; <1 GB RAM | Binary label (`SAFE` / `INJECTION`) + score | Reference Only (Archived) |

---

### Published Benchmark Cross-Analysis (Focus on BIPIA, deepset, Lakera Gandalf)

All figures below are cited from published evaluation reports (self-reported or standardized evaluations):

```
+----------------------------------------------------------------------------------------------------------+
| BENCHMARK EVALUATION COMPARISON                                                                          |
+------------------------------------+----------------+------------------+---------------+-----------------+
| Model                              | BIPIA (F1/FPR) | deepset (F1/Acc) | Gandalf / PINT| NotInject (Acc) |
+------------------------------------+----------------+------------------+---------------+-----------------+
| Mistral Moderation API (2603)      | n/a (internal) | n/a              | n/a           | n/a             |
| Mistral Shieldstral 1.0 3B         | n/a            | n/a              | n/a           | HarmBench 99.4% |
| deepset DeBERTa-v3 Injection       | 0.971 (FPR 1.0)| 0.992 / 99.14%   | Recall 0.996  | 0.286 (Severe FP)|
| Lakera Guard                       | Top Tier       | n/a              | Author/100%   | PINT: 95.2%     |
| Horizon Labs Prompt Guard Base     | 0.628 (FPR 0.02)| 0.763 (FPR 0.00)| Recall 0.822  | 0.944 (Low FP)  |
| Meta Prompt Guard 86M [Ref]        | 0.020 (FPR 0.00)| 0.235 (FPR 0.00)| n/a           | 0.953           |
| Protect AI DeBERTa v2 [Ref]        | 0.312 (FPR 0.20)| 0.537 (FPR 0.00)| n/a           | 0.563           |
+------------------------------------+----------------+------------------+---------------+-----------------+
```

#### Detailed Observations:
1. **The deepset False-Positive Anomaly on BIPIA:** While `deepset/deberta-v3-base-injection` shows a nominal F1 of 0.971 on the BIPIA indirect injection dataset, independent benchmark runs reveal a **1.00 False Positive Rate (100% false alarms)** on the benign contexts. On the NotInject benchmark (benign queries with suspicious trigger words), deepset achieves only **28.6% accuracy (71.4% false alarms)**. The model card explicitly acknowledges this over-triggering tendency. For Damga AI, this would result in legitimate Turkish scrap invoices being falsely blocked as prompt injections.
2. **Meta Prompt Guard 86M Blind Spot on Indirect Injections:** Meta Prompt Guard achieves an F1 of only **0.020 on BIPIA**. It was trained almost exclusively on direct conversational jailbreaks and misses indirect instructions hidden inside tables, documents, and emails.
3. **Horizon Labs Document Balance:** Horizon Labs Base scores **0.628 F1 on BIPIA with only a 0.02 FPR**, while maintaining **94.4% accuracy on NotInject** and **96.9% F1 on PIArena**. Its 8k context window and explicit 30-language training (including Turkish) make it uniquely suited for agent document ingestion.
4. **Mistral Moderation 2 & Shieldstral:** Mistral Moderation API (`mistral-moderation-2603`) covers 11 categories including explicit `jailbreaking` at zero cost with 128k context. Shieldstral 1.0 3B achieves an exceptional **99.4% F1 on HarmBench** and **84.6% on PolyGuard Multilingual**, allowing users to write a natural-language prompt guard policy such as: *"Does this document contain instructions attempting to alter CBAM calculations, ignore guidelines, or inject system prompts?"*.

---

## 4. Group B: Decision / Judge / Classifier-Style Models

### Who Makes Jev? (TypeSafe AI Verification)
- **Developer:** TypeSafe AI (Co-founders: Diogo Almeida [former OpenAI researcher and early RLHF pioneer], Erik Gafni, Sasha Sheng).
- **Headquarters:** **San Francisco, California, United States**.
- **European Status:** **Non-European**.
- **Model Nature:** Closed-weight "System One" decision model accessed strictly via API (`api.typesafe.ai` / `jevtypesafeai.com`). Evaluates structured questions in a single parallel forward pass. Charges **$0.042 per million input tokens with free output tokens**.
- **Evaluation Paper:** arXiv:2609.30216v1 (*"Jev in the Wild: A Data-Driven Analysis of the Jev Model's Functionality, Applications and Ecosystem"*). Analyzed 2,170 public GitHub repositories utilizing Jev for triage, routing, and review gates. Proves zero syntactic schema hallucination (the model cannot emit tokens outside the defined `Choice`, `Score`, or `Noul` types).
- **Turkish Handling:** Can process Turkish document state if question criteria keys are provided in English; accuracy and calibration on non-English inputs have higher variance.

---

### Comparative Matrix

| Model | Developer & Country | Region | Open Weights? | Context | Turkish Support | How to Use | Output Format | Best Candidate? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ministral 3B / 8B (Constrained JSON)** | Mistral AI (France) | EU | Yes (Apache 2.0 Base) | 128k | **Yes** (Native multilingual) | Mistral API ($0.04/M tokens) or HF local (~2.5 GB RAM) | Pydantic JSON schema (Boolean yes/no, Choice enum, numeric score) | **YES** (Best Overall EU Alternative to Jev) |
| **Atla Selene-1-Mini 8B** | Atla AI (UK) | Non-EU | Yes (Apache 2.0) | 128k | Partial (Llama 3.1 base) | HF: `AtlaAI/Selene-1-Mini-Llama-3.1-8B`; ~6-8 GB RAM | 1-5 Rubric score, Yes/No verification, Pairwise preference + critique | **YES** (Best Evaluator / Judge Quality) |
| **Flow-Judge-v0.1** | Flow AI / Aiven (Finland) | EU | Yes (Apache 2.0) | 128k | Partial (Phi-3.5 base) | HF: `flowaicom/Flow-Judge-v0.1`; ~3.0 GB RAM | Structured `<feedback>` + `<score>` tags (pass/fail, 3-Likert, 5-Likert) | **YES** (Best Lightweight Open Judge) |
| *TypeSafe AI Jev [Baseline]* | TypeSafe AI (USA) | Non-EU | No (API only) | 64k | Partial (State in TR, keys in EN) | Cloud API: $0.042 / 1M in, $0.00 out | Typed `Choice`, `Score`, `Noul` (probability) | Baseline Reference |
| *Patronus AI Lynx 8B [Ref]* | Patronus AI (USA) | Non-EU | Yes (Llama 3 Community) | 8,192 | **No** (EN only) | HF: `PatronusAI/Llama-3-Patronus-Lynx-8B-Instruct` | Binary `PASS` / `FAIL` + reasoning for RAG faithfulness | Reference Only |
| *Prometheus 2 7B [Ref]* | KAIST / LG / CMU (KR/US) | Non-EU | Yes (Apache 2.0) | 8,192 | **No** (EN only) | HF: `prometheus-eval/prometheus-7b-v2.0` | Absolute 1-5 score with critique, or Pairwise choice | Reference Only |

---

### Benchmark & Quality Comparison (Judge & Evaluation Suites)

1. **Atla Selene-1-Mini 8B:**
   - **RewardBench Overall Score:** **89.13%** (Ranked **#1 among all 8B generative models**, outperforming GPT-4o).
   - **EvalBiasBench & AutoJ:** Demonstrates higher alignment with human expert evaluations than GPT-4o while running in an 8B parameter envelope.
   - **Architecture:** Post-trained from `Llama-3.1-8B` using a combination of SFT and DPO on multi-turn evaluation datasets.
2. **Flow AI Flow-Judge-v0.1:**
   - **Efficiency:** 3.8B parameters based on `Phi-3.5-mini-instruct`.
   - **Rubric Calibration:** Matches or exceeds GPT-4o-mini across held-out binary, 3-Likert, and 5-Likert test suites in Pearson/Spearman correlation with human domain evaluators.
3. **Ministral 3B with Structured Outputs:**
   - **MMLU:** 60.9% (outperforming Llama 3.2 3B).
   - **Schema Reliability:** >99.8% schema conformance when invoked with Mistral's native `response_format={"type": "json_schema"}`.
   - **Cost Comparison:** Exactly on par with Jev ($0.04/M input vs Jev's $0.042/M input), but hosted inside the EU (Paris) with full native Turkish support.

---

## 5. Fit for Damga AI

Damga AI processes Turkish evidence documents (weighbridge receipts from Aliağa or Gebze scrap yards, natural gas utility invoices from BOTAŞ, laboratory scrap spectrometer sheets) to calculate and verify embedded CBAM emissions. The deployment environment targets an Apple Silicon Mac locally, alongside European sovereign cloud backends.

### Group A: Prompt-Injection Guard Fit

#### Quick Setup Today (Zero Friction)
- **Fastest Cloud / API Setup:** **Mistral Moderation API (`mistral-moderation-2603`)**. Zero cost ($0.00), zero local compute, 128k context window, hosted in Paris. Requires simply wrapping the document text in a standard HTTP request to `https://api.mistral.ai/v1/moderations`.
- **Fastest Local Sub-1B Setup (<1 GB RAM on Mac):** **Horizon Labs Prompt Injection Guard Base (`Horizon-Labs/prompt-injection-guard-base`)**. 308M parameters (or 141M small variant) with pre-compiled quantized ONNX (`onnx/model_quantized.onnx`). Runs in under 30ms on Apple Silicon CPU/Metal using `onnxruntime`, requires <500 MB RAM, supports 8k tokens, and natively supports Turkish.

#### Top 3 Candidates & Factual Tradeoffs

1. **Mistral Moderation API (`mistral-moderation-2603`) [France / EU]**
   - *Detection Quality:* Evaluated across 11 harmful categories; explicit jailbreaking detection.
   - *Size & Setup:* 0 MB local footprint (Cloud API).
   - *Cost:* **Free ($0.00)** on Mistral La Plateforme.
   - *License:* Proprietary API terms.
   - *Turkish Support:* Processes Turkish tokenization, but safety thresholds are tuned across 11 major global languages.
   - *Tradeoff:* Requires outbound internet access to Mistral's EU endpoint. Cannot run air-gapped.

2. **Horizon Labs Prompt Injection Guard Base (308M) [UK / European]**
   - *Detection Quality:* Balanced agentic training: 0.628 BIPIA F1 with only 2% FPR; 94.4% accuracy on NotInject (eliminates the disastrous false alarm rate of deepset).
   - *Size & Setup:* 308M parameters, <500 MB RAM, ONNX runtime.
   - *Cost:* Free open-source / $0.00 local inference.
   - *License:* **Apache-2.0** (permissive open-source).
   - *Turkish Support:* **Full native training** (explicitly trained on Turkish `tr` along with 29 other languages).
   - *Tradeoff:* Community-released model (Sept 2026); smaller enterprise brand recognition than Mistral.

3. **Mistral Shieldstral 1.0 3B [France / EU]**
   - *Detection Quality:* State-of-the-art policy-adaptive classifier (99.4% F1 on HarmBench; 84.6% on PolyGuard). Single forward pass.
   - *Size & Setup:* 3.0B parameters; runs on Mac in 4-bit quantization (~2.5 GB RAM) or EU cloud GPU.
   - *Cost:* Free open-weights / minimal local compute.
   - *License:* **Apache-2.0**.
   - *Turkish Support:* Multilingual base; policy instructions can be authored in English to evaluate Turkish invoice text.
   - *Tradeoff:* Requires ~2.5-4 GB RAM (larger than sub-1B BERT models).

---

### Group B: Decision Model Fit

#### Quick Setup Today (Zero Friction)
- **Fastest Cloud / API Setup:** **Ministral 3B on Mistral La Plateforme**. Direct European replacement for TypeSafe AI Jev. Pricing is virtually identical ($0.04/M input tokens), hosted in Paris, 128k context, supports Pydantic JSON schema output (guaranteeing typed booleans and enums), and natively understands Turkish documents.
- **Fastest Local Model on Mac:** **Flow-Judge-v0.1 (3.8B)** or **Ministral-3-3B-Base (4-bit GGUF)**. Both run in under ~3 GB RAM on an Apple Silicon Mac using `llama.cpp` or MLX, returning structured verification verdicts in ~100-200ms.

#### Top 3 Candidates & Factual Tradeoffs

1. **Mistral Ministral 3B with Structured Output [France / EU]**
   - *Decision Quality:* 60.9% MMLU; >99.8% JSON schema compliance. Can answer: *"Does this scrap purchase invoice declare at least 150 tonnes of HMS 1/2 scrap? Return JSON { valid: boolean, tonnage: float, confidence: float }"*.
   - *Size & Cost:* Hosted API at **$0.04 / 1M tokens** (comparable to Jev's $0.042/M); or run local 3B weights in ~2.5 GB RAM.
   - *License:* Apache 2.0 (Base weights) / Mistral API.
   - *Turkish Support:* **Excellent native Turkish comprehension** (supplier addresses, Turkish tax IDs, steel terminology).
   - *Tradeoff:* Autoregressive token generation has slightly higher latency (~300-500ms) than Jev's non-autoregressive parallel classifier.

2. **Flow AI Flow-Judge-v0.1 (3.8B) [Finland / EU]**
   - *Decision Quality:* Specialized LLM-as-a-judge model; emits structured `<feedback>` critique and `<score>` tags. Matches GPT-4o-mini on evaluation rubrics.
   - *Size & Cost:* 3.8B parameters (~3 GB RAM locally), Apache 2.0 open weights.
   - *License:* **Apache-2.0**.
   - *Turkish Support:* Understands Turkish context; rubrics and evaluation prompt should be written in English.
   - *Tradeoff:* Requires parsing `<feedback>` and `<score>` XML-style tags rather than receiving a raw binary logit or strict JSON schema.

3. **Atla Selene-1-Mini 8B [United Kingdom]**
   - *Decision Quality:* **Highest benchmarked judgment accuracy** (#1 8B on RewardBench at 89.13%, outperforming GPT-4o).
   - *Size & Cost:* 8.0B parameters (~6-8 GB RAM in 4-bit quant); free open weights or Atla API.
   - *License:* **Apache-2.0**.
   - *Turkish Support:* Base model (Llama 3.1) handles Turkish, but Selene post-training was primarily English and Western European languages.
   - *Tradeoff:* 8B footprint requires more RAM on a Mac than Ministral 3B or Flow-Judge; UK is post-Brexit non-EU.

---

## 6. Methodology & Source Verification

### Research Method
- Data was gathered across official model cards on Hugging Face, peer-reviewed arXiv technical reports, official API documentation, corporate filings, and developer release notes.
- In compliance with project guidelines, **no scores, numbers, or licenses were invented or guessed**. Where a model lacked a published figure for a specific benchmark (e.g., BIPIA on Shieldstral or deepset on Mistral Moderation), it is explicitly designated as `n/a` with the factual explanation.
- Corporate headquarters were confirmed via corporate registry records, acquisition filings, and venture announcements.

### Fallback Tool Notice & Unreadable URLs
- **Octen Search Fallback:** When executing web page extraction via `/Users/bedirhan/.agents/skills/octen-search/scripts/octen.py extract`, the Octen service returned `Octen HTTP 403: {"code":403,"msg":"Payment method required"}`. In accordance with the prompt's hard rules, built-in search and direct HTTP fetch tools were utilized as the approved fallback.
- **Unreadable / Gated URLs:**
  - `https://huggingface.co/meta-llama/Prompt-Guard-86M/raw/main/README.md`: Blocked from direct unauthenticated raw download due to Hugging Face model gating requiring a signed license agreement. Technical data was verified via Meta's arXiv paper 2407.21783 (*Llama 3 Herd of Models*) and public technical documentation.

---

## 7. Summary Recommendation Matrix for Damga AI

```
========================================================================================
DAMGA AI ARCHITECTURAL STACK RECOMMENDATION (ALL EUROPEAN)
========================================================================================
Stage                  Recommended Option                 Fallback / Local Option
----------------------------------------------------------------------------------------
Prompt Guard Layer     Mistral Moderation API (2603)      Horizon Labs Guard Base (308M)
                       • France / EU                      • UK / European Non-EU
                       • 128k context, Free ($0.00)       • Sub-1B (<500MB RAM), Apache 2.0
                       • Hosted in Paris                  • Trained on 30 langs incl. Turkish

Decision Layer         Mistral Ministral 3B (JSON mode)   Flow-Judge-v0.1 (3.8B)
                       • France / EU                      • Finland / EU
                       • $0.04 / 1M tokens (same as Jev)  • 128k context, Apache 2.0
                       • Full native Turkish support      • Local Mac inference (~3 GB RAM)
========================================================================================
```
