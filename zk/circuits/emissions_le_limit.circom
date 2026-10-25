pragma circom 2.0.0;

include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";
include "../node_modules/circomlib/circuits/bitify.circom";

/**
 * @title EmissionsLeLimit
 * @notice Proves that direct emissions (in kgCO2 per tonne) are less than or equal to a given limit,
 *         and matches a Poseidon commitment without revealing the exact emission value or salt.
 */
template EmissionsLeLimit() {
    // Private inputs
    signal input value;  // Direct emissions in kgCO2 per tonne (integer)
    signal input salt;   // Random blinding factor

    // Public inputs
    signal input commitment; // Poseidon(value, salt)
    signal input limit;      // Maximum allowable emissions in kgCO2 per tonne

    // 1. Range checks: constrain value and limit to 32 bits to prevent field overflow
    component valueBits = Num2Bits(32);
    valueBits.in <== value;

    component limitBits = Num2Bits(32);
    limitBits.in <== limit;

    // 2. Commitment check: commitment === Poseidon(value, salt)
    component hasher = Poseidon(2);
    hasher.inputs[0] <== value;
    hasher.inputs[1] <== salt;
    commitment === hasher.out;

    // 3. Inequality check: value <= limit
    component le = LessEqThan(32);
    le.in[0] <== value;
    le.in[1] <== limit;
    le.out === 1;
}

component main {public [commitment, limit]} = EmissionsLeLimit();
