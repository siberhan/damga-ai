# Damga AI

**A checked, sealed, and complete CBAM file for the verifier, and a QR passport for the EU buyer.**

Damga AI helps Turkish steel makers that melt scrap in electric arc furnaces (EAF) prove their real CBAM emissions. An AI reads the evidence documents and quotes every number it uses. Normal code does the carbon math and the red/yellow checks. Every attempt is sealed on Ethereum Sepolia. A human verifier signs. The smart contract checks the signatures and two zero-knowledge proofs, then issues a Digital Product Passport with a GS1 Digital Link QR code.

- **Track:** Sustainable Supply Chains (digital product passports, recycling traceability). It also covers Carbon Markets & Emissions Transparency.
- **Live contract:** [`DamgaRegistry` on Sepolia](https://sepolia.etherscan.io/address/0x5b6d1E0AEf85b8fddb3D7D637f9981442fe493eb), source verified on Sourcify (exact match).
- **Demo passport:** passport #2. Check it yourself with one command (see [Verify it yourself](#verify-it-yourself)).

> We do not replace the accredited verifier. We give the verifier a checked, sealed, and complete file.

---

## 1. The problem

From 2026, an EU importer of steel pays for CBAM certificates. It can use a plant's **real** emissions only when an accredited verifier has checked them. Without verified data it must use the EU **default value**.

| Fact | Value | Source |
|---|---|---|
| Default value, Türkiye, rebar CN 7214 20 00 (also billets 7207 11 14, wire rod 7213, wire 7217) | 2.310 tCO₂/t, **2.541 in 2026** with the +10% mark-up | Implementing Regulation (EU) 2025/2621, Annex I |
| Route the default assumes | blast furnace (BF/BOF) | same |
| Typical direct emissions of a scrap EAF | about 0.04–0.10 tCO₂/t | IEA via IEEFA, EU JRC |
| Turkish crude steel made in EAFs (2025) | 72.2% of 38.1 Mt | TÇÜD |
| Turkish steel exports to the EU (2025) | 7.9 Mt, 40.7% of exports | ÇİB |
| Accredited CBAM verifiers on 2026-07-31 | none yet | DEKRA |

So a clean scrap EAF plant that cannot prove its numbers is charged as if it were a blast furnace. For one tonne of billets in 2026 (Q3 price €82.32), the gap between the default value and verified data is **about €48 to €97 per tonne**. For a plant that sells 10,000 t a year to the EU, this is about €0.5–1 million a year. Verification is the bottleneck, and verifiers are few.

Damga AI's user is the **export manager of a scrap EAF plant**. Their decision: send the EU buyer verified real values instead of default values. Damga AI makes the verifier's job faster to check and impossible to fake quietly.

## 2. How it works

```
 Exporter (plant)            Damga AI backend                          Sepolia (proof of stake)         Verifier            EU importer / customs
 ─────────────────           ────────────────                          ────────────────────────         ────────            ─────────────────────
 yearly form (EU template)
 + 36 evidence PDFs   ──►  1. PDF → text
                           2. prompt-injection screen (regex + Jev 1.14)
                           3. AI extracts numbers WITH exact quotes (MiMo v2.6 Flash)
                           4. quote check: the number must be in the quoted text
                           5. CODE does the CBAM math + red / yellow / missing rules
                           6. AI result signed (EIP-712: input hash,
                              model hash, ruleset hash, confidence)  ──► submitAttempt()
                                                                         every attempt stored, docs
                                                                         marked used (no reuse)
                                                                                                   ──► sees docs, flags,
                                                                                                       attempt history;
                                                                                                       resolves reds, checks
                                                                                                       yellows, signs EIP-712
                           7. two Groth16 proofs over the sealed data ──► issuePassport()
                                                                         checks 3 signatures, rules,
                                                                         both proofs, latest attempt
                                                                                                                         ──► scans QR (GS1 Digital Link)
                                                                                                                             sees proven claims;
                                                                                                                             importer opens the exact
                                                                                                                             value with a salt
```

### The flag rules

- **Red** (clear cheat or impossible value), only from code. Examples: the form says less gas than the gas bills (`form_vs_docs`), or the metal on the invoices cannot make the steel produced (`material_balance`, yield 0.812–0.963 from BREF Table 8.1). The file still reaches the verifier, but **it cannot be signed** while a red flag is open. It closes when the plant corrects the number (a new attempt) or the verifier writes a reason. Both go on-chain. This matches the EU verification statement, which lists misstatements "found and corrected".
- **Yellow** (unusual but possible), for example electricity per tonne below the BREF range. The exporter explains, the verifier marks it as checked.
- **Missing** evidence, for example 10 of 12 monthly gas bills. A missing document is never treated as zero, so the file cannot be signed.
- **The AI never decides.** AI findings are at most yellow. A text that tries to instruct the AI is removed before the AI reads it and shown as a yellow flag (`injection_screened`).
- **One hard block:** a document changed after sealing changes the Merkle root, so the contract rejects it.

### What the contract enforces

`contracts/src/DamgaRegistry.sol`:
- Only approved model hashes and ruleset hashes are accepted. A changed model or rule file gives a new hash, which the owner must approve first.
- The plant, the AI signer, and the verifier each sign EIP-712 messages. **The AI has no key to mint**: it only signs an attestation.
- Every attempt is stored. A passport can be issued only from the latest attempt, so a cheater cannot quietly retry until a file passes.
- A document hash used for one file cannot be used for another (`DocReused`), so the same invoice cannot count twice.
- One passport per plant, year, and product. A correction makes version 2, which points to version 1. The old passport becomes `SUPERSEDED` and stays on-chain. Status values: `ACTIVE`, `REVOKED`, `DISPUTED`, `SUPERSEDED`.
- Two Groth16 proofs, checked on-chain: "direct emissions ≤ limit" and "scrap share of metal input ≥ X%". Both are proved against Poseidon commitments to the private values.

### Who sees what

| Viewer | Sees |
|---|---|
| Anyone (QR page) | The proven claims "≤ 0.200 tCO₂/t" and "scrap share ≥ 90%", the process route, the verifier, "documents unchanged", the model and ruleset, the number of attempts |
| EU importer | Also the exact direct emissions (needed for its CBAM declaration, Regulation (EU) 2023/956 Art. 6(2)(c)). The exporter gives it a salt, and the page checks the value against the on-chain commitment. A wrong salt is refused. |
| Verifier only | The documents, the exact scrap share, and the input mix (scrap, pig iron, DRI). These show the plant's recipe, so they never appear on the passport. |

Standards: the passport is a **W3C Verifiable Credential 2.0** shape, and the QR code is a **GS1 Digital Link** (`/01/<GTIN>/10/<lot>` redirects to the newest active passport). The form follows the sheets of the European Commission's CBAM communication template for installations.

## 3. Verify it yourself

The judge's check needs **no API key and no private key**. It reads passport #2 from Sepolia and checks it against the public files in this repo.

```bash
cd backend && uv venv --python 3.12 && uv pip install -r requirements.txt && cd ..
cd zk && npm install && cd ..
backend/.venv/bin/python scripts/verify.py --passport 2
```

It checks, and exits with code 0 only when all pass:
1. the passport, attempt, model, and ruleset records on the chain;
2. both zero-knowledge proofs again, with snarkjs and the published verification keys;
3. the evidence PDFs: their hashes rebuild the on-chain Merkle root (`docsRoot`);
4. the three EIP-712 signatures (plant, AI, verifier);
5. the signed AI result: the emission math and the rules are **run again in code** and give the same result hash.

An LLM does not give exactly the same answer every time, so the same result is promised for the code part. The AI output is signed and stored, and the check replays it.

### Run the app

```bash
cd web && npm install && npm run build && cd ..
cd backend && .venv/bin/uvicorn damga.api:app --port 8000
# open http://localhost:8000
```

Copy `.env.example` to `.env`. Without keys the app runs from the signed, precomputed AI results in `data/precomputed/`. To run the AI live, set `OPENROUTER_API_KEY` and `AI_MODE=live`. To write to Sepolia, set the signer keys and `SEPOLIA_RPC_URL`.

Tests: `cd backend && .venv/bin/python -m pytest` (36 tests), `cd contracts && forge test`, `cd web && npm test`.

## 4. What is real and what is not

| Part | Status |
|---|---|
| Smart contract and both Groth16 verifiers on Sepolia | **Real**, deployed and source-verified on Sourcify |
| Passport #2, its 3 attempts, and the superseded passport #1 | **Real** Sepolia transactions |
| EU default values, mark-up, benchmarks, certificate prices | **Real**, official EU sources (section 1) |
| Plant input ranges (kWh, gas, electrodes, lime, yield) | **Real** ranges from the EU Iron & Steel BREF (2013) Table 8.1 |
| AI extraction and injection screen | **Real** model calls (MiMo v2.6 Flash and Jev 1.14 through OpenRouter). The demo shows signed results stored ahead of time. |
| Prompt-injection test texts | **Real** public sets: Microsoft BIPIA, deepset/prompt-injections, Lakera gandalf_ignore_instructions. We wrote no attacks ourselves. |
| Invoices, bills, lab reports (42 cases, 1,550 PDFs) | **Synthetic**, made by `data/generate.py` with the real ranges above |
| "Aliağa Demo Steel Works" and "Demo Verification GmbH" | **Fictional** |
| Verifier signature | Demo key in the backend. A real verifier would sign with its own wallet. |
| Gas | Paid by our relayer, so the plant needs no wallet |

## 5. Measured results

### Detection on the 42 test cases

All 42 cases were run with the live models (MiMo v2.6 Flash + Jev 1.14) on 2026-10-25. The signed results are in `data/precomputed/`, and the full report is `backend/EVAL.md` (`backend/.venv/bin/python -m damga.eval` rebuilds it from the stored results).

| Expected → got | Green | Yellow | Red | Missing |
|---|---|---|---|---|
| **Green** (19) | 19 | 0 | 0 | 0 |
| **Yellow** (2) | 0 | 2 | 0 | 0 |
| **Red** (18) | 0 | 0 | 18 | 0 |
| **Missing** (3) | 0 | 0 | 0 | 3 |

**42 of 42 cases got the right status, and every expected rule fired with no false flags** (`form_vs_docs` 16, `material_balance` 5, `missing_evidence` 3, `sector_range_electricity` 2, `injection_screened` 1). Read this with section 9: the cases are synthetic and the cheats are clear on purpose, so this shows that the pipeline works end to end, not how it does on real, messy documents. During this run, 2 of 32 cases first crashed because the model added text after its JSON. We fixed the parser and ran those 2 again.

### Prompt-injection screen

Held-out set: 45 attack texts and 45 normal texts (30 of them are lines from our own invoices), not used to build the regex.

| Screen | Attacks caught | False alarms |
|---|---|---|
| Regex only | 35.6% | 0% |
| **Jev 1.14 (used)** | **93.3%** | **0%** |

We tested all 19 decision models on OpenRouter (`research/guard-test/`). Jev 1.14 had the best catch rate with no false alarms at a low price. A text that gets through still cannot approve a file: the AI only adds findings, and code decides.

### Cost and time

- AI cost: about **$0.0045 per file** (36 PDFs), measured on OpenRouter. The 34 live runs above cost $0.147 in total.
- Time: 9–33 seconds per file with 8 parallel workers.
- Models: Xiaomi MiMo v2.6 Flash reads the numbers, Jev 1.14 screens the text. We chose small, cheap models because the job is reading and quoting, and the math is done in code. We did not measure energy use. Sepolia is proof of stake.

### Gas (measured on Sepolia)

| Operation | Gas used | Cost on Sepolia (at the 1 gwei we paid) |
|---|---|---|
| `registerFile` (once per plant, year, product) | 353,639 | 0.00035 ETH |
| `submitAttempt` (36 documents, 2 signatures) | about 5,257,000 | 0.0053 ETH |
| `issuePassport` (3 signatures, 2 Groth16 proofs) | 2,358,703 | 0.0024 ETH |
| `revokePassport` (supersede) | 36,969 | 0.00004 ETH |
| **One honest passport (register + 1 attempt + issue)** | **about 7,960,000** | **about 0.008 ETH** |
| Deploy: registry / each verifier | 16,434,307 / about 2,116,000 | one time |

`submitAttempt` is the biggest cost because the contract marks each of the 36 document hashes as used. Gas on Sepolia is higher than Foundry's local estimate (`contracts/GAS.md`, made with fewer documents), mostly because new storage slots cost more on Sepolia. Roadmap: store only the Merkle root and check reuse with a Merkle proof, and move to a low-cost Ethereum L2.

## 6. Architecture (six layers)

| Layer | In Damga AI | On-chain? |
|---|---|---|
| 1. Sources signed at origin | The plant signs its declaration (EIP-712). Evidence PDFs are hashed with SHA-256. | no |
| 2. Off-chain data | PDFs and the form stay with the plant and the verifier. Sector pack `sectors/steel_eaf.yaml` holds ranges, factors, and rules. | no |
| 3. AI with versioned models | Injection screen, extraction with quotes, quote check. The model and guard names are hashed into the model hash. | no |
| 4. Proofs and attestations | Code-only math and rules, signed AI result, verifier signature, two Groth16 proofs (Circom, snarkjs) | hashes only |
| 5. Ledger (commitments only) | `DamgaRegistry` on Sepolia: docs root, result hash, model and ruleset hashes, commitments, attempts, passport status | **yes** |
| 6. Application | FastAPI backend with a relayer that pays gas; React app with exporter, verifier, and passport pages; GS1 Digital Link; `scripts/verify.py` | no |

**Why a blockchain and not a database:** the plant (Türkiye), the verifier, the importer (EU), and customs do not share one trusted operator. A public chain gives all of them the same record of every attempt, and nobody can delete a failed attempt. Customs and buyers in other countries cannot join a private network, so a public chain carries only hashes and proofs.

**New sector = new file.** The CBAM template has the same sheets for cement, aluminium, fertilisers, and hydrogen. Only the inputs change, so a new sector needs a new sector pack (inputs, factors, ranges, rules), not new code.

## 7. Security and data integrity

Written in the risk structure of assets, security criteria, threats, and countermeasures.

**Assets:** the evidence documents (trade secrets: prices, suppliers, recipe), the declared values, the AI result, the signer keys, the passport record.

**Security criteria:** confidentiality of the documents, integrity of the documents and results, a record that cannot be deleted, and only authorised signers.

| Threat | Countermeasure | Limit |
|---|---|---|
| Plant changes a document after sealing | Merkle root on-chain; `verify.py` rebuilds it | none, hard block |
| Plant hides a purchase (pig iron) | `material_balance` red flag from physics (yield range) | ranges are wide; small hiding may pass |
| Plant declares less than its bills | `form_vs_docs` red flag, 2% tolerance | a gap under 2% is not flagged (see section 9) |
| Plant retries until a file passes | every attempt on-chain; passport only from the latest attempt; verifier sees the history | |
| Same invoice used in two files | `DocReused` in the contract | |
| Text in a PDF that instructs the AI | regex + Jev 1.14 screen, removed lines shown to the verifier; AI findings are at most yellow | 93.3% caught on the held-out set |
| AI invents a number | the quoted text must contain the number, or the field is rejected | |
| A changed model or rule file | only approved model and ruleset hashes are accepted | the owner approves them |
| AI key stolen | the AI key can only sign attestations; minting needs the plant and verifier signatures too | |
| Relayer / owner key | one owner key approves models, signers, and verifiers in this demo | roadmap: multisig |
| Exact values leak from the passport | only commitments and ZK claims on-chain; exact value needs the importer salt | in this demo the salt endpoint has no login |

**Privacy, KVKK and GDPR.** Raw documents never go on-chain. But **the AI does not run locally**: to read the documents, the backend sends their text to the model providers through OpenRouter. A real plant must accept this in its contract with Damga AI, or run the same pipeline with a model it hosts itself (the model is one setting, `AI_MODEL`). No personal data is needed in the documents. In this public demo the synthetic evidence is in the repo, so anyone can rebuild the exact values; a real deployment keeps the evidence with the plant and the verifier.

**Crypto-agility.** A passport lives for years. SHA-256 and Poseidon hashes are not broken by known quantum attacks, and the passport format can add a post-quantum signature later. Groth16 needs a one-time setup per circuit; for the hackathon we ran it ourselves (`zk/`), and a real system would use a multi-party ceremony.

## 8. Climate impact

Damga AI does not cut emissions by itself. It fixes a **price signal**. Today a Turkish scrap EAF plant without verified data pays as if it used a blast furnace. With verified data, the CBAM cost follows the real emissions, so low-carbon steel is paid for being low-carbon.

- **Per tonne:** the demo plant's verified direct emissions are 0.143 tCO₂/t against a default of 2.541 tCO₂/t in 2026. The cost gap is about €48–97 per tonne (section 1).
- **Scale:** Turkish steel exports to the EU were 7.9 Mt in 2025, and 72.2% of Turkish crude steel is made in EAFs.
- **Why it matters for the climate:** when verified scrap EAF steel costs less at the EU border, buyers have a reason to choose scrap EAF steel over blast furnace steel, and plants have a reason to raise their scrap share. The scrap share proof on the passport makes recycled input visible to buyers.
- **Against greenwashing:** a low number is not enough. The red flags catch hidden inputs and lowered bills, and every failed attempt stays visible.

## 9. Known limits

- **The cases are synthetic.** No real plant data is used. Plant values follow the BREF ranges, and the EU default values are official.
- **The cheats are clear on purpose,** so a viewer can see the catch in a short demo. The 16 generated honest cases are one plant at different sizes.
- **Form vs. documents has a 2% tolerance.** Honest files also have small gaps (meter rounding, billing periods). With 10,000,000 m³ of gas in the bills, a form with 9,700,000 m³ (3% lower) is red, but 9,850,000 m³ (1.5% lower) is **not flagged**. A 1.5% gas gap hides about 1–2 kg CO₂ per tonne.
- **If the documents are also false, only physics checks remain.** When the same false number is on the form and the documents, only the material balance and the BREF ranges can catch it, and they are wide. This is why a signed human verifier stays in the loop.
- **The site visit stays.** In 2026, the first year of CBAM verification, the verifier must visit the plant (Implementing Regulation (EU) 2025/2546). Damga AI does not remove it.
- **Electricity** is used only as a plausibility check. CBAM does not count it for steel.
- The demo verifier signs with a key in the backend, and one owner key controls approvals.

## 10. Adoption and roadmap

- **Adoption:** the plant uses a web page and needs no wallet (the relayer pays gas). The verifier signs with its own wallet. The importer only scans a QR code.
- **Next:** the plant's own verifier signs from its wallet; Turkish e-Fatura (UBL XML) input; supplier passports for pig iron and DRI linked from the steel passport; more sectors as sector packs; Merkle-proof reuse checks and an L2 to cut gas; a multisig owner; a random second check by an independent verifier.
- **CBAM today, DPP next:** the same passport fields (carbon, scrap share, route) are ready when an EU Digital Product Passport for steel becomes required.

## Repository

| Folder | What |
|---|---|
| `contracts/` | Solidity registry and Groth16 verifiers (Foundry), deployment in `deployments.sepolia.json` |
| `zk/` | Circom circuits, keys, proof scripts |
| `backend/` | FastAPI app, AI pipeline, rules, emissions math, signing, chain calls |
| `web/` | React app: exporter, verifier, passport pages |
| `sectors/steel_eaf.yaml` | Sector pack: inputs, factors, BREF ranges, rules, sources |
| `data/` | Case generator, 42 synthetic cases, signed AI results, injection test set (`data/README.md`) |
| `scripts/verify.py` | Independent check of a passport |
| `research/` | BREF ranges and the guard model tests |
