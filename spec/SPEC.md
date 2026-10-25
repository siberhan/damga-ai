# Damga AI — Build Spec v1

This file is the single source of truth shared by all agents. If your code needs a shape that is
not here, use the closest example in `spec/examples/` and say so in your final report. Do not
invent a different shape.

## 1. Product in one paragraph

A Turkish scrap EAF steel plant (the **exporter**) fills a yearly form shaped like the European
Commission's CBAM communication template and uploads evidence documents (invoices, gas bills,
weighbridge tickets, lab analysis, production records). The **AI** reads each number from each
document with the exact quote it came from. **Code** (not the AI) calculates direct emissions and
runs the red / yellow / missing rules. The documents' hashes and the signed AI result are sealed on
Ethereum Sepolia as an **attempt** (every attempt is kept). The exporter sends the file to its
accredited **verifier**, who sees the documents, the flags, and the attempt history, resolves
flags, and signs (EIP-712). The contract checks every signature and rule, verifies two Groth16 ZK
proofs, and mints a **passport**. The **EU importer / customs** scans a QR code (GS1 Digital Link)
and sees the passport.

Demo actors are fictional: plant **"Aliağa Demo Steel Works (fictional)"** in Aliağa, İzmir;
verifier **"Demo Verification GmbH (fictional)"**. Never use a real company name.

## 2. Repository layout and ownership

Each agent writes ONLY in its own folder(s).

| Path | Owner | What |
|---|---|---|
| `spec/` | coordinator | this spec and examples |
| `contracts/` | contracts agent | Foundry project: Solidity, tests, deploy script |
| `zk/` | zk agent | Circom circuits, snarkjs scripts, Solidity verifiers |
| `backend/` | backend agent | FastAPI app, AI pipeline, rules engine, chain client |
| `sectors/` | data agent | `steel_eaf.yaml` sector pack |
| `data/cases/`, `data/generate.py` | data agent | synthetic demo and test files |
| `data/injection/` | injection agent | public prompt-injection texts |
| `data/precomputed/` | backend agent (by running the pipeline) | signed AI results |
| `web/` | frontend agent | Vite + React + TypeScript UI |
| `scripts/verify.py` | backend agent | one-command judge verifier |
| `research/` | research agents | BREF ranges, EU model comparison |
| `README.md`, `docs/` | coordinator | |

Secrets live only in `.env` at the project root (never committed). Names are fixed:
`SEPOLIA_RPC_URL`, `RELAYER_PRIVATE_KEY`, `AI_SIGNER_PRIVATE_KEY`, `PLANT_SIGNER_PRIVATE_KEY`,
`DEMO_VERIFIER_PRIVATE_KEY`, `ETHERSCAN_API_KEY`, `MISTRAL_API_KEY`, `AI_MODEL`,
`AI_MODE` (`precomputed` | `live`), `DAMGA_REGISTRY_ADDRESS`. `.env.example` lists them empty.

## 3. Units and hashing conventions (everyone must match these exactly)

- Masses in JSON: tonnes as numbers (`812.5`). On-chain and in ZK: integers.
- Emissions on-chain / ZK: **kgCO₂ per tonne of product, integer** (0.085 t/t → `85`).
- Shares on-chain / ZK: **per mille integer** (96.0 % → `960`).
- CN code: 8-digit string in JSON (`"72142000"`), `uint32` on-chain.
- `plantId` = `keccak256(utf8(plant.plant_id))` → `bytes32`.
- `fileKey` = `keccak256(abi.encode(bytes32 plantId, uint16 year, uint32 cnCode))`.
- **Document hash** = SHA-256 of the raw file bytes, as `bytes32` (`0x` + 64 hex).
- **Canonical JSON** = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.
- `declarationHash` = SHA-256 of the canonical JSON of `declaration.json`.
- `resultHash` = SHA-256 of the canonical JSON of the AI result **without** its `signature` field.
- `docsRoot` = Merkle root over the document hashes: leaf = `keccak256(abi.encodePacked(docHash))`,
  leaves sorted ascending, parent = `keccak256(sorted pair)` (OpenZeppelin `MerkleProof` style,
  odd leaf is carried up unchanged). The contract recomputes it from the `docHashes[]` it receives.
- `inputHash` = `keccak256(abi.encode(docsRoot, declarationHash))`.
- `modelHash` = `keccak256(utf8("<provider>:<model name>:<model version>"))`.
- `rulesetHash` = SHA-256 of the raw bytes of `sectors/steel_eaf.yaml`.
- ZK commitments = `Poseidon(value, salt)` exactly as `node zk/scripts/commit.js <value> <salt>` prints.

## 4. Statuses and flags

Attempt status (`uint8` on-chain): `0 GREEN`, `1 YELLOW`, `2 RED`, `3 MISSING`.
Worst level wins: MISSING > RED > YELLOW > GREEN for display, but **MISSING and RED both block signing**.

Flag levels:
- **red**: clear fraud or impossible value. Made **only by code rules**. File still goes to the
  verifier, but cannot be signed while open. Closes by (a) a new corrected attempt, or (b) the
  verifier writes a reason (`resolution`), which goes on-chain as a hash.
- **yellow**: unusual but possible (outside the sector range from the BREF). Exporter must write an
  explanation before sending; verifier must mark each one checked before signing.
- **missing**: required evidence absent (e.g. 10 of 12 monthly gas bills). Blocks green and signing.
  A missing document is never treated as zero.
- The **AI may only add findings** (`source: "ai"`, level at most `yellow`). Red and missing come
  from code (`source: "code"`). A prompt injection can therefore never approve or clear a file.
- **Hard block** (contract revert, not a flag): document hashes at signing differ from the sealed
  attempt (`DocsChanged`), a document hash already used by another file (`DocReused`), a second
  passport for the same file key (`PassportExists`).

Rule ids (sector pack `rules`, implemented in backend `rules.py`):

| id | level | check |
|---|---|---|
| `form_vs_docs` | red | each form input total vs the sum of the same field over its evidence docs; differs by more than the tolerance (default 2 %) |
| `material_balance` | red | (scrap + pig iron + DRI from invoices) × yield must be within the BREF yield range of the crude steel produced |
| `missing_evidence` | missing | every required evidence type is present for every required period (12 monthly gas and electricity bills) |
| `quote_check` | missing | an extracted value whose quote is not found verbatim in the document text is dropped; if that leaves a required field without evidence it becomes missing |
| `sector_range_*` | yellow | each per-tonne ratio (kWh/t, gas/t, electrodes/t, lime/t) vs the BREF range |
| `low_vs_sector` | yellow | direct emissions per tonne below the sector range |
| `injection_screened` | yellow (info) | text removed by the prompt-injection screen; shown to the verifier |

## 5. File formats (examples in `spec/examples/`)

- `declaration.example.json` — the yearly form (exporter input).
- `manifest.example.json` — list of evidence documents of one attempt.
- `extraction.example.json` — AI output for ONE document (fields + exact quotes).
- `ai_result.example.json` — the signed result of one attempt (extractions + totals + emissions + flags).
- `passport_vc.example.json` — the passport as a W3C Verifiable Credential 2.0 shape.
- `api/*.example.json` — API responses the frontend consumes.

A demo case on disk (`data/cases/<case_id>/`):
```
declaration.json
manifest.json
docs/<doc_id>.pdf          # text-based PDFs, generated
truth.json                 # ground truth: {"expected_status": "red", "expected_flags": ["material_balance"], "cheat": "..."}
```

## 6. Emission math (code, backend `emissions.py`)

Mass-balance style, per the CBAM monitoring rules for steel (only direct emissions; electricity is
**not** added, it is only used for range checks):

```
fuel_CO2_t   = Σ fuel_amount × NCV × EF                       (natural gas, other fuels)
carbon_CO2_t = (Σ input_mass × C_content − Σ output_mass × C_content) × 44/12
               (inputs: electrodes, coal/anthracite, pig iron, DRI, scrap, ferro-alloys;
                outputs: steel product, slag)
precursor_t  = Σ purchased precursor tonnes × its embedded emissions (supplier data, else EU default)
direct_kg_per_t = round(1000 × (fuel_CO2_t + carbon_CO2_t + precursor_t) / product_t)
scrap_share_permille = round(1000 × scrap_t / (scrap_t + pig_iron_t + dri_t))
```
All factors (NCV, EF, carbon contents, default precursor values) come from `sectors/steel_eaf.yaml`,
each with its source. Same inputs → same output, every time.

## 7. Smart contract (`contracts/src/DamgaRegistry.sol`)

Solidity ^0.8.24, Foundry, OpenZeppelin (`EIP712`, `ECDSA`, `Ownable`). EIP-712 domain:
`name "DamgaAI"`, `version "1"`, chainId, verifyingContract.

Roles (set by owner): `aiSigners[address]`, `verifiers[address]` (accredited verifiers, with a
name), `plantSigners[bytes32 plantId] = address`, `approvedModels[bytes32 modelHash]`,
`approvedRulesets[bytes32 rulesetHash]`. Anyone may submit transactions (the backend relayer pays
gas, so the plant needs no wallet); authority comes only from the signatures.

Typed structs:
```
PlantDeclaration(bytes32 fileKey,bytes32 docsRoot,bytes32 declarationHash,uint256 nonce)
AIAttestation(bytes32 fileKey,bytes32 inputHash,bytes32 modelHash,bytes32 rulesetHash,bytes32 resultHash,uint8 status,uint16 redCount,uint16 yellowCount,uint16 missingCount,uint16 confidenceBps)
Verification(bytes32 fileKey,uint256 attemptIndex,bytes32 docsRoot,bytes32 resultHash,bytes32 resolutionsHash,uint16 redResolved,uint16 yellowChecked,uint256 emissionsCommitment,uint256 scrapCommitment,uint32 emissionsLimit,uint16 minScrapShare,bytes32 vcHash)
```

Functions:
```
registerFile(bytes32 plantId, uint16 year, uint32 cnCode) returns (bytes32 fileKey)
submitAttempt(bytes32 fileKey, bytes32[] docHashes, bytes32 declarationHash,
              AIAttestation att, bytes plantSig, bytes aiSig) returns (uint256 attemptIndex)
    - recomputes docsRoot from docHashes, checks plant signature (plantSigners[plantId]),
      AI signature (aiSigners), att.inputHash == keccak256(abi.encode(docsRoot, declarationHash)),
      approved model + ruleset, each doc hash not used by another fileKey (DocReused), stores attempt.
issuePassport(bytes32 fileKey, uint256 attemptIndex, bytes32[] docHashes, Verification v,
              bytes verifierSig, uint256[8] emissionsProof, uint256[8] scrapProof)
              returns (uint256 passportId)
    - attempt must be the latest of the file; recomputed docsRoot == sealed docsRoot (DocsChanged);
      v.resultHash == attempt resultHash; verifierSig from a registered verifier;
      status != MISSING; v.redResolved == redCount; v.yellowChecked == yellowCount;
      no ACTIVE passport for fileKey (PassportExists) — a new version is only allowed after
      the previous one was SUPERSEDED via revoke(...,supersede=true);
      both Groth16 proofs verify with public inputs [commitment, limit] / [commitment, minShare];
      stores passport {fileKey, attemptIndex, version, prevPassportId, verifier, docsRoot,
      resultHash, emissionsCommitment, scrapCommitment, emissionsLimit, minScrapShare,
      modelHash, rulesetHash, vcHash, status, issuedAt}.
revokePassport(uint256 passportId, bytes32 reasonHash, bool supersede)   // issuing verifier or owner
disputePassport(uint256 passportId, bytes32 reasonHash)                  // owner (demo: the importer side)
views: getFile, getAttempts(fileKey), getAttempt(fileKey,i), getPassport(id),
       passportOfFile(fileKey), isDocUsed(docHash)
```
Events: `FileRegistered`, `AttemptSubmitted(fileKey, index, status, redCount, yellowCount, missingCount, resultHash)`,
`PassportIssued(passportId, fileKey, attemptIndex, verifier)`, `PassportRevoked`, `PassportDisputed`.
Custom errors: `DocsChanged`, `DocReused`, `PassportExists`, `NotLatestAttempt`, `BadSignature`,
`UnapprovedModel`, `UnapprovedRuleset`, `OpenRedFlags`, `UncheckedYellowFlags`, `MissingEvidence`,
`InvalidProof`, `InputHashMismatch`, `ResultHashMismatch`.

## 8. What the passport shows (two tiers)

- **Public (QR, anyone):** verified by whom and when; status (active / revoked / disputed /
  superseded); "direct emissions ≤ `emissionsLimit`" and "scrap share ≥ `minScrapShare`", both
  ZK-proven; process route; documents unchanged since sealing (hash check); model + ruleset
  version; attempt count. No invoices, prices, or suppliers.
- **Importer (disclosure link with the salt):** only the exact direct emissions (kgCO₂/t), the
  value the importer must enter in its CBAM declaration (Regulation (EU) 2023/956 Art. 6(2)(c)).
  The page checks `Poseidon(value, salt)` against the on-chain emissions commitment.
- **Never shown on any passport view:** the input mix (scrap / pig iron / DRI %) and the exact
  scrap share. They stay in the private file; only the verifier sees them. The public page shows
  the scrap share only as the ZK-proven "≥ minScrapShare" claim.

## 9. Backend API (FastAPI, prefix `/api`, JSON)

```
GET  /api/health
GET  /api/cases                                   demo cases list
POST /api/files                {plant_id, year, cn_code}          -> FileSummary
GET  /api/files                                                  -> FileSummary[]
GET  /api/files/{fileKey}                                        -> FileDetail (attempts, flags, chain refs)
POST /api/files/{fileKey}/attempts   multipart (declaration.json + docs[]) or {case_id}  -> Attempt
POST /api/files/{fileKey}/explanations  {attempt_index, explanations: {flag_id: text}}  -> Attempt
POST /api/files/{fileKey}/send       {attempt_index}               -> {verifier_link}
GET  /api/verifier/queue                                         -> FileSummary[]
POST /api/files/{fileKey}/attempts/{i}/resolutions  {red: {flag_id: reason}, yellow_checked: [flag_id]}
GET  /api/files/{fileKey}/attempts/{i}/typed-data   -> EIP-712 typed data for the verifier to sign
POST /api/files/{fileKey}/attempts/{i}/verify   {signature} or {demo_signer: true} -> {passport_id, tx_hash}
GET  /api/passports/{id}                          -> PassportPublic
GET  /api/passports/{id}/disclose?salt=...        -> PassportImporter
GET  /api/docs/{fileKey}/{i}/{doc_id}             -> the PDF (verifier only)
GET  /01/{gtin}/10/{lot}                          -> redirect to /passport/{id} (GS1 Digital Link)
```
Shapes: `spec/examples/api/`. Every response that touches the chain carries `tx_hash` and an
Etherscan link (`https://sepolia.etherscan.io/tx/<hash>`).

## 10. AI pipeline (backend)

1. PDF → text (`pypdf`).
2. **Injection screen** before the model sees the text: drop paragraphs that try to instruct the
   model (heuristics + optional model classifier). Record what was dropped.
3. **Extraction** with a European model (Mistral API, model from `AI_MODEL`), strict JSON output,
   temperature 0: per document, a list of `{key, value, unit, quote, confidence}` using only the
   field keys listed in the sector pack for that document type.
4. **Quote check** in code: the quote must appear verbatim (after whitespace normalisation) in the
   document text, and the number in the quote must equal the value. Otherwise drop the field.
5. Code: totals, emissions, rules, flags. AI writes one short plain-English explanation per flag.
6. Sign the AI result: `resultHash`, then the EIP-712 `AIAttestation` with `AI_SIGNER_PRIVATE_KEY`.
7. `AI_MODE=precomputed` (default for the demo and judges): results are read from
   `data/precomputed/<case_id>/attempt-<n>.json`, already signed. `live` calls the model.

## 11. Judge verifier (`scripts/verify.py`)

`python3 scripts/verify.py --passport <id>` (no API key; public Sepolia RPC by default):
reads the passport, its attempt, and the events from chain; loads the matching case from
`data/cases/` and the AI result from `data/precomputed/`; recomputes document hashes, docsRoot,
declarationHash, resultHash; recovers all three signers and compares with the on-chain roles;
reruns the emission math and the rules from the extracted values and checks they give the same
totals, flags, and status; verifies both ZK proofs. Prints one PASS/FAIL line per check.

## 12. Frontend (`web/`)

Vite + React + TypeScript, no UI kit needed; clean, calm, readable; mobile-friendly passport page.
Built files go to `web/dist` and FastAPI serves them at `/` (one deploy). Routes:
`/exporter`, `/exporter/files/:fileKey`, `/verifier`, `/verifier/files/:fileKey`,
`/passport/:id`. The verifier signs with MetaMask `eth_signTypedData_v4` when available, else a
clearly labelled "Sign with demo verifier key" button (`demo_signer: true`).

## 13. Sector pack shape (`sectors/steel_eaf.yaml`)

```yaml
id: steel_eaf
version: 1.0.0
name: Scrap EAF steel, long products
cn_codes: ["72071114", "72131000", "72142000", "72171010"]
eu_default_value_t_per_t: 2.310            # Türkiye, Implementing Regulation (EU) 2026/1740 Annex I
markup_2026: 0.10
benchmark_t_per_t: { bf_bof: 1.364, scrap_eaf: 0.066 }   # (EU) 2025/2620
doc_types:                                  # field keys the AI may extract per document type
  gas_bill:          { fields: [natural_gas_m3], periods: monthly, required: true }
  electricity_bill:  { fields: [electricity_mwh], periods: monthly, required: true }
  purchase_invoice:  { fields: [scrap_t, pig_iron_t, dri_t, electrodes_t, carbon_charge_t, lime_t, ferroalloys_t], periods: any, required: true }
  weighbridge:       { fields: [scrap_t, pig_iron_t, dri_t], periods: any, required: false }
  lab_analysis:      { fields: [c_content_scrap, c_content_product, c_content_slag], periods: yearly, required: true }
  production_record: { fields: [crude_steel_t, billet_t, product_t, slag_t], periods: yearly, required: true }
  process_flow:      { fields: [], periods: yearly, required: true }
factors:                                    # every factor has value, unit, source
  natural_gas: { ncv: {value: ..., unit: GJ/1000m3, source: ...}, ef: {value: ..., unit: tCO2/TJ, source: ...} }
  carbon_content: { electrodes: {value: ..., unit: tC/t, source: ...}, carbon_charge: ..., pig_iron: ..., dri: ..., scrap: ..., product: ..., slag: ... }
  precursor_default_t_per_t: { pig_iron: {value: ..., source: ...}, dri: {value: ..., source: ...} }
ranges:                                     # from research/bref-eaf-ranges.json, per tonne of liquid steel unless stated
  yield_liquid_per_metal_input: { min: ..., max: ..., source: ... }
  electricity_kwh_per_t: { min: ..., max: ..., source: ... }
  natural_gas_m3_per_t: { min: ..., max: ..., source: ... }
  electrodes_kg_per_t: { min: ..., max: ..., source: ... }
  lime_kg_per_t: { min: ..., max: ..., source: ... }
  direct_kg_co2_per_t: { min: ..., max: ..., source: ... }
rules:
  form_vs_docs: { level: red, tolerance_pct: 2.0 }
  material_balance: { level: red }
  missing_evidence: { level: missing }
  quote_check: { level: missing }
  sector_range: { level: yellow }
  low_vs_sector: { level: yellow }
  injection_screened: { level: yellow }
```
Field keys above are the only extraction keys. Backend reads this file; changing a number here
changes `rulesetHash`, so bump `version` when you change it.
