pragma circom 2.0.0;

include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";
include "../node_modules/circomlib/circuits/bitify.circom";

/**
 * @title ScrapShareGe
 * @notice Proves that circular scrap share (in per mille, 0..1000) is greater than or equal to
 *         a minimum threshold minShare, and does not exceed 1000 (100.0%),
 *         matching a Poseidon commitment without revealing the exact scrap share or salt.
 */
template ScrapShareGe() {
    // Private inputs
    signal input scrapShare; // Recycled scrap share in per mille (0..1000, e.g. 960 = 96.0%)
    signal input salt;       // Random blinding factor

    // Public inputs
    signal input commitment; // Poseidon(scrapShare, salt)
    signal input minShare;   // Minimum required scrap share in per mille (0..1000, e.g. 900 = 90.0%)

    // 1. Range checks: constrain scrapShare and minShare to 32 bits to prevent field overflow
    component scrapBits = Num2Bits(32);
    scrapBits.in <== scrapShare;

    component minShareBits = Num2Bits(32);
    minShareBits.in <== minShare;

    // 2. Commitment check: commitment === Poseidon(scrapShare, salt)
    component hasher = Poseidon(2);
    hasher.inputs[0] <== scrapShare;
    hasher.inputs[1] <== salt;
    commitment === hasher.out;

    // 3. Bound check: scrapShare <= 1000 (per mille max is 1000)
    component maxCheck = LessEqThan(32);
    maxCheck.in[0] <== scrapShare;
    maxCheck.in[1] <== 1000;
    maxCheck.out === 1;

    // 4. Threshold check: scrapShare >= minShare (i.e. minShare <= scrapShare)
    component geCheck = LessEqThan(32);
    geCheck.in[0] <== minShare;
    geCheck.in[1] <== scrapShare;
    geCheck.out === 1;
}

component main {public [commitment, minShare]} = ScrapShareGe();
