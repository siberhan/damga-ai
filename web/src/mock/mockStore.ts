import type {
  FileDetail,
  FileSummary,
  DemoCase,
  PassportPublic,
  PassportImporter,
  TypedDataPayload,
  Attempt,
} from '../types.ts';
import {
  DEMO_CASES,
  MOCK_HONEST_FILE,
  MOCK_CHEATING_FILE,
  MOCK_PASSPORT_PUBLIC,
  MOCK_PASSPORT_IMPORTER,
  createSummaryList,
} from './demoData.ts';

class MockStore {
  private files: Map<string, FileDetail> = new Map();
  private passports: Map<number, PassportPublic> = new Map();
  private importerData: Map<number, PassportImporter> = new Map();
  private nextPassportId = 2;

  constructor() {
    this.reset();
  }

  public reset() {
    this.files.clear();
    this.passports.clear();
    this.importerData.clear();

    const honest = JSON.parse(JSON.stringify(MOCK_HONEST_FILE)) as FileDetail;
    const cheating = JSON.parse(JSON.stringify(MOCK_CHEATING_FILE)) as FileDetail;

    this.files.set(honest.file_key, honest);
    this.files.set(cheating.file_key, cheating);

    this.passports.set(1, JSON.parse(JSON.stringify(MOCK_PASSPORT_PUBLIC)));
    this.importerData.set(1, JSON.parse(JSON.stringify(MOCK_PASSPORT_IMPORTER)));
  }

  public getCases(): DemoCase[] {
    return DEMO_CASES;
  }

  public getFiles(): FileSummary[] {
    return createSummaryList(Array.from(this.files.values()));
  }

  public getFile(fileKey: string): FileDetail | null {
    return this.files.get(fileKey) || null;
  }

  public createFile(plantId: string, year: number, cnCode: string): FileSummary {
    const randomHex = Math.random().toString(16).substring(2, 10);
    const fileKey = `0x${randomHex}9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8`;
    const newDetail: FileDetail = {
      file_key: fileKey,
      plant: {
        plant_id: plantId || 'TR-ALIAGA-DEMO-001',
        name: 'Aliağa Demo Steel Works (fictional)',
        country: 'TR',
        city: 'Aliağa, İzmir',
        installation_name: 'Melt shop and rolling mill',
      },
      year: year || 2026,
      product: {
        cn_code: cnCode || '72142000',
        name: 'Concrete reinforcing bar (rebar)',
        gtin: '00200000000014',
        lot: `${year}-${cnCode}`,
      },
      state: 'draft',
      passport_id: null,
      history_summary: 'New file created. No attempt submitted yet.',
      attempts: [],
    };

    this.files.set(fileKey, newDetail);
    return {
      file_key: fileKey,
      plant: newDetail.plant,
      year: newDetail.year,
      product: newDetail.product,
      state: 'draft',
      status: 'missing',
      attempt_count: 0,
      passport_id: null,
      updated_at: new Date().toISOString(),
    };
  }

  public uploadAttempt(fileKey: string, caseId?: string): Attempt {
    const file = this.files.get(fileKey);
    if (!file) {
      throw new Error(`File not found: ${fileKey}`);
    }

    let templateAttempt: Attempt;
    if (caseId === 'cheat-pigiron-invoice-01') {
      templateAttempt = JSON.parse(JSON.stringify(MOCK_CHEATING_FILE.attempts[0]));
    } else if (caseId === 'missing-gas-bills-01') {
      templateAttempt = JSON.parse(JSON.stringify(MOCK_CHEATING_FILE.attempts[1]));
    } else if (caseId === 'honest-eaf-rebar-01') {
      templateAttempt = JSON.parse(JSON.stringify(MOCK_HONEST_FILE.attempts[0]));
    } else {
      // Default: clean new attempt based on honest template
      templateAttempt = JSON.parse(JSON.stringify(MOCK_HONEST_FILE.attempts[0]));
    }

    const newIndex = file.attempts.length;
    templateAttempt.index = newIndex;
    templateAttempt.submitted_at = new Date().toISOString();
    templateAttempt.tx_hash = `0x${Math.random().toString(16).substring(2)}${Math.random().toString(16).substring(2)}`;
    templateAttempt.etherscan = `https://sepolia.etherscan.io/tx/${templateAttempt.tx_hash}`;

    file.attempts.push(templateAttempt);
    file.state = 'attempt_submitted';
    file.history_summary = `${file.attempts.length} attempt(s) submitted. Latest status: ${templateAttempt.status.toUpperCase()}.`;

    return templateAttempt;
  }

  public submitExplanations(fileKey: string, attemptIndex: number, explanations: Record<string, string>): Attempt {
    const file = this.files.get(fileKey);
    if (!file) throw new Error('File not found');
    const attempt = file.attempts.find((a) => a.index === attemptIndex);
    if (!attempt) throw new Error('Attempt not found');

    for (const flag of attempt.flags) {
      if (explanations[flag.id]) {
        flag.exporter_explanation = explanations[flag.id];
      }
    }
    return attempt;
  }

  public sendToVerifier(fileKey: string, attemptIndex: number): { verifier_link: string } {
    const file = this.files.get(fileKey);
    if (!file) throw new Error('File not found');
    const attempt = file.attempts.find((a) => a.index === attemptIndex);
    if (!attempt) throw new Error('Attempt not found');

    // Rule: Disabled while missing evidence
    if (attempt.status === 'missing' || attempt.counts.missing > 0) {
      throw new Error('Cannot send to verifier: Missing required evidence must be uploaded first.');
    }

    file.state = 'sent_to_verifier';
    return {
      verifier_link: `/verifier/files/${fileKey}`,
    };
  }

  public getVerifierQueue(): FileSummary[] {
    return Array.from(this.files.values())
      .filter((f) => f.state === 'sent_to_verifier' || f.state === 'attempt_submitted' || f.state === 'verified')
      .map((f) => {
        const latestAttempt = f.attempts[f.attempts.length - 1];
        return {
          file_key: f.file_key,
          plant: f.plant,
          year: f.year,
          product: f.product,
          state: f.state as FileSummary['state'],
          status: latestAttempt ? latestAttempt.status : 'missing',
          attempt_count: f.attempts.length,
          passport_id: f.passport_id,
          updated_at: latestAttempt ? latestAttempt.submitted_at : new Date().toISOString(),
        };
      });
  }

  public saveResolutions(
    fileKey: string,
    attemptIndex: number,
    redResolutions: Record<string, string>,
    yellowChecked: string[]
  ): { success: boolean; attempt: Attempt } {
    const file = this.files.get(fileKey);
    if (!file) throw new Error('File not found');
    const attempt = file.attempts.find((a) => a.index === attemptIndex);
    if (!attempt) throw new Error('Attempt not found');

    for (const flag of attempt.flags) {
      if (flag.level === 'red') {
        if (redResolutions[flag.id]) {
          flag.resolution = redResolutions[flag.id];
          flag.state = 'resolved';
        }
      } else if (flag.level === 'yellow') {
        if (yellowChecked.includes(flag.id)) {
          flag.checked = true;
          flag.state = 'checked';
        } else {
          flag.checked = false;
        }
      }
    }

    return { success: true, attempt };
  }

  public getTypedData(fileKey: string, attemptIndex: number): TypedDataPayload {
    const file = this.files.get(fileKey);
    if (!file) throw new Error('File not found');
    const attempt = file.attempts.find((a) => a.index === attemptIndex);
    if (!attempt) throw new Error('Attempt not found');

    return {
      domain: {
        name: 'DamgaAI',
        version: '1',
        chainId: 11155111, // Sepolia
        verifyingContract: '0x71C8A1D3b5b630eE640B2f4f2D0aB5C7D0E99812',
      },
      types: {
        Verification: [
          { name: 'fileKey', type: 'bytes32' },
          { name: 'attemptIndex', type: 'uint256' },
          { name: 'docsRoot', type: 'bytes32' },
          { name: 'resultHash', type: 'bytes32' },
          { name: 'resolutionsHash', type: 'bytes32' },
          { name: 'redResolved', type: 'uint16' },
          { name: 'yellowChecked', type: 'uint16' },
          { name: 'emissionsCommitment', type: 'uint256' },
          { name: 'scrapCommitment', type: 'uint256' },
          { name: 'emissionsLimit', type: 'uint32' },
          { name: 'minScrapShare', type: 'uint16' },
          { name: 'vcHash', type: 'bytes32' },
        ],
      },
      primaryType: 'Verification',
      message: {
        fileKey: file.file_key,
        attemptIndex,
        docsRoot: attempt.docs_root,
        resultHash: attempt.result_hash,
        resolutionsHash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        redResolved: attempt.flags.filter((f) => f.level === 'red' && f.resolution).length,
        yellowChecked: attempt.flags.filter((f) => f.level === 'yellow' && f.checked).length,
        emissionsCommitment: '0x1c8b3a77d201e5a9b...',
        scrapCommitment: '0x2d9e4a88f302a6b0c...',
        emissionsLimit: 150,
        minScrapShare: 900,
        vcHash: '0x998877665544332211...',
      },
    };
  }

  public verifyAttempt(
    fileKey: string,
    attemptIndex: number,
    options: { signature?: string; demo_signer?: boolean }
  ): { passport_id: number; tx_hash: string } {
    const file = this.files.get(fileKey);
    if (!file) throw new Error('File not found');
    const attempt = file.attempts.find((a) => a.index === attemptIndex);
    if (!attempt) throw new Error('Attempt not found');

    // Hard verification checks
    if (attempt.status === 'missing' || attempt.counts.missing > 0) {
      throw new Error('Signing blocked: Missing evidence must be resolved before signing.');
    }

    const openRed = attempt.flags.filter((f) => f.level === 'red' && !f.resolution);
    if (openRed.length > 0) {
      throw new Error(`Signing blocked: ${openRed.length} open red flag(s) must have recorded verifier resolutions.`);
    }

    const uncheckedYellow = attempt.flags.filter((f) => f.level === 'yellow' && !f.checked);
    if (uncheckedYellow.length > 0) {
      throw new Error(`Signing blocked: ${uncheckedYellow.length} yellow flag(s) must be reviewed and marked checked.`);
    }

    const passportId = this.nextPassportId++;
    const txHash = `0x${Math.random().toString(16).substring(2)}${Math.random().toString(16).substring(2)}`;

    const newPassport: PassportPublic = {
      passport_id: passportId,
      status: 'active',
      product: {
        cn_code: file.product.cn_code,
        name: file.product.name,
        gtin: file.product.gtin || '00200000000014',
        lot: file.product.lot || `${file.year}-${file.product.cn_code}`,
      },
      plant: file.plant,
      reporting_period: String(file.year),
      verified_by: {
        name: options.demo_signer ? 'Demo Verification GmbH (fictional verifier)' : 'Demo Verification GmbH (fictional)',
        address: '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC',
      },
      issued_at: new Date().toISOString(),
      process_route: ['EAF', 'continuous_casting', 'hot_rolling'],
      claims: [
        {
          label: 'Direct emissions',
          statement: '≤ 0.150 tCO₂ per tonne',
          proof: 'zk-groth16',
          verified_on_chain: true,
        },
        {
          label: 'Scrap share of metal input',
          statement: '≥ 90%',
          proof: 'zk-groth16',
          verified_on_chain: true,
        },
      ],
      eu_default_value_t_per_t: 2.310,
      markup_2026: 0.10,
      documents_unchanged: true,
      attempt_count: file.attempts.length,
      model: attempt.model,
      ruleset_version: attempt.ruleset_version,
      chain: {
        registry: '0x71C8A1D3b5b630eE640B2f4f2D0aB5C7D0E99812',
        tx_hash: txHash,
        etherscan: `https://sepolia.etherscan.io/tx/${txHash}`,
      },
      vc_url: `/api/passports/${passportId}/vc`,
    };

    const newImporter: PassportImporter = {
      passport_id: passportId,
      direct_kg_per_t: attempt.emissions.direct_kg_per_t,
      commitment_match: true,
      cost_gap_note: 'Using the verified value instead of the EU default (2.310 tCO2/t + 10% mark-up in 2026).',
    };

    this.passports.set(passportId, newPassport);
    this.importerData.set(passportId, newImporter);

    file.state = 'verified';
    file.passport_id = passportId;

    return { passport_id: passportId, tx_hash: txHash };
  }

  public getPassport(id: number): PassportPublic | null {
    return this.passports.get(id) || null;
  }

  public getPassportImporter(id: number): PassportImporter | null {
    return this.importerData.get(id) || null;
  }
}

export const mockStore = new MockStore();
