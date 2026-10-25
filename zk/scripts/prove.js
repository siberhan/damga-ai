#!/usr/bin/env node

/**
 * prove.js - Generates Groth16 zk-SNARK proof and public signals, writes JSON files,
 * and prints Solidity verifier calldata.
 *
 * Usage: node prove.js <circuit> <input.json> <outdir>
 * Example: node prove.js emissions_le_limit input.json ./proofs
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as snarkjs from 'snarkjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 3) {
    console.error('Usage: node prove.js <circuit> <input.json> <outdir>');
    console.error('Example: node prove.js emissions_le_limit input.json ./out');
    process.exit(1);
  }

  const circuitArg = args[0].replace(/\.circom$/, '');
  const inputFile = path.resolve(process.cwd(), args[1]);
  const outDir = path.resolve(process.cwd(), args[2]);

  if (!fs.existsSync(inputFile)) {
    console.error(`Error: Input file not found: ${inputFile}`);
    process.exit(1);
  }

  const inputContent = fs.readFileSync(inputFile, 'utf8');
  let inputData;
  try {
    inputData = JSON.parse(inputContent);
  } catch (err) {
    console.error(`Error parsing JSON input: ${err.message}`);
    process.exit(1);
  }

  // Resolve wasm and zkey paths
  let wasmPath = path.resolve(ROOT_DIR, `build/${circuitArg}_js/${circuitArg}.wasm`);
  let zkeyPath = path.resolve(ROOT_DIR, `build/${circuitArg}_final.zkey`);

  // Fallback to checking local build directory if run inside zk/
  if (!fs.existsSync(wasmPath)) {
    wasmPath = path.resolve(process.cwd(), `build/${circuitArg}_js/${circuitArg}.wasm`);
  }
  if (!fs.existsSync(zkeyPath)) {
    zkeyPath = path.resolve(process.cwd(), `build/${circuitArg}_final.zkey`);
  }

  if (!fs.existsSync(wasmPath)) {
    console.error(`Error: WASM file not found at ${wasmPath}. Run scripts/setup.sh first.`);
    process.exit(1);
  }
  if (!fs.existsSync(zkeyPath)) {
    console.error(`Error: zkey file not found at ${zkeyPath}. Run scripts/setup.sh first.`);
    process.exit(1);
  }

  // Generate proof
  let fullProveResult;
  try {
    fullProveResult = await snarkjs.groth16.fullProve(inputData, wasmPath, zkeyPath);
  } catch (err) {
    console.error(`Error generating proof: ${err.message}`);
    process.exit(1);
  }

  const { proof, publicSignals } = fullProveResult;

  // Ensure output directory exists
  fs.mkdirSync(outDir, { recursive: true });

  const proofPath = path.join(outDir, 'proof.json');
  const publicPath = path.join(outDir, 'public.json');

  fs.writeFileSync(proofPath, JSON.stringify(proof, null, 2));
  fs.writeFileSync(publicPath, JSON.stringify(publicSignals, null, 2));

  // Export calldata for Solidity verifier
  const calldata = await snarkjs.groth16.exportSolidityCallData(proof, publicSignals);

  console.log(`Proof written to: ${proofPath}`);
  console.log(`Public signals written to: ${publicPath}`);
  console.log('\n--- Solidity Calldata ---');
  console.log(calldata);
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
