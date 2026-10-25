#!/usr/bin/env bash
set -euo pipefail

# setup.sh - End-to-end setup script for Damga AI Groth16 zk-SNARK circuits
# 1. Compiles circom circuits
# 2. Runs Groth16 setup using Hermez ptau
# 3. Applies local phase-2 contribution
# 4. Exports verification keys and Solidity verifiers
# 5. Renames Solidity verifier contract names to avoid collisions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ZK_ROOT}"

mkdir -p bin build ptau verifiers

# Check circom binary
CIRCOM_BIN="${ZK_ROOT}/bin/circom"
if [ ! -f "${CIRCOM_BIN}" ]; then
  echo "[*] Downloading circom binary for macOS..."
  curl -sL -o "${CIRCOM_BIN}" "https://github.com/iden3/circom/releases/download/v2.2.3/circom-macos-amd64"
  chmod +x "${CIRCOM_BIN}"
fi

# Check ptau file
PTAU_FILE="${ZK_ROOT}/ptau/powersOfTau28_hez_final_12.ptau"
if [ ! -f "${PTAU_FILE}" ]; then
  echo "[*] Downloading Hermez powersOfTau28_hez_final_12.ptau..."
  curl -L -o "${PTAU_FILE}" "https://circom.info/powersOfTau28_hez_final_12.ptau"
fi

CIRCUITS=("emissions_le_limit" "scrap_share_ge")
VERIFIERS=("EmissionsLeLimitVerifier" "ScrapShareGeVerifier")

for i in "${!CIRCUITS[@]}"; do
  CIRCUIT="${CIRCUITS[$i]}"
  CONTRACT_NAME="${VERIFIERS[$i]}"

  echo "=================================================="
  echo "[*] Processing circuit: ${CIRCUIT}"
  echo "=================================================="

  # 1. Compile circom circuit
  echo "[1/4] Compiling ${CIRCUIT}.circom..."
  "${CIRCOM_BIN}" "circuits/${CIRCUIT}.circom" --r1cs --wasm --sym -o build/

  # 2. Groth16 Setup
  echo "[2/4] Groth16 setup with ptau..."
  npx snarkjs groth16 setup "build/${CIRCUIT}.r1cs" "${PTAU_FILE}" "build/${CIRCUIT}_0000.zkey"

  # 3. Local phase 2 contribution
  echo "[3/4] Contributing local phase-2 randomness..."
  RANDOM_SEED="damga-ai-entropy-${CIRCUIT}-$(date +%s)"
  npx snarkjs zkey contribute "build/${CIRCUIT}_0000.zkey" "build/${CIRCUIT}_final.zkey" \
    --name="Damga AI Local Contributor" -v -e="${RANDOM_SEED}"

  # Clean up intermediate 0000 zkey
  rm -f "build/${CIRCUIT}_0000.zkey"

  # 4. Export verification key and Solidity verifier
  echo "[4/4] Exporting verification key and Solidity verifier..."
  npx snarkjs zkey export verificationkey "build/${CIRCUIT}_final.zkey" "build/${CIRCUIT}_vkey.json"
  npx snarkjs zkey export solidityverifier "build/${CIRCUIT}_final.zkey" "verifiers/${CONTRACT_NAME}.sol"

  # Rename contract Groth16Verifier to avoid contract name collision
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/contract Groth16Verifier/contract ${CONTRACT_NAME}/" "verifiers/${CONTRACT_NAME}.sol"
  else
    sed -i "s/contract Groth16Verifier/contract ${CONTRACT_NAME}/" "verifiers/${CONTRACT_NAME}.sol"
  fi

  echo "[+] Generated: build/${CIRCUIT}_vkey.json"
  echo "[+] Generated: verifiers/${CONTRACT_NAME}.sol (Contract: ${CONTRACT_NAME})"
done

echo "=================================================="
echo "[+] All circuits compiled and verified successfully!"
echo "=================================================="
