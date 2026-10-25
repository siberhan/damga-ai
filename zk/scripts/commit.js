#!/usr/bin/env node

/**
 * commit.js - Computes Poseidon commitment for private value and salt
 * Usage: node commit.js <value> <salt>
 *
 * Prints the Poseidon hash as a decimal string (standard field element representation).
 */

import { buildPoseidon } from 'circomlibjs';

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node commit.js <value> <salt>');
    console.error('Example: node commit.js 85 123456');
    process.exit(1);
  }

  const rawValue = args[0];
  const rawSalt = args[1];

  let val, salt;
  try {
    val = BigInt(rawValue);
    salt = BigInt(rawSalt);
  } catch (err) {
    console.error('Error: <value> and <salt> must be valid integers or hex strings');
    process.exit(1);
  }

  const poseidon = await buildPoseidon();
  const hash = poseidon([val, salt]);
  const decimalString = poseidon.F.toString(hash);

  console.log(decimalString);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
