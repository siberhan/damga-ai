import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { api, isDemoMode } from '../src/api.ts';

describe('Damga AI Web — API Client Tests', () => {
  it('falls back to demo mode and mockStore when backend is offline', async () => {
    const health = await api.getHealth();
    assert.equal(health.demo, true);
    assert.equal(isDemoMode(), true);

    const files = await api.getFiles();
    assert.ok(files.length >= 2, 'Should return at least honest and cheating files');

    const cases = await api.getCases();
    assert.ok(cases.length >= 3);
  });

  it('retrieves file details and handles attempt workflows', async () => {
    const files = await api.getFiles();
    const honestSummary = files.find((f) => f.plant.name.includes('Aliağa'));
    assert.ok(honestSummary);

    const fileDetail = await api.getFile(honestSummary.file_key);
    assert.equal(fileDetail.file_key, honestSummary.file_key);
    assert.ok(fileDetail.attempts.length > 0);

    const typedData = await api.getTypedData(honestSummary.file_key, 0);
    assert.equal(typedData.primaryType, 'Verification');
    assert.equal(typedData.domain.name, 'DamgaAI');
  });

  it('fetches passport #1 and importer disclosure', async () => {
    const passport = await api.getPassport(1);
    assert.equal(passport.passport_id, 1);
    assert.equal(passport.product.cn_code, '72142000');
    assert.equal(passport.verified_by.name, 'Demo Verification GmbH (fictional)');

    const importer = await api.getPassportImporter(1, 'salt_test_123');
    assert.equal(importer.passport_id, 1);
    assert.equal(importer.direct_kg_per_t, 92);
    assert.equal(importer.commitment_match, true);
  });
});
