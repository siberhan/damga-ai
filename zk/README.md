# Damga AI — Zero-Knowledge Circuits (Circom + snarkjs / Groth16)

Zero-knowledge proof subsystem for **Damga AI**, an AI + blockchain Digital Product Passport for Turkish scrap electric arc furnace (EAF) steel producers (rebar, billets, wire rod, wire) reporting to EU importers under the EU Carbon Border Adjustment Mechanism (CBAM).

Steel mills must prove their real emissions and recycled scrap content without revealing commercially confidential parameters (exact production volumes, proprietary scrap recipes, utility invoices, and margin data) to competitors, buyers, or public explorers.

---

## 1. Circuits Overview

### Circuit 1: `emissions_le_limit.circom`
* **Purpose**: Proves that direct specific greenhouse gas emissions are less than or equal to an agreed limit or EU CBAM benchmark, without revealing the exact emission figure.
* **Units**: Integer kilograms of $\text{CO}_2$ equivalent per tonne of crude steel ($\text{kgCO}_2/\text{t}$).
  * *Example*: $85\text{ kgCO}_2/\text{t}$ ($0.085\text{ tCO}_2/\text{t}$) direct emissions against an EU blast furnace baseline limit of $2310\text{ kgCO}_2/\text{t}$.
* **Private Inputs**:
  * `value`: Integer direct emissions in $\text{kgCO}_2/\text{t}$.
  * `salt`: Cryptographic blinding factor (field element / random scalar).
* **Public Inputs**:
  * `commitment`: Decimal string of `Poseidon(value, salt)`. Sealed in the on-chain passport on Ethereum Sepolia.
  * `limit`: Maximum allowable emissions ceiling in $\text{kgCO}_2/\text{t}$.
* **Constraints**:
  1. $\text{commitment} \equiv \text{Poseidon}(\text{value}, \text{salt})$
  2. $\text{value} \le \text{limit}$ (`LessEqThan(32)`)
  3. Range checks: $\text{value}$ and $\text{limit}$ constrained to 32 bits (`Num2Bits(32)`) to eliminate modular field overflow attacks.

### Circuit 2: `scrap_share_ge.circom`
* **Purpose**: Proves that recycled scrap input share meets or exceeds a minimum circularity threshold (e.g. $\ge 90\%$), proving low-embodied carbon circular steel origin without disclosing supplier scrap percentages.
* **Units**: Per mille ($\text{‰}$, integer $0 \dots 1000$).
  * *Example*: $960\text{ ‰}$ corresponds to $96.0\%$ circular scrap metal input, exceeding a $900\text{ ‰}$ ($90.0\%$) threshold.
* **Private Inputs**:
  * `scrapShare`: Recycled scrap content in per mille ($0 \dots 1000$).
  * `salt`: Cryptographic blinding factor.
* **Public Inputs**:
  * `commitment`: Decimal string of `Poseidon(scrapShare, salt)`. Sealed in the on-chain passport.
  * `minShare`: Minimum required scrap share threshold in per mille ($0 \dots 1000$).
* **Constraints**:
  1. $\text{commitment} \equiv \text{Poseidon}(\text{scrapShare}, \text{salt})$
  2. $\text{scrapShare} \ge \text{minShare}$ (`LessEqThan(32)` applied to `minShare <= scrapShare`)
  3. $\text{scrapShare} \le 1000$ (`LessEqThan(32)`)
  4. Range checks: 32-bit bound enforcement on inputs.

---

## 2. Directory Structure

```text
zk/
├── bin/
│   └── circom                     # Precompiled circom 2 compiler binary
├── circuits/
│   ├── emissions_le_limit.circom  # Emissions <= limit circuit
│   └── scrap_share_ge.circom      # Scrap share >= minShare circuit
├── ptau/
│   └── powersOfTau28_hez_final_12.ptau # Hermez public Powers of Tau (4096 constraints)
├── build/                         # Compiled R1CS, WASM, zkey, and vkey artifacts
│   ├── emissions_le_limit_final.zkey
│   ├── emissions_le_limit_vkey.json
│   ├── scrap_share_ge_final.zkey
│   └── scrap_share_ge_vkey.json
├── scripts/
│   ├── setup.sh                   # Compiles circuits, runs Groth16 setup, exports keys & verifiers
│   ├── commit.js                  # CLI tool: computes Poseidon commitment
│   ├── prove.js                   # CLI tool: generates proof, public signals, and Solidity calldata
│   └── verify.js                  # CLI tool: verifies Groth16 proof
├── verifiers/
│   ├── EmissionsLeLimitVerifier.sol # Standalone Solidity verifier contract
│   └── ScrapShareGeVerifier.sol     # Standalone Solidity verifier contract
├── test/
│   └── run.js                     # Plain Node.js test suite (passing & failing edge cases)
├── .gitignore                     # Ignores node_modules, ptau, intermediates; retains keys & verifiers
├── package.json                   # Dependencies: snarkjs, circomlib, circomlibjs
└── README.md
```

---

## 3. Quick Start & CLI Usage

All commands are executed inside the `zk/` folder.

### 3.1 Install Dependencies
```bash
cd zk
npm install
```

### 3.2 Run Complete Circuit Setup
Compiles the circom circuits, runs Groth16 setup with the Hermez Powers of Tau, contributes local phase-2 entropy, and generates both JSON verification keys and Solidity contracts:
```bash
npm run setup
# or: bash scripts/setup.sh
```

### 3.3 Compute Poseidon Commitment
Computes the exact decimal string commitment for the private value and salt (used in off-chain evidence processing and smart contracts):
```bash
node scripts/commit.js <value> <salt>

# Example (Emissions: 85 kgCO2/t, salt: 123456):
node scripts/commit.js 85 123456
# Output: 10595131917387162678112551071422234631479221246797203425432737482837389974289

# Example (Scrap share: 960 per mille, salt: 654321):
node scripts/commit.js 960 654321
# Output: 11973996415107898864769021902326198536881073411312785769266399140850688990649
```

### 3.4 Generate a Proof & Calldata
Accepts the circuit name, input JSON file, and destination directory. Outputs `proof.json`, `public.json`, and prints the formatted Solidity `calldata`:
```bash
node scripts/prove.js <circuit> <input.json> <outdir>

# Example:
node scripts/prove.js emissions_le_limit sample_input.json ./proof_out
```

### 3.5 Verify a Proof
Verifies a generated proof against the circuit's verification key:
```bash
node scripts/verify.js <circuit_name_or_vkey.json> <proof.json> <public.json>

# Example:
node scripts/verify.js emissions_le_limit ./proof_out/proof.json ./proof_out/public.json
# Output: PASS: Proof verified successfully!
```

### 3.6 Run Test Suite
Runs automated tests including positive proofs, constraint rejections (values above ceiling / below floor), salt mismatches, and on-chain signal tampering:
```bash
npm test
# or: node test/run.js
```

---

## 4. Solidity Verifier Integration

The verifier contracts are exported to `verifiers/`:
* `verifiers/EmissionsLeLimitVerifier.sol`: Contract `EmissionsLeLimitVerifier`
* `verifiers/ScrapShareGeVerifier.sol`: Contract `ScrapShareGeVerifier`

Both contracts implement the standard Groth16 verification function:
```solidity
function verifyProof(
    uint[2] memory a,
    uint[2][2] memory b,
    uint[2] memory c,
    uint[2] memory input
) public view returns (bool r)
```

The `input` array corresponds directly to `[commitment, limit]` or `[commitment, minShare]`. The `prove.js` script automatically generates the ABI-encoded parameters ready for `eth_call` or smart contract invocations.

---

## 5. Security & Trusted Setup Disclosure

> [!NOTE]
> **Hackathon Trusted Setup Note**:
> For the Phase 1 multi-party computation, we utilized the battle-tested, publicly verified Hermez `powersOfTau28_hez_final_12.ptau` ceremony (supporting up to 4,096 constraints; our circuits utilize 340 and 373 constraints respectively).
>
> Phase 2 (circuit-specific toxic waste reduction) was conducted locally by the Damga AI team via `snarkjs zkey contribute` using machine-generated system entropy. This setup is fully secure and sufficient for hackathon judging and testnet deployments (Ethereum Sepolia). Before deploying to mainnet or high-value cross-border compliance environments, a publicly participated, multi-contributor Phase 2 ceremony should be held.
