#!/usr/bin/env node

/**
 * verify.js - Verifies a Groth16 zk-SNARK proof using verification key and public signals.
 *
 * Usage:
 *   node verify.js <circuit_or_vkey.json> <proof.json> <public.json>
 *
 * Example:
 *   node verify.js emissions_le_limit out/proof.json out/public.json
 *   node verify.js build/emissions_le_limit_vkey.json out/proof.json out/public.json
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
    console.error('Usage: node verify.js <circuit_name_or_vkey.json> <proof.json> <public.json>');
    console.error('Example: node verify.js emissions_le_limit ./out/proof.json ./out/public.json');
    process.exit(1);
  }

  const vkeyOrCircuit = args[0];
  const proofFile = path.resolve(process.cwd(), args[1]);
  const publicFile = path.resolve(process.cwd(), args[2]);

  let vkeyPath;
  if (vkeyOrCircuit.endsWith('.json')) {
    vkeyPath = path.resolve(process.cwd(), vkeyOrCircuit);
  } else {
    const circuitName = vkeyOrCircuit.replace(/\.circom$/, '');
    vkeyPath = path.resolve(ROOT_DIR, `build/${circuitName}_vkey.json`);
    if (!fs.existsSync(vkeyPath)) {
      vkeyPath = path.resolve(process.cwd(), `build/${circuitName}_vkey.json`);
    }
  }

  if (!fs.existsSync(vkeyPath)) {
    console.error(`Error: Verification key not found at ${vkeyPath}`);
    process.exit(1);
  }
  if (!fs.existsSync(proofFile)) {
    console.error(`Error: Proof file not found at ${proofFile}`);
    process.exit(1);
  }
  if (!fs.existsSync(publicFile)) {
    console.error(`Error: Public signals file not found at ${publicFile}`);
    process.exit(1);
  }

  const vkey = JSON.parse(fs.readFileSync(vkeyPath, 'utf8'));
  const proof = JSON.parse(fs.readFileSync(proofFile, 'utf8'));
  const publicSignals = JSON.parse(fs.readFileSync(publicFile, 'utf8'));

  const isValid = await snarkjs.groth16.verify(vkey, publicSignals, proof);

  if (isValid) {
    console.log('PASS: Proof verified successfully!');
    process.exit(0);
  } else {
    console.error('FAIL: Invalid proof verification!');
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(`Error during verification: ${err.message}`);
  process.exit(1);
});
