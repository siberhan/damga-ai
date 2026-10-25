# Damga AI — Smart Contracts

This directory contains the Solidity smart contracts, Groth16 zero-knowledge verifiers, Foundry test suite, and deployment scripts for **Damga AI**, an end-to-end verifiable audit and digital product passport platform for Turkish scrap EAF steel under the European Union Carbon Border Adjustment Mechanism (CBAM).

## Overview

`DamgaRegistry.sol` is the central cryptographic settlement layer of Damga AI deployed on Ethereum Sepolia. It binds physical supply chain documentation, AI-assisted extraction results, accredited verifier decisions, and ZK proofs into immutable digital passports.

### Core Features

1. **Role-Based Authority via EIP-712 Signatures:**
   - **Plant Signer:** Signs `PlantDeclaration(bytes32 fileKey,bytes32 docsRoot,bytes32 declarationHash,uint256 nonce)`.
   - **AI Signer:** Signs `AIAttestation(bytes32 fileKey,bytes32 inputHash,bytes32 modelHash,bytes32 rulesetHash,bytes32 resultHash,uint8 status,uint16 redCount,uint16 yellowCount,uint16 missingCount,uint16 confidenceBps)`.
   - **Accredited Verifier:** Signs `Verification(bytes32 fileKey,uint256 attemptIndex,bytes32 docsRoot,bytes32 resultHash,bytes32 resolutionsHash,uint16 redResolved,uint16 yellowChecked,uint256 emissionsCommitment,uint256 scrapCommitment,uint32 emissionsLimit,uint16 minScrapShare,bytes32 vcHash)`.
   - Anyone may submit transactions (e.g. backend relayer pays gas); authority originates strictly from cryptographically verified signatures.

2. **Deterministic Document Integrity (Merkle Tree):**
   - Documents are sealed via SHA-256 hashes.
   - `docsRoot` is computed deterministically:
     - Leaf = `keccak256(abi.encodePacked(docHash))`, leaves sorted ascending.
     - Parent = `keccak256(sorted pair)` (OZ `MerkleProof` convention, odd leaf carried up).
     - Verified at every attempt sealing and passport issuance (`DocsChanged` protection).

3. **Anti-Fraud & Rules Enforcement:**
   - **Invoice Reuse Protection (`DocReused`):** No document hash may be submitted across two distinct reporting files.
   - **Red Flag Resolution (`OpenRedFlags`):** If an attempt triggers RED flags, a passport cannot be issued unless every flag has an on-chain verifier resolution (`v.redResolved == redCount`).
   - **Yellow Flag Checks (`UncheckedYellowFlags`):** All yellow flags must be verified before passport minting.
   - **Missing Evidence Block (`MissingEvidence`):** Attempts with status `MISSING` (or `missingCount > 0`) are hard blocked from passport issuance.
   - **Model & Ruleset Version Whitelist (`UnapprovedModel`, `UnapprovedRuleset`):** AI model hash and sector ruleset hash must match on-chain approved governance records.

4. **Groth16 Zero-Knowledge Verification:**
   - Evaluates two Groth16 snarkjs-compatible verifiers directly on-chain:
     - **Emissions Verifier:** Verifies `direct_emissions <= emissions_limit` without disclosing raw supplier fuel invoices.
     - **Scrap Share Verifier:** Verifies `scrap_share >= min_scrap_share` without disclosing exact blend proportions.

5. **Passport Lifecycle & Superseding:**
   - Exactly one `ACTIVE` passport is allowed per `fileKey` (`PassportExists`).
   - If a corrected declaration is needed, the verifier or owner revokes the passport with `supersede = true` (`SUPERSEDED`).
   - The subsequent passport increments `version` and points to `prevPassportId`.
   - Importers or customs authorities can dispute an active passport via owner governance (`DISPUTED`).

---

## Directory Structure

```
contracts/
├── abi/
│   └── DamgaRegistry.json          # Exported ABI consumed by backend & frontend
├── lib/
│   ├── forge-std/                  # Foundry standard testing library
│   └── openzeppelin-contracts/     # OpenZeppelin Contracts v5
├── script/
│   └── Deploy.s.sol                # Deployment and role initialization script
├── src/
│   ├── DamgaRegistry.sol           # Core protocol registry
│   ├── interfaces/
│   │   └── IGroth16Verifier.sol    # Generic Groth16 verifier interface
│   └── verifiers/
│       ├── EmissionsLeLimitVerifier.sol # Snarkjs Groth16 verifier for direct emissions
│       └── ScrapShareGeVerifier.sol     # Snarkjs Groth16 verifier for scrap share
├── test/
│   └── DamgaRegistry.t.sol         # Comprehensive Foundry test suite (18 test scenarios)
├── foundry.toml                    # Foundry configuration
├── GAS.md                          # Gas consumption report
└── README.md                       # This file
```

---

## Prerequisites & Installation

Foundry is required:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

---

## Build

Compile contracts and verifiers:
```bash
forge build
```

Export ABI to `contracts/abi/DamgaRegistry.json`:
```bash
mkdir -p abi && python3 -c '
import json
with open("out/DamgaRegistry.sol/DamgaRegistry.json") as f:
    artifact = json.load(f)
with open("abi/DamgaRegistry.json", "w") as f:
    json.dump(artifact["abi"], f, indent=2)
'
```

---

## Running Tests

Run the full test suite:
```bash
forge test -v
```

Run test suite with detailed gas report:
```bash
forge test --gas-report
```

All 18 unit and integration tests cover:
- Happy path (File registration -> Green attempt submission -> Passport issuance).
- Red flag attempts blocking passport issuance without resolution, and passing with exact resolutions.
- Missing evidence rejection.
- Unchecked yellow flags rejection.
- Document alteration detection (`DocsChanged`).
- Cross-file document reuse rejection (`DocReused`).
- Duplicate active passport rejection (`PassportExists`).
- Stale attempt rejection (`NotLatestAttempt`).
- Signer impersonation and invalid signatures (AI, Plant, Verifier).
- Unapproved model and ruleset rejection.
- Invalid ZK proof rejection (`InvalidProof`).
- Revocation with superseding and version chain linking (`prevPassportId`).
- Revocation without superseding blocking subsequent issuance.
- Governance dispute marking (`DISPUTED`).
- Multi-attempt audit history preservation.
- Deployment and compilation with real snarkjs Groth16 verifiers.

---

## Deployment to Sepolia

To broadcast to Ethereum Sepolia:

```bash
# Load environment variables
source ../.env

# Deploy Groth16 Verifiers, DamgaRegistry, and register roles
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify \
    --etherscan-api-key $ETHERSCAN_API_KEY
```

Environment variables read from root `.env`:
- `SEPOLIA_RPC_URL`: Sepolia RPC endpoint
- `RELAYER_PRIVATE_KEY`: Private key of deployer / relayer
- `PLANT_SIGNER_PRIVATE_KEY` or `PLANT_SIGNER_ADDRESS`: Signer for `TR-ALIAGA-DEMO-001`
- `AI_SIGNER_PRIVATE_KEY` or `AI_SIGNER_ADDRESS`: Accredited AI attestation signer
- `DEMO_VERIFIER_PRIVATE_KEY` or `DEMO_VERIFIER_ADDRESS`: "Demo Verification GmbH (fictional)" signer
- `MODEL_HASH`: Approved Mistral AI model hash
- `RULESET_HASH`: Approved sector ruleset hash (`sectors/steel_eaf.yaml`)

---

## Gas Consumption Report

Measurements taken via `forge test --gas-report`:

| Function | Min Gas | Avg Gas | Median Gas | Max Gas | Calls Measured |
|---|---|---|---|---|---|
| `submitAttempt` | 42,170 | 286,924 | 352,170 | 352,206 | 25 |
| `issuePassport` | 44,310 | 221,538 | 62,783 | 437,119 | 16 |
| `registerFile` | 95,864 | 95,864 | 95,864 | 95,864 | 19 |
| `revokePassport` | 33,648 | 37,233 | 37,233 | 40,819 | 2 |
| `disputePassport` | 24,532 | 32,499 | 32,499 | 40,466 | 2 |
| `computeDocsRoot` | 3,464 | 5,650 | 5,760 | 5,760 | 21 |

Detailed gas analysis and economic comparisons are documented in [GAS.md](GAS.md).
