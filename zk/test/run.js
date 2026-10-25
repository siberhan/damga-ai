#!/usr/bin/env node

/**
 * run.js - Automated tests for Damga AI zero-knowledge circuits
 *
 * Tests both circuits:
 * 1. EmissionsLeLimit (direct emissions <= limit)
 *    - Passing case: value=85 <= limit=2310
 *    - Failing case 1: value=2400 > limit=2310 (proof generation fails)
 *    - Failing case 2: invalid salt/commitment mismatch (proof generation fails)
 *    - Verification rejection: tampered public signals rejected by verifier
 *
 * 2. ScrapShareGe (scrap share >= minShare && scrapShare <= 1000)
 *    - Passing case: scrapShare=960 >= minShare=900
 *    - Failing case 1: scrapShare=850 < minShare=900 (proof generation fails)
 *    - Failing case 2: scrapShare=1050 > 1000 (proof generation fails)
 *    - Failing case 3: invalid salt/commitment mismatch (proof generation fails)
 *    - Verification rejection: tampered public signals rejected by verifier
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as snarkjs from 'snarkjs';
import { buildPoseidon } from 'circomlibjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ZK_ROOT = path.resolve(__dirname, '..');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function report(testName, passed, detail = '') {
  totalTests++;
  if (passed) {
    passedTests++;
    console.log(`  [PASS] ${testName}${detail ? ` (${detail})` : ''}`);
  } else {
    failedTests++;
    console.error(`  [FAIL] ${testName}${detail ? ` (${detail})` : ''}`);
  }
}

async function testEmissionsCircuit(poseidon) {
  console.log('\n==================================================');
  console.log('Testing Circuit: emissions_le_limit');
  console.log('==================================================');

  const wasmPath = path.join(ZK_ROOT, 'build/emissions_le_limit_js/emissions_le_limit.wasm');
  const zkeyPath = path.join(ZK_ROOT, 'build/emissions_le_limit_final.zkey');
  const vkeyPath = path.join(ZK_ROOT, 'build/emissions_le_limit_vkey.json');

  if (!fs.existsSync(wasmPath) || !fs.existsSync(zkeyPath) || !fs.existsSync(vkeyPath)) {
    throw new Error('Circuit build artifacts not found. Run "bash scripts/setup.sh" first.');
  }

  const vkey = JSON.parse(fs.readFileSync(vkeyPath, 'utf8'));

  // Test 1: Passing case (value: 85 kgCO2/t <= limit: 2310 kgCO2/t)
  const valValid = 85n;
  const saltValid = 12345678901234567890n;
  const limitValid = 2310n;
  const commValid = poseidon.F.toString(poseidon([valValid, saltValid]));

  try {
    const input = {
      value: valValid.toString(),
      salt: saltValid.toString(),
      commitment: commValid,
      limit: limitValid.toString()
    };
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    const verified = await snarkjs.groth16.verify(vkey, publicSignals, proof);
    report('Passing Case: value=85 <= limit=2310', verified === true, 'proof generated and verified');

    // Test 1b: Verifier rejection on tampered public input
    const tamperedSignals = [...publicSignals];
    tamperedSignals[1] = '1000'; // Altered limit in public signals
    const tamperVerified = await snarkjs.groth16.verify(vkey, tamperedSignals, proof);
    report('Verification Tamper Check: altered limit rejected', tamperVerified === false);
  } catch (err) {
    report('Passing Case: value=85 <= limit=2310', false, err.message);
  }

  // Test 2: Failing case - value > limit (value: 2400 > limit: 2310)
  const valExceed = 2400n;
  const commExceed = poseidon.F.toString(poseidon([valExceed, saltValid]));
  try {
    const input = {
      value: valExceed.toString(),
      salt: saltValid.toString(),
      commitment: commExceed,
      limit: limitValid.toString()
    };
    await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    report('Failing Case: value=2400 > limit=2310', false, 'Should have failed proof generation');
  } catch (err) {
    report('Failing Case: value=2400 > limit=2310', true, 'Constraint assertion failed as expected');
  }

  // Test 3: Failing case - wrong salt / commitment mismatch
  try {
    const wrongSalt = 999999999n;
    const input = {
      value: valValid.toString(),
      salt: wrongSalt.toString(),
      commitment: commValid, // Does not match Poseidon(value, wrongSalt)
      limit: limitValid.toString()
    };
    await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    report('Failing Case: Wrong salt / commitment mismatch', false, 'Should have failed commitment constraint');
  } catch (err) {
    report('Failing Case: Wrong salt / commitment mismatch', true, 'Commitment assertion failed as expected');
  }
}

async function testScrapCircuit(poseidon) {
  console.log('\n==================================================');
  console.log('Testing Circuit: scrap_share_ge');
  console.log('==================================================');

  const wasmPath = path.join(ZK_ROOT, 'build/scrap_share_ge_js/scrap_share_ge.wasm');
  const zkeyPath = path.join(ZK_ROOT, 'build/scrap_share_ge_final.zkey');
  const vkeyPath = path.join(ZK_ROOT, 'build/scrap_share_ge_vkey.json');

  if (!fs.existsSync(wasmPath) || !fs.existsSync(zkeyPath) || !fs.existsSync(vkeyPath)) {
    throw new Error('Circuit build artifacts not found. Run "bash scripts/setup.sh" first.');
  }

  const vkey = JSON.parse(fs.readFileSync(vkeyPath, 'utf8'));

  // Test 1: Passing case (scrapShare: 960 per mille >= minShare: 900 per mille)
  const shareValid = 960n;
  const saltValid = 98765432109876543210n;
  const minValid = 900n;
  const commValid = poseidon.F.toString(poseidon([shareValid, saltValid]));

  try {
    const input = {
      scrapShare: shareValid.toString(),
      salt: saltValid.toString(),
      commitment: commValid,
      minShare: minValid.toString()
    };
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    const verified = await snarkjs.groth16.verify(vkey, publicSignals, proof);
    report('Passing Case: scrapShare=960 >= minShare=900', verified === true, 'proof generated and verified');

    // Test 1b: Verifier rejection on tampered public input
    const tamperedSignals = [...publicSignals];
    tamperedSignals[1] = '990'; // Altered threshold
    const tamperVerified = await snarkjs.groth16.verify(vkey, tamperedSignals, proof);
    report('Verification Tamper Check: altered minShare rejected', tamperVerified === false);
  } catch (err) {
    report('Passing Case: scrapShare=960 >= minShare=900', false, err.message);
  }

  // Test 2: Failing case - scrapShare < minShare (850 < 900)
  const shareLow = 850n;
  const commLow = poseidon.F.toString(poseidon([shareLow, saltValid]));
  try {
    const input = {
      scrapShare: shareLow.toString(),
      salt: saltValid.toString(),
      commitment: commLow,
      minShare: minValid.toString()
    };
    await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    report('Failing Case: scrapShare=850 < minShare=900', false, 'Should have failed proof generation');
  } catch (err) {
    report('Failing Case: scrapShare=850 < minShare=900', true, 'Constraint assertion failed as expected');
  }

  // Test 3: Failing case - scrapShare > 1000 (1050 > 1000)
  const shareExcess = 1050n;
  const commExcess = poseidon.F.toString(poseidon([shareExcess, saltValid]));
  try {
    const input = {
      scrapShare: shareExcess.toString(),
      salt: saltValid.toString(),
      commitment: commExcess,
      minShare: minValid.toString()
    };
    await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    report('Failing Case: scrapShare=1050 > 1000', false, 'Should have failed bound check');
  } catch (err) {
    report('Failing Case: scrapShare=1050 > 1000', true, 'Max bound check failed as expected');
  }

  // Test 4: Failing case - wrong salt / commitment mismatch
  try {
    const wrongSalt = 111111111n;
    const input = {
      scrapShare: shareValid.toString(),
      salt: wrongSalt.toString(),
      commitment: commValid, // Mismatch
      minShare: minValid.toString()
    };
    await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);
    report('Failing Case: Wrong salt / commitment mismatch', false, 'Should have failed commitment constraint');
  } catch (err) {
    report('Failing Case: Wrong salt / commitment mismatch', true, 'Commitment assertion failed as expected');
  }
}

async function main() {
  console.log('==================================================');
  console.log('Running Damga AI ZK Circuit Tests (Groth16)');
  console.log('==================================================');

  const poseidon = await buildPoseidon();

  await testEmissionsCircuit(poseidon);
  await testScrapCircuit(poseidon);

  console.log('\n==================================================');
  console.log(`Test Summary: ${passedTests}/${totalTests} tests passed (${failedTests} failed)`);
  console.log('==================================================\n');

  if (failedTests > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

main().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
