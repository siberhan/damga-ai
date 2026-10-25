import type {
  FileDetail,
  FileSummary,
  DemoCase,
  PassportPublic,
  PassportImporter,
  TypedDataPayload,
  Attempt,
} from './types.ts';
import { mockStore } from './mock/mockStore.ts';

type DemoStateListener = (isDemo: boolean) => void;
const listeners = new Set<DemoStateListener>();

const getEnvMock = (): boolean => {
  try {
    return typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_USE_MOCK === '1';
  } catch {
    return false;
  }
};

let _isDemoMode: boolean = getEnvMock();
let _hasCheckedHealth = false;

export function isDemoMode(): boolean {
  return _isDemoMode;
}

export function subscribeDemoMode(listener: DemoStateListener): () => void {
  listeners.add(listener);
  listener(_isDemoMode);
  return () => {
    listeners.delete(listener);
  };
}

function setDemoMode(val: boolean) {
  if (_isDemoMode !== val) {
    _isDemoMode = val;
    listeners.forEach((l) => l(val));
  }
}

async function checkHealth(): Promise<boolean> {
  if (getEnvMock()) {
    setDemoMode(true);
    return false;
  }
  if (_hasCheckedHealth && !_isDemoMode) {
    return true;
  }

  try {
    const res = await fetch('/api/health', { method: 'GET', credentials: 'omit' });
    if (res.ok) {
      setDemoMode(false);
      _hasCheckedHealth = true;
      return true;
    }
  } catch {
    // health check failed
  }
  setDemoMode(true);
  _hasCheckedHealth = true;
  return false;
}

export async function initApiClient(): Promise<boolean> {
  return await checkHealth();
}

// Mock data is used only when the backend is not running at all (or VITE_USE_MOCK=1).
// When the backend is up, its errors are shown as they are: a failed call never turns into fake data.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (res.ok) return (await res.json()) as T;
  const err = await res.json().catch(() => ({}));
  throw new Error(err.detail || `${res.status} ${res.statusText}`);
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  async getHealth(): Promise<{ status: string; demo: boolean }> {
    const healthy = await checkHealth();
    return { status: healthy ? 'ok' : 'mock', demo: _isDemoMode };
  },

  async getCases(): Promise<DemoCase[]> {
    if (await checkHealth()) return request('/api/cases');
    return mockStore.getCases();
  },

  async getFiles(): Promise<FileSummary[]> {
    if (await checkHealth()) return request('/api/files');
    return mockStore.getFiles();
  },

  async getFile(fileKey: string): Promise<FileDetail> {
    if (await checkHealth()) return request(`/api/files/${encodeURIComponent(fileKey)}`);
    const local = mockStore.getFile(fileKey);
    if (!local) throw new Error(`File key ${fileKey} not found`);
    return local;
  },

  async createFile(plantId: string, year: number, cnCode: string): Promise<FileSummary> {
    if (await checkHealth()) return request('/api/files', json({ plant_id: plantId, year, cn_code: cnCode }));
    return mockStore.createFile(plantId, year, cnCode);
  },

  async uploadAttempt(
    fileKey: string,
    payload: { case_id?: string; formData?: FormData }
  ): Promise<Attempt> {
    if (await checkHealth()) {
      const path = `/api/files/${encodeURIComponent(fileKey)}/attempts`;
      return payload.formData
        ? request(path, { method: 'POST', body: payload.formData })
        : request(path, json({ case_id: payload.case_id }));
    }
    return mockStore.uploadAttempt(fileKey, payload.case_id);
  },

  async submitExplanations(
    fileKey: string,
    attemptIndex: number,
    explanations: Record<string, string>
  ): Promise<Attempt> {
    if (await checkHealth()) {
      return request(
        `/api/files/${encodeURIComponent(fileKey)}/explanations`,
        json({ attempt_index: attemptIndex, explanations })
      );
    }
    return mockStore.submitExplanations(fileKey, attemptIndex, explanations);
  },

  async sendToVerifier(fileKey: string, attemptIndex: number): Promise<{ verifier_link: string }> {
    if (await checkHealth()) {
      return request(`/api/files/${encodeURIComponent(fileKey)}/send`, json({ attempt_index: attemptIndex }));
    }
    return mockStore.sendToVerifier(fileKey, attemptIndex);
  },

  async getVerifierQueue(): Promise<FileSummary[]> {
    if (await checkHealth()) return request('/api/verifier/queue');
    return mockStore.getVerifierQueue();
  },

  async saveResolutions(
    fileKey: string,
    attemptIndex: number,
    redResolutions: Record<string, string>,
    yellowChecked: string[]
  ): Promise<{ success: boolean; attempt: Attempt }> {
    if (await checkHealth()) {
      return request(
        `/api/files/${encodeURIComponent(fileKey)}/attempts/${attemptIndex}/resolutions`,
        json({ red: redResolutions, yellow_checked: yellowChecked })
      );
    }
    return mockStore.saveResolutions(fileKey, attemptIndex, redResolutions, yellowChecked);
  },

  async getTypedData(fileKey: string, attemptIndex: number): Promise<TypedDataPayload> {
    if (await checkHealth()) {
      return request(`/api/files/${encodeURIComponent(fileKey)}/attempts/${attemptIndex}/typed-data`);
    }
    return mockStore.getTypedData(fileKey, attemptIndex);
  },

  async verifyAttempt(
    fileKey: string,
    attemptIndex: number,
    params: { signature?: string; demo_signer?: boolean }
  ): Promise<{ passport_id: number; tx_hash: string | null; etherscan?: string | null; importer_salt?: string }> {
    if (await checkHealth()) {
      return request(
        `/api/files/${encodeURIComponent(fileKey)}/attempts/${attemptIndex}/verify`,
        json(params)
      );
    }
    return mockStore.verifyAttempt(fileKey, attemptIndex, params);
  },

  async getImporterSalt(fileKey: string): Promise<{ passport_id: number; importer_salt: string }> {
    if (await checkHealth()) return request(`/api/files/${encodeURIComponent(fileKey)}/importer-salt`);
    throw new Error('The importer salt exists only when the backend is running');
  },

  async getPassport(id: number): Promise<PassportPublic> {
    if (await checkHealth()) return request(`/api/passports/${id}`);
    const p = mockStore.getPassport(id);
    if (!p) throw new Error(`Passport #${id} not found`);
    return p;
  },

  async getPassportImporter(id: number, salts?: string): Promise<PassportImporter> {
    if (await checkHealth()) {
      const q = salts ? `?salts=${encodeURIComponent(salts)}` : '';
      return request(`/api/passports/${id}/disclose${q}`);
    }
    const imp = mockStore.getPassportImporter(id);
    if (!imp) throw new Error(`Importer disclosure for passport #${id} not found`);
    return imp;
  },

  getDocUrl(fileKey: string, attemptIndex: number, docId: string): string {
    return `/api/docs/${encodeURIComponent(fileKey)}/${attemptIndex}/${encodeURIComponent(docId)}`;
  },
};
