# Damga AI — Backend & Judge Verifier

FastAPI backend, deterministic rules and emissions engine, EIP-712 signer, Groth16 ZK proof generator, and judge verification harness for **Damga AI** (IEEE ClimateChain Global Hackathon 2026).

## Overview & Architecture

The backend implements the end-to-end verification and passport issuance pipeline defined in `spec/SPEC.md`:

```
               [ Uploaded PDFs ]
                       │
               (1. PDF to Text via pypdf)
                       │
               (2. Paragraph Prompt-Injection Screen)
                       │
               (3. Field Extraction: Mistral API / Precomputed)
                       │
               (4. Quote Verification: Verbatim & Number Match)
                       │
               (5. CBAM Direct Emissions & Scrap Share Math)
                       │
               (6. Deterministic Red / Yellow / Missing Rules)
                       │
               (7. Canonical JSON Hashing & EIP-712 AIAttestation Signing)
                       │
    ┌──────────────────┴──────────────────┐
    ▼                                     ▼
[ Offline Local Mode ]           [ Ethereum Sepolia ]
- State JSONs in backend/state/  - submitAttempt()
- Instant demo & testing         - issuePassport() + ZK Proofs
```

## Setup & Installation

System Python 3.15 has no packages by default; use `uv` with Python 3.12:

```bash
cd backend
uv venv --python 3.12
uv pip install -r requirements.txt
```

Pinned dependencies include:
- `fastapi`, `uvicorn[standard]`
- `pydantic`, `pyyaml`, `pypdf`
- `web3`, `eth-account`, `httpx`, `python-multipart`
- `pytest`, `python-dotenv`

## Running the Services

### 1. Start the FastAPI Server

From `backend/`:
```bash
uv run uvicorn damga.api:app --reload --port 8000
```
- API Base URL: `http://localhost:8000/api`
- OpenAPI Swagger Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- Frontend SPA: Automatically serves `web/dist` at `/` when built.

### 2. Run the Judge Verifier (`scripts/verify.py`)

A single standalone script designed for hackathon judges to cryptographically verify any issued passport:

```bash
backend/.venv/bin/python scripts/verify.py --passport 1
```

Verification stages:
1. Loads passport and sealed attempt record
2. Computes SHA-256 for all evidence documents and verifies `docsRoot` Merkle tree (OpenZeppelin sorted pair style)
3. Computes canonical JSON `declarationHash` and EIP-712 `inputHash`
4. Verifies canonical JSON `resultHash` integrity
5. Recovers signers from EIP-712 signatures (`AIAttestation`, `Verification`)
6. Deterministically replays emissions math and rules engine over extracted document values
7. Verifies Groth16 zk-SNARK proofs (`emissions_le_limit` and `scrap_share_ge`)

### 3. Run Pipeline CLI & Precomputation

To run an attempt on any case folder under `data/cases/<case_id>/`:
```bash
backend/.venv/bin/python -m damga.pipeline --case honest-01 --attempt 0
```
Writes signed attempt JSON to `data/precomputed/<case_id>/attempt-0.json`.

### 4. Run Evaluation Harness

Evaluates the AI and rules pipeline against all 42 test cases in `data/cases/` and compares against ground truth:

```bash
backend/.venv/bin/python -m damga.eval
```
Generates confusion matrix and performance statistics in `backend/EVAL.md`.

### 5. Run Unit Tests

```bash
cd backend
.venv/bin/pytest
```

## Environment Variables

Configured in the project root `.env` (never committed):

| Variable | Description | Default / Fallback |
|---|---|---|
| `AI_MODE` | `precomputed` or `live` | `precomputed` (fast, deterministic, no API key needed) |
| `AI_MODEL` | Mistral model identifier | `mistral-small-latest` |
| `MISTRAL_API_KEY` | Mistral API key (required only if `AI_MODE=live`) | Skips cleanly if unset |
| `DAMGA_REGISTRY_ADDRESS` | Sepolia contract address | If unset, runs in full "offline" mode (`tx_hash: null`) |
| `SEPOLIA_RPC_URL` | Ethereum Sepolia RPC URL | `https://ethereum-sepolia-rpc.publicnode.com` |
| `RELAYER_PRIVATE_KEY` | Hex private key paying gas on Sepolia | Used for on-chain submission |
| `AI_SIGNER_PRIVATE_KEY` | EIP-712 signer key for AI attestation | Deterministic demo key fallback |
| `PLANT_SIGNER_PRIVATE_KEY` | EIP-712 signer key for exporter declaration | Deterministic demo key fallback |
| `DEMO_VERIFIER_PRIVATE_KEY` | EIP-712 signer key for accredited verifier | Deterministic demo key fallback |

## How Precomputed Mode Works

For demo reliability, zero latency, and judge reproducibility without requiring third-party API keys:
1. `AI_MODE=precomputed` loads signed AI results from `data/precomputed/<case_id>/attempt-<n>.json`.
2. When judges run `scripts/verify.py` or submit attempts in the UI, all calculations, Merkle roots, rules engine checks, and ZK proofs execute dynamically and deterministically.
3. In `live` mode, the backend calls the Mistral API via plain `httpx` with `response_format={"type": "json_object"}` and temperature 0.

## Zero-Knowledge Proofs

Wraps Circom circuits and Groth16 proofs:
- `emissions_le_limit`: Proves direct emissions (kgCO₂/t) ≤ 150 kg/t matching a Poseidon commitment without disclosing exact plant operational figures.
- `scrap_share_ge`: Proves circular recycled scrap input share ≥ 900‰ (90.0%) matching a Poseidon commitment.
- Calldata exported as `uint256[8]` arrays for smart contract verification.
