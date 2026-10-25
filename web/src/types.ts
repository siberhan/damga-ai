export type FlagLevel = 'red' | 'yellow' | 'missing' | 'info';
export type FlagSource = 'code' | 'ai';
export type FlagState = 'open' | 'resolved' | 'checked';
export type AttemptStatus = 'green' | 'yellow' | 'red' | 'missing';
export type PassportStatus = 'active' | 'revoked' | 'disputed' | 'superseded';

export interface EvidenceSnippet {
  doc_id: string;
  quote: string;
}

export interface Flag {
  id: string;
  level: FlagLevel;
  rule: string;
  source: FlagSource;
  field?: string;
  message: string;
  values?: Record<string, unknown>;
  evidence: EvidenceSnippet[];
  ai_explanation: string;
  state: FlagState;
  resolution: string | null;
  checked?: boolean;
  exporter_explanation?: string;
  confidence?: number;
}

export interface ExtractionField {
  key: string;
  value: number | string;
  unit?: string;
  quote: string;
  confidence: number;
  quote_check: 'pass' | 'fail' | 'missing';
}

export interface DocumentExtraction {
  doc_id: string;
  doc_type: string;
  doc_sha256: string;
  fields: ExtractionField[];
  injection_screen?: {
    removed: Array<{
      text: string;
      reason: string;
      source_set?: string | null;
    }>;
  };
}

export interface DocumentMeta {
  doc_id: string;
  type: string;
  period: string;
  sha256: string;
  url: string;
  name?: string;
}

export interface EmissionBreakdown {
  source: string;
  t_co2: number;
}

export interface EmissionsData {
  direct_kg_per_t: number;
  eu_default_gap_eur_range?: [number, number];
  breakdown?: EmissionBreakdown[];
  scrap_share_permille: number;
  input_mix_permille: {
    scrap: number;
    pig_iron: number;
    dri: number;
  };
}

export interface Attempt {
  index: number;
  status: AttemptStatus;
  legacy?: boolean;
  note?: string | null;
  counts: {
    red: number;
    yellow: number;
    missing: number;
  };
  direct_kg_per_t: number;
  submitted_at: string;
  tx_hash?: string;
  etherscan?: string;
  result_hash: string;
  docs_root: string;
  flags: Flag[];
  documents: DocumentMeta[];
  extractions?: DocumentExtraction[];
  totals?: {
    from_docs: Record<string, number>;
    from_form: Record<string, number>;
  };
  emissions: EmissionsData;
  model: {
    name: string;
    version: string;
    provider?: string;
    model_hash?: string;
  };
  ruleset_version: string;
  confidence_bps: number;
}

export interface PlantInfo {
  plant_id: string;
  name: string;
  country?: string;
  city?: string;
  installation_name?: string;
}

export interface ProductInfo {
  cn_code: string;
  name: string;
  gtin?: string;
  lot?: string;
}

export interface FileSummary {
  file_key: string;
  plant: PlantInfo;
  year: number;
  product: ProductInfo;
  state: 'draft' | 'attempt_submitted' | 'sent_to_verifier' | 'verified' | 'rejected';
  status: AttemptStatus;
  attempt_count: number;
  passport_id: number | null;
  updated_at?: string;
}

export interface FileDetail {
  file_key: string;
  plant: PlantInfo;
  year: number;
  product: ProductInfo;
  state: string;
  passport_id: number | null;
  attempts: Attempt[];
  history_summary: string;
}

export interface DemoCase {
  id: string;
  name: string;
  description: string;
  badge?: string;
}

export interface PassportClaim {
  label: string;
  statement: string;
  proof: string;
  verified_on_chain: boolean;
}

export interface PassportPublic {
  passport_id: number;
  status: PassportStatus;
  product: ProductInfo & { gtin: string; lot: string };
  plant: PlantInfo;
  reporting_period: string;
  verified_by: {
    name: string;
    address: string;
  };
  issued_at: string;
  process_route: string[];
  claims: PassportClaim[];
  eu_default_value_t_per_t: number;
  markup_2026?: number;
  documents_unchanged: boolean;
  attempt_count: number;
  model: {
    name: string;
    version: string;
  };
  ruleset_version: string;
  chain: {
    registry: string;
    tx_hash: string;
    etherscan: string;
  };
  vc_url: string;
}

export interface PassportImporter {
  passport_id: number;
  direct_kg_per_t: number;
  commitment_match: boolean;
  cost_gap_note: string;
}

export interface TypedDataDomain {
  name: string;
  version: string;
  chainId: number;
  verifyingContract: string;
}

export interface TypedDataPayload {
  domain: TypedDataDomain;
  types: Record<string, Array<{ name: string; type: string }>>;
  primaryType: string;
  message: Record<string, unknown>;
}
