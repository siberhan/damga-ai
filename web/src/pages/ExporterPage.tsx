import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api';
import type { FileSummary, FileDetail, DemoCase, Attempt, DocumentMeta } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { DocumentModal } from '../components/DocumentModal';
import { RoleGuide } from '../components/RoleGuide';

export const ExporterPage: React.FC = () => {
  const { fileKey } = useParams<{ fileKey?: string }>();

  const [files, setFiles] = useState<FileSummary[]>([]);
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [activeFile, setActiveFile] = useState<FileDetail | null>(null);
  const [selectedAttemptIndex, setSelectedAttemptIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New file form state
  const [showNewFileModal, setShowNewFileModal] = useState<boolean>(false);
  const [newPlantId, setNewPlantId] = useState<string>('TR-ALIAGA-DEMO-001');
  const [newYear, setNewYear] = useState<number>(2026);
  const [newCnCode, setNewCnCode] = useState<string>('72142000');

  // New attempt upload / demo case pick state
  const [selectedCaseId, setSelectedCaseId] = useState<string>('cheat-pigiron-invoice-01');
  const [uploadingAttempt, setUploadingAttempt] = useState<boolean>(false);

  // Yellow explanations state
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [savingExplanation, setSavingExplanation] = useState<boolean>(false);
  const [explanationSavedMsg, setExplanationSavedMsg] = useState<string | null>(null);

  // Send to verifier state
  const [sendingVerifier, setSendingVerifier] = useState<boolean>(false);
  const [verifierSuccessMsg, setVerifierSuccessMsg] = useState<string | null>(null);

  // Document modal state
  const [activeDoc, setActiveDoc] = useState<DocumentMeta | null>(null);

  // Disclosure salt the exporter passes privately to its EU importer
  const [importerSalt, setImporterSalt] = useState<string | null>(null);
  const [saltCopied, setSaltCopied] = useState<boolean>(false);
  const activeFileKey = activeFile?.file_key;
  const activePassportId = activeFile?.passport_id;

  useEffect(() => {
    let ignore = false;
    setImporterSalt(null);
    setSaltCopied(false);
    if (activeFileKey && activePassportId) {
      api
        .getImporterSalt(activeFileKey)
        .then((r) => {
          if (!ignore) setImporterSalt(r.importer_salt);
        })
        .catch(() => {
          if (!ignore) setImporterSalt(null);
        });
    }
    return () => {
      ignore = true;
    };
  }, [activeFileKey, activePassportId]);

  const loadFiles = async () => {
    try {
      const [fileList, caseList] = await Promise.all([api.getFiles(), api.getCases()]);
      setFiles(fileList);
      setCases(caseList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load exporter data');
    } finally {
      setLoading(false);
    }
  };

  const loadFileDetail = async (key: string) => {
    try {
      setError(null);
      const detail = await api.getFile(key);
      setActiveFile(detail);
      if (detail.attempts.length > 0) {
        const lastIdx = detail.attempts.length - 1;
        setSelectedAttemptIndex(lastIdx);
        // initialize explanations from attempt flags
        const expMap: Record<string, string> = {};
        for (const flag of detail.attempts[lastIdx].flags) {
          if (flag.exporter_explanation) {
            expMap[flag.id] = flag.exporter_explanation;
          }
        }
        setExplanations(expMap);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load file details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const init = async () => {
      try {
        const [fileList, caseList] = await Promise.all([api.getFiles(), api.getCases()]);
        if (!ignore) {
          setFiles(fileList);
          setCases(caseList);
        }
      } catch (err: unknown) {
        if (!ignore) setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    init();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;
    if (fileKey) {
      const fetchDetail = async () => {
        try {
          const detail = await api.getFile(fileKey);
          if (!ignore) {
            setActiveFile(detail);
            if (detail.attempts.length > 0) {
              const lastIdx = detail.attempts.length - 1;
              setSelectedAttemptIndex(lastIdx);
              const expMap: Record<string, string> = {};
              for (const flag of detail.attempts[lastIdx].flags) {
                if (flag.exporter_explanation) expMap[flag.id] = flag.exporter_explanation;
              }
              setExplanations(expMap);
            }
          }
        } catch (err: unknown) {
          if (!ignore) setError(err instanceof Error ? err.message : 'Failed to load file');
        } finally {
          if (!ignore) setLoading(false);
        }
      };
      fetchDetail();
    }
    return () => {
      ignore = true;
    };
  }, [fileKey]);

  const handleCreateFile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createFile(newPlantId, newYear, newCnCode);
      setShowNewFileModal(false);
      await loadFiles();
      window.location.hash = '';
      window.location.href = `/exporter/files/${created.file_key}`;
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Could not create file');
    }
  };

  const handleUploadAttempt = async () => {
    if (!activeFile) return;
    try {
      setUploadingAttempt(true);
      await api.uploadAttempt(activeFile.file_key, { case_id: selectedCaseId });
      await loadFileDetail(activeFile.file_key);
      await loadFiles();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to upload attempt');
    } finally {
      setUploadingAttempt(false);
    }
  };

  const handleSaveExplanations = async () => {
    if (!activeFile) return;
    try {
      setSavingExplanation(true);
      setExplanationSavedMsg(null);
      await api.submitExplanations(activeFile.file_key, selectedAttemptIndex, explanations);
      setExplanationSavedMsg('Explanations saved successfully.');
      setTimeout(() => setExplanationSavedMsg(null), 3000);
      await loadFileDetail(activeFile.file_key);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to save explanation');
    } finally {
      setSavingExplanation(false);
    }
  };

  const handleSendToVerifier = async () => {
    if (!activeFile) return;
    try {
      setSendingVerifier(true);
      setVerifierSuccessMsg(null);
      const res = await api.sendToVerifier(activeFile.file_key, selectedAttemptIndex);
      setVerifierSuccessMsg(`File successfully dispatched to verifier queue: ${res.verifier_link}`);
      await loadFileDetail(activeFile.file_key);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error sending to verifier');
    } finally {
      setSendingVerifier(false);
    }
  };

  const currentAttempt: Attempt | undefined = activeFile?.attempts[selectedAttemptIndex];

  // If viewing file detail screen
  if (fileKey && activeFile) {
    const isMissingEvidence =
      currentAttempt?.status === 'missing' || (currentAttempt && currentAttempt.counts.missing > 0);

    return (
      <div>
        <RoleGuide
          step={1}
          role="Exporter (Turkish steel plant)"
          steps={['Open a file or create a new one', 'Pick a demo case and upload it as a new attempt', 'Fix or explain red findings until the file is green']}
          next={{ label: 'Send to verifier', to: '/verifier' }}
        />
        <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link to="/exporter" style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            ← Back to Exporter Files
          </Link>
          <span style={{ color: 'var(--border-strong)' }}>/</span>
          <span className="font-mono" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {activeFile.file_key.substring(0, 14)}...
          </span>
        </div>

        {/* File Header */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  {activeFile.plant.name}
                </h1>
                <StatusBadge status={currentAttempt?.status || 'missing'} size="md" />
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                Product: <strong>{activeFile.product.name}</strong> (CN {activeFile.product.cn_code}) &bull; Reporting Period: <strong>{activeFile.year}</strong> &bull; Plant ID: <code>{activeFile.plant.plant_id}</code>
              </p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '0.35rem' }}>
                History summary: <em>{activeFile.history_summary}</em>
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              {activeFile.passport_id && (
                <Link to={`/passport/${activeFile.passport_id}`} className="btn btn-secondary">
                  View Minted Passport #{activeFile.passport_id} ↗
                </Link>
              )}
            </div>
          </div>

          {/* Disclosure salt for the importer */}
          {importerSalt && (
            <div style={{ marginTop: '1.25rem', padding: '0.85rem 1rem', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>
                Disclosure salt for your EU importer
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '0.3rem 0 0.6rem' }}>
                Send this privately to your importer. With it, the importer sees the exact direct emissions on the passport page and can check them against the on-chain commitment. Without it, only the proven claims are visible.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <code style={{ flex: '1 1 16rem', minWidth: 0, wordBreak: 'break-all', fontSize: '0.78rem' }}>{importerSalt}</code>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    navigator.clipboard?.writeText(importerSalt).then(() => setSaltCopied(true)).catch(() => setSaltCopied(false));
                  }}
                >
                  {saltCopied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          )}

          {/* Attempt Selector */}
          {activeFile.attempts.length > 0 && (
            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginRight: '0.5rem' }}>
                Select Attempt ({activeFile.attempts.length}):
              </span>
              {activeFile.attempts.map((att, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedAttemptIndex(idx);
                    const expMap: Record<string, string> = {};
                    for (const flag of att.flags) {
                      if (flag.exporter_explanation) expMap[flag.id] = flag.exporter_explanation;
                    }
                    setExplanations(expMap);
                  }}
                  className={`btn ${selectedAttemptIndex === idx ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.3rem 0.75rem', fontSize: '0.82rem' }}
                >
                  Attempt {idx + 1} &bull; {att.legacy ? 'old set' : <StatusBadge status={att.status} size="sm" showIcon={false} />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Current Attempt AI Result Banner */}
        {currentAttempt ? (
          <div>
            <div className={`status-banner status-${currentAttempt.status}`}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>
                {currentAttempt.status === 'green' && '✓'}
                {currentAttempt.status === 'yellow' && '⚠'}
                {currentAttempt.status === 'red' && '✕'}
                {currentAttempt.status === 'missing' && '⊘'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    Attempt {currentAttempt.index + 1} Status: {currentAttempt.status.toUpperCase()}
                  </h3>
                  <div style={{ fontSize: '0.82rem' }}>
                    Submitted: {new Date(currentAttempt.submitted_at).toLocaleString()}
                  </div>
                </div>
                <p style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
                  {currentAttempt.legacy && currentAttempt.note}
                  {!currentAttempt.legacy && currentAttempt.status === 'green' && 'All rule checks passed. No fraud discrepancies or missing documentation detected. Ready for accredited verifier sign-off.'}
                  {currentAttempt.status === 'yellow' && 'Advisory findings detected. Exporter operational explanations are required before the verifier can conclude review.'}
                  {currentAttempt.status === 'red' && 'Critical rule failure. Severe discrepancy detected between declaration form and uploaded primary evidence or physical material balance.'}
                  {currentAttempt.status === 'missing' && 'Mandatory evidence incomplete. Primary documentation for required periods is missing. Submission to verifier is blocked until all records are sealed.'}
                </p>
                <div style={{ marginTop: '0.5rem', fontSize: '0.82rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <span>Red Flags: <strong>{currentAttempt.counts.red}</strong></span>
                  <span>Yellow Flags: <strong>{currentAttempt.counts.yellow}</strong></span>
                  <span>Missing Evidence: <strong>{currentAttempt.counts.missing}</strong></span>
                  <span>Model Confidence: <strong>{(currentAttempt.confidence_bps / 100).toFixed(1)}%</strong></span>
                  {currentAttempt.tx_hash && (
                    <span>
                      Sealed Tx:{' '}
                      <a href={currentAttempt.etherscan} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>
                        {currentAttempt.tx_hash.substring(0, 10)}... (Etherscan ↗)
                      </a>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Direct Emissions vs EU Default */}
            <div className="card">
              <h2 className="card-title">Direct Emissions vs EU CBAM Benchmark</h2>
              <div className="emissions-grid">
                <div className="stat-box">
                  <div className="stat-box-label">Verified Direct Emissions</div>
                  <div className="stat-box-value" style={{ color: '#0369a1' }}>
                    {(currentAttempt.emissions.direct_kg_per_t / 1000).toFixed(3)}
                    <span style={{ fontSize: '0.9rem', fontWeight: 500, marginLeft: '4px' }}>tCO₂ / t</span>
                  </div>
                  <div className="stat-box-sub">
                    {currentAttempt.emissions.direct_kg_per_t} kgCO₂ per tonne product
                  </div>
                </div>

                <div className="stat-box">
                  <div className="stat-box-label">EU Default (Turkey 2026)</div>
                  <div className="stat-box-value" style={{ color: '#991b1b' }}>
                    2.541
                    <span style={{ fontSize: '0.9rem', fontWeight: 500, marginLeft: '4px' }}>tCO₂ / t</span>
                  </div>
                  <div className="stat-box-sub">
                    Base default 2.310 tCO₂/t + 10% mark-up penalty in 2026
                  </div>
                </div>

                <div className="stat-box">
                  <div className="stat-box-label">Scrap Share of Metal Input</div>
                  <div className="stat-box-value" style={{ color: '#065f46' }}>
                    {(currentAttempt.emissions.scrap_share_permille / 10).toFixed(1)}%
                  </div>
                  <div className="stat-box-sub">
                    Scrap EAF Process Route
                  </div>
                </div>

                {currentAttempt.emissions.eu_default_gap_eur_range && (
                  <div className="stat-box" style={{ background: '#ecfdf5', borderColor: '#a7f3d0' }}>
                    <div className="stat-box-label" style={{ color: '#065f46' }}>Cost Gap Saving vs Default</div>
                    <div className="stat-box-value" style={{ color: '#065f46' }}>
                      €{currentAttempt.emissions.eu_default_gap_eur_range[0]} – €{currentAttempt.emissions.eu_default_gap_eur_range[1]}
                      <span style={{ fontSize: '0.9rem', fontWeight: 500, marginLeft: '4px' }}>/ t</span>
                    </div>
                    <div className="stat-box-sub" style={{ color: '#065f46' }}>
                      Potential ETS certificate liability saved per tonne of steel
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* AI and Deterministic Code Flags */}
            <div className="card">
              <h2 className="card-title">
                <span>AI & Deterministic Code Audit Flags</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
                  {currentAttempt.flags.length} finding(s)
                </span>
              </h2>

              {currentAttempt.flags.length === 0 ? (
                <div style={{ padding: '1rem', background: '#ecfdf5', borderRadius: '6px', color: '#065f46', fontSize: '0.9rem' }}>
                  ✓ No discrepancies detected. Declaration matches 100% of verified invoices, tickets, and bills.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {currentAttempt.flags.map((flag) => (
                    <div key={flag.id} className={`flag-card level-${flag.level}`}>
                      <div className="flag-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <StatusBadge status={flag.level} size="sm" />
                          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Rule: {flag.rule}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="flag-source-badge">
                            source: <strong>{flag.source}</strong>
                          </span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            Status: <strong>{flag.state.toUpperCase()}</strong>
                          </span>
                        </div>
                      </div>

                      <p style={{ fontSize: '0.95rem', fontWeight: 500, color: 'var(--text-main)', marginTop: '0.25rem' }}>
                        {flag.message}
                      </p>

                      {/* Evidence quote highlighted snippet */}
                      {flag.evidence && flag.evidence.length > 0 && (
                        <div style={{ marginTop: '0.5rem' }}>
                          <span style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>
                            Verbatim Document Evidence Snippet:
                          </span>
                          {flag.evidence.map((ev, i) => (
                            <div key={i} className="evidence-quote">
                              <span style={{ display: 'block', fontSize: '0.75rem', color: '#92400e', marginBottom: '2px' }}>
                                [{ev.doc_id}]
                              </span>
                              &ldquo;{ev.quote}&rdquo;
                            </div>
                          ))}
                        </div>
                      )}

                      {/* AI Explanation */}
                      {flag.ai_explanation && (
                        <div className="ai-explanation-box">
                          <strong>AI Explanation:</strong> {flag.ai_explanation}
                        </div>
                      )}

                      {/* Yellow explanation box for exporter */}
                      {flag.level === 'yellow' && (
                        <div style={{ marginTop: '0.75rem', background: '#fffbeb', border: '1px solid #fde68a', padding: '0.75rem', borderRadius: '4px' }}>
                          <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#92400e', marginBottom: '0.35rem' }}>
                            Exporter Operational Explanation (Required for Verifier):
                          </label>
                          <textarea
                            rows={2}
                            value={explanations[flag.id] ?? flag.exporter_explanation ?? ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              setExplanations((prev) => ({ ...prev, [flag.id]: val }));
                            }}
                            placeholder="Explain operational variance (e.g. maintenance downtime, scrap mix change)..."
                            style={{ width: '100%', fontSize: '0.88rem' }}
                          />
                        </div>
                      )}

                      {flag.resolution && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#065f46', background: '#ecfdf5', padding: '0.5rem', borderRadius: '4px' }}>
                          <strong>Verifier Resolution Hash:</strong> {flag.resolution}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Save explanation button if any yellow flags */}
                  {currentAttempt.flags.some((f) => f.level === 'yellow') && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem' }}>
                      <button
                        className="btn btn-primary"
                        onClick={handleSaveExplanations}
                        disabled={savingExplanation}
                      >
                        {savingExplanation ? 'Saving...' : 'Save Exporter Explanations'}
                      </button>
                      {explanationSavedMsg && (
                        <span style={{ color: '#065f46', fontSize: '0.85rem', fontWeight: 600 }}>
                          ✓ {explanationSavedMsg}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Per-Document Extracted Fields with Quotes */}
            <div className="card">
              <h2 className="card-title">
                <span>Per-Document Extracted Primary Evidence</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
                  {currentAttempt.documents.length} document(s) sealed
                </span>
              </h2>

              <table className="data-table">
                <thead>
                  <tr>
                    <th>Doc ID / Name</th>
                    <th>Type</th>
                    <th>Period</th>
                    <th>Extracted Key & Value</th>
                    <th>Verbatim Quote Snippet</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {currentAttempt.documents.map((doc) => {
                    const docExtraction = currentAttempt.extractions?.find((e) => e.doc_id === doc.doc_id);
                    return (
                      <tr key={doc.doc_id}>
                        <td>
                          <strong>{doc.name || doc.doc_id}</strong>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="font-mono">
                            {doc.sha256.substring(0, 16)}...
                          </div>
                        </td>
                        <td>{doc.type}</td>
                        <td>{doc.period}</td>
                        <td>
                          {docExtraction && docExtraction.fields.length > 0 ? (
                            docExtraction.fields.map((f, fi) => (
                              <div key={fi} style={{ marginBottom: '4px' }}>
                                <code>{f.key}</code>: <strong>{f.value} {f.unit || ''}</strong>
                              </div>
                            ))
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Audit summary</span>
                          )}
                        </td>
                        <td>
                          {docExtraction && docExtraction.fields.length > 0 ? (
                            docExtraction.fields.map((f, fi) => (
                              <div key={fi} className="evidence-quote" style={{ margin: '2px 0', fontSize: '0.78rem' }}>
                                &ldquo;{f.quote}&rdquo;
                              </div>
                            ))
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>—</span>
                          )}
                        </td>
                        <td>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => setActiveDoc(doc)}
                          >
                            Inspect PDF
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Action Bar: Send to Verifier */}
            <div className="card" style={{ background: '#f8fafc', borderColor: '#cbd5e1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Submit Declaration to Accredited Verifier</h3>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    Once ready, lock the attempt and dispatch to Demo Verification GmbH for EIP-712 audit and ZK passport issuance.
                  </p>
                  {isMissingEvidence && (
                    <div style={{ marginTop: '0.5rem', color: '#991b1b', fontSize: '0.85rem', fontWeight: 600 }}>
                      ⊘ &ldquo;Send to verifier&rdquo; disabled: Incomplete submission. All required energy and material evidence must be provided.
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleSendToVerifier}
                    disabled={isMissingEvidence || sendingVerifier}
                    style={{ minWidth: '180px', padding: '0.65rem 1.25rem' }}
                  >
                    {sendingVerifier ? 'Sending...' : 'Send to Verifier →'}
                  </button>
                  {verifierSuccessMsg && (
                    <span style={{ color: '#065f46', fontSize: '0.82rem', fontWeight: 600 }}>
                      ✓ {verifierSuccessMsg}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Attempt History with Etherscan Links */}
            <div className="card">
              <h2 className="card-title">Attempt History & On-Chain Sealing</h2>
              <div className="timeline">
                {activeFile.attempts.map((att, i) => (
                  <div key={i} className="timeline-item">
                    <div
                      className={`timeline-marker status-${att.status}`}
                      style={{ border: '2px solid currentColor' }}
                    >
                      {i + 1}
                    </div>
                    <div className="timeline-content">
                      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <strong>Attempt #{att.index + 1}</strong> &bull; <StatusBadge status={att.status} size="sm" />
                        </div>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {new Date(att.submitted_at).toLocaleString()}
                        </div>
                      </div>
                      <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                        Direct Emissions: <strong>{att.emissions.direct_kg_per_t} kgCO₂/t</strong> &bull; Red Flags: <strong>{att.counts.red}</strong>, Yellow Flags: <strong>{att.counts.yellow}</strong>, Missing: <strong>{att.counts.missing}</strong>
                      </p>
                      {att.tx_hash && (
                        <div style={{ marginTop: '0.25rem', fontSize: '0.82rem' }}>
                          Sepolia Tx:{' '}
                          <a
                            href={att.etherscan}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono"
                          >
                            {att.tx_hash} ↗
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* New Attempt Upload Box */}
            <div className="card">
              <h2 className="card-title">Submit New Attempt for this File</h2>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Upload a corrected <code>declaration.json</code> + invoices, or load a predefined scenario:
              </p>

              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <select
                  value={selectedCaseId}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  style={{ flex: 1, minWidth: '260px' }}
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.badge})
                    </option>
                  ))}
                </select>

                <button
                  className="btn btn-secondary"
                  onClick={handleUploadAttempt}
                  disabled={uploadingAttempt}
                >
                  {uploadingAttempt ? 'Processing AI Pipeline...' : 'Upload Attempt from Scenario'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              No attempts have been submitted for this file yet.
            </p>
            <button className="btn btn-primary" onClick={handleUploadAttempt} disabled={uploadingAttempt}>
              {uploadingAttempt ? 'Processing...' : 'Upload Initial Attempt (Pick Scenario)'}
            </button>
          </div>
        )}

        {activeDoc && (
          <DocumentModal
            doc={activeDoc}
            extractions={currentAttempt?.extractions?.find((e) => e.doc_id === activeDoc.doc_id)}
            onClose={() => setActiveDoc(null)}
          />
        )}
      </div>
    );
  }

  // File Listing Screen (/exporter)
  return (
    <div>
      <RoleGuide
        step={1}
        role="Exporter (Turkish steel plant)"
        steps={['Open a file or create a new one', 'Pick a demo case and upload it as a new attempt', 'Fix or explain red findings until the file is green']}
        next={{ label: 'Send to verifier', to: '/verifier' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-main)' }}>
            Exporter Declarations
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Manage CBAM yearly emissions filings for steel installations and seal primary evidence on Sepolia.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowNewFileModal(true)}>
          + Create New File
        </button>
      </div>

      {loading && files.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Loading exporter files...
        </div>
      ) : error ? (
        <div style={{ padding: '1.5rem', background: '#fef2f2', color: '#991b1b', borderRadius: '8px' }}>
          {error}
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Plant Name</th>
                <th>Year</th>
                <th>Product & CN Code</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Workflow State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.file_key}>
                  <td>
                    <strong>{file.plant.name}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      ID: {file.plant.plant_id}
                    </div>
                  </td>
                  <td><strong>{file.year}</strong></td>
                  <td>
                    <div>{file.product.name}</div>
                    <code style={{ fontSize: '0.78rem' }}>CN {file.product.cn_code}</code>
                  </td>
                  <td>
                    <StatusBadge status={file.status} size="sm" />
                  </td>
                  <td>
                    <strong>{file.attempt_count}</strong> attempt(s)
                  </td>
                  <td>
                    <span style={{ fontSize: '0.85rem', textTransform: 'capitalize' }}>
                      {file.state.replace(/_/g, ' ')}
                    </span>
                    {file.passport_id && (
                      <span style={{ display: 'block', fontSize: '0.75rem', color: '#065f46' }}>
                        Passport #{file.passport_id}
                      </span>
                    )}
                  </td>
                  <td>
                    <Link
                      to={`/exporter/files/${file.file_key}`}
                      className="btn btn-secondary"
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }}
                    >
                      Open File →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Demo Scenarios Quick Pick Section */}
      <div className="card" style={{ marginTop: '2rem' }}>
        <h2 className="card-title">Available Demo Cases (Ground Truth Scenarios)</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {cases.map((c) => (
            <div key={c.id} style={{ border: '1px solid var(--border-color)', borderRadius: '6px', padding: '1rem', background: 'var(--bg-surface-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.name}</span>
                {c.badge && <span className="demo-data-badge">{c.badge}</span>}
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                {c.description}
              </p>
              <code style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Case ID: {c.id}</code>
            </div>
          ))}
        </div>
      </div>

      {/* Create File Modal */}
      {showNewFileModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          onClick={() => setShowNewFileModal(false)}
        >
          <div
            className="card"
            style={{ maxWidth: '500px', width: '100%', margin: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Create New Installation File</h2>
            <form onSubmit={handleCreateFile}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                  Plant Identifier
                </label>
                <input
                  type="text"
                  value={newPlantId}
                  onChange={(e) => setNewPlantId(e.target.value)}
                  style={{ width: '100%' }}
                  required
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                  Reporting Year
                </label>
                <input
                  type="number"
                  value={newYear}
                  onChange={(e) => setNewYear(Number(e.target.value))}
                  style={{ width: '100%' }}
                  required
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                  Product CN Code
                </label>
                <select
                  value={newCnCode}
                  onChange={(e) => setNewCnCode(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="72142000">72142000 — Concrete Reinforcing Bar (Rebar)</option>
                  <option value="72131000">72131000 — Wire Rod</option>
                  <option value="72071114">72071114 — Semi-finished Steel Billets</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowNewFileModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create File
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
