import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mockStore } from '../src/mock/mockStore.ts';
import { MOCK_CHEATING_FILE, MOCK_HONEST_FILE, DEMO_CASES } from '../src/mock/demoData.ts';

describe('Damga AI Web — Mock Store & Business Rule Tests', () => {
  it('loads demo cases according to spec', () => {
    const cases = mockStore.getCases();
    assert.equal(cases.length, 3);
    assert.ok(cases.some((c) => c.id === 'cheat-pigiron-invoice-01'));
    assert.ok(cases.some((c) => c.id === 'honest-eaf-rebar-01'));
    assert.ok(cases.some((c) => c.id === 'missing-gas-bills-01'));
  });

  it('contains the honest file with green status and minted passport #1', () => {
    const honest = mockStore.getFile(MOCK_HONEST_FILE.file_key);
    assert.ok(honest, 'Honest file should exist in mock store');
    assert.equal(honest.state, 'verified');
    assert.equal(honest.passport_id, 1);
    assert.equal(honest.attempts[0].status, 'green');
    assert.equal(honest.attempts[0].counts.red, 0);
    assert.equal(honest.attempts[0].counts.yellow, 0);
    assert.equal(honest.attempts[0].counts.missing, 0);

    const passport = mockStore.getPassport(1);
    assert.ok(passport, 'Passport #1 must exist');
    assert.equal(passport.product.cn_code, '72142000');
    assert.equal(passport.status, 'active');
    assert.equal(passport.claims.length, 2);
  });

  it('contains the cheating file with 3 attempts and required demo flags', () => {
    const cheating = mockStore.getFile(MOCK_CHEATING_FILE.file_key);
    assert.ok(cheating, 'Cheating file should exist in mock store');
    assert.equal(cheating.attempts.length, 3);

    // Attempt 0: Red status
    const att0 = cheating.attempts[0];
    assert.equal(att0.status, 'red');

    // Flag 1: Pig iron discrepancy
    const pigIronFlag = att0.flags.find((f) => f.rule === 'form_vs_docs');
    assert.ok(pigIronFlag, 'Must include form_vs_docs red flag');
    assert.equal(pigIronFlag.level, 'red');
    assert.equal(pigIronFlag.source, 'code');
    assert.match(pigIronFlag.message, /The form says 0 t of pig iron, but invoice INV-PIG-012 shows 800 t/);
    assert.ok(pigIronFlag.evidence.some((e) => e.quote.includes('800.000 t')));

    // Flag 2: Material balance
    const matBalanceFlag = att0.flags.find((f) => f.rule === 'material_balance');
    assert.ok(matBalanceFlag, 'Must include material_balance red flag');
    assert.equal(matBalanceFlag.level, 'red');

    // Flag 3: Yellow flag with exporter explanation
    const yellowFlag = att0.flags.find((f) => f.level === 'yellow');
    assert.ok(yellowFlag, 'Must include yellow flag');
    assert.ok(yellowFlag.exporter_explanation, 'Yellow flag should have exporter explanation');

    // Flag 4: Injection screened info flag
    const injectionFlag = att0.flags.find((f) => f.rule === 'injection_screened');
    assert.ok(injectionFlag, 'Must include injection_screened flag');
    assert.equal(injectionFlag.source, 'code');

    // Attempt 1: Missing evidence state (10 of 12 gas bills)
    const att1 = cheating.attempts[1];
    assert.equal(att1.status, 'missing');
    const missingFlag = att1.flags.find((f) => f.rule === 'missing_evidence');
    assert.ok(missingFlag, 'Must include missing_evidence flag');
    assert.match(missingFlag.message, /10 of 12 gas bills/);

    // Attempt 2: Corrected state
    const att2 = cheating.attempts[2];
    assert.equal(att2.status, 'yellow');
    assert.equal(att2.counts.red, 0);
    assert.equal(att2.counts.missing, 0);
  });

  it('blocks sending to verifier when evidence is missing', () => {
    mockStore.reset();
    const cheating = mockStore.getFile(MOCK_CHEATING_FILE.file_key)!;
    // Attempt 1 is missing evidence
    assert.throws(
      () => mockStore.sendToVerifier(cheating.file_key, 1),
      /Missing required evidence must be uploaded first/
    );
  });

  it('blocks verifier signing when red flags are unresolved or yellow unchecked', () => {
    mockStore.reset();
    const cheating = mockStore.getFile(MOCK_CHEATING_FILE.file_key)!;

    // Attempt 0 has 2 red flags unresolved
    assert.throws(
      () => mockStore.verifyAttempt(cheating.file_key, 0, { demo_signer: true }),
      /open red flag/
    );

    // Attempt 2 has 1 yellow flag unchecked
    assert.throws(
      () => mockStore.verifyAttempt(cheating.file_key, 2, { demo_signer: true }),
      /yellow flag/
    );

    // Check yellow flag and retry
    mockStore.saveResolutions(cheating.file_key, 2, {}, ['F3-REV']);
    const mintResult = mockStore.verifyAttempt(cheating.file_key, 2, { demo_signer: true });

    assert.ok(mintResult.passport_id > 1, 'Should mint passport with id > 1');
    assert.ok(mintResult.tx_hash.startsWith('0x'));

    const newPassport = mockStore.getPassport(mintResult.passport_id);
    assert.ok(newPassport);
    assert.equal(newPassport.status, 'active');
  });

  it('provides confidential importer view matching on-chain commitments without exposing prices', () => {
    const importer = mockStore.getPassportImporter(1);
    assert.ok(importer);
    assert.equal(importer.direct_kg_per_t, 92);
    assert.equal(importer.commitment_match, true);
    assert.equal('scrap_share_permille' in importer, false);
    assert.equal('input_mix_permille' in importer, false);

    const passportJson = JSON.stringify(mockStore.getPassport(1));
    assert.equal(passportJson.includes('EUR'), false, 'Public passport must not contain prices');
    assert.equal(passportJson.includes('price'), false, 'Public passport must not contain prices');
    assert.equal(passportJson.includes('INV-SCRAP'), false, 'Public passport must not expose invoices');
  });
});
