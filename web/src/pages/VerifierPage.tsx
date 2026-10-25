import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api';
import type { FileSummary, FileDetail, Attempt, DocumentMeta } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { DocumentModal } from '../components/DocumentModal';
import { RoleGuide } from '../components/RoleGuide';

export const VerifierPage: React.FC = () => {
  const { fileKey } = useParams<{ fileKey?: string }>();

  const [queue, setQueue] = useState<FileSummary[]>([]);
  const [activeFile, setActiveFile] = useState<FileDetail | null>(null);
  const [selectedAttemptIndex, setSelectedAttemptIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Verifier resolution inputs
  const [redResolutions, setRedResolutions] = useState<Record<string, string>>({});
  const [yellowChecked, setYellowChecked] = useState<string[]>([]);
  const [savingResolutions, setSavingResolutions] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Sign & Issue Passport state
  const [signing, setSigning] = useState<boolean>(false);
  const [signingMethod, setSigningMethod] = useState<'metamask' | 'demo' | null>(null);
  const [mintResult, setMintResult] = useState<{ passport_id: number; tx_hash: string | null } | null>(null);

  // Document modal
  const [activeDoc, setActiveDoc] = useState<DocumentMeta | null>(null);

  const loadQueue = async () => {
    try {
      const q = await api.getVerifierQueue();
      setQueue(q);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load verifier queue');
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

        // Prepopulate red resolutions and yellow checked from attempt
        const reds: Record<string, string> = {};
        const yellows: string[] = [];
        for (const f of detail.attempts[lastIdx].flags) {
          if (f.level === 'red' && f.resolution) {
            reds[f.id] = f.resolution;
          }
          if (f.level === 'yellow' && f.checked) {
            yellows.push(f.id);
          }
        }
        setRedResolutions(reds);
        setYellowChecked(yellows);
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
        const q = await api.getVerifierQueue();
        if (!ignore) setQueue(q);
      } catch (err: unknown) {
        if (!ignore) setError(err instanceof Error ? err.message : 'Failed to load queue');
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
              const reds: Record<string, string> = {};
              const yellows: string[] = [];
              for (const f of detail.attempts[lastIdx].flags) {
                if (f.level === 'red' && f.resolution) reds[f.id] = f.resolution;
                if (f.level === 'yellow' && f.checked) yellows.push(f.id);
              }
              setRedResolutions(reds);
              setYellowChecked(yellows);
            }
          }
        } catch (err: unknown) {
          if (!ignore) setError(err instanceof Error ? err.message : 'Failed to load details');
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

  const handleSaveResolutions = async () => {
    if (!activeFile) return;
    try {
      setSavingResolutions(true);
      setSaveSuccessMsg(null);
      await api.saveResolutions(
        activeFile.file_key,
        selectedAttemptIndex,
        redResolutions,
        yellowChecked
      );
      setSaveSuccessMsg('Auditor resolutions updated.');
      setTimeout(() => setSaveSuccessMsg(null), 3000);
      await loadFileDetail(activeFile.file_key);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to save resolutions');
    } finally {
      setSavingResolutions(false);
    }
  };

  const currentAttempt: Attempt | undefined = activeFile?.attempts[selectedAttemptIndex];

  // Validation logic for the Sign button:
  // "The Sign button stays disabled while any red is unresolved, any yellow unchecked, or evidence missing, and says why"
  const getSigningDisabledReasons = (): string[] => {
    if (!currentAttempt) return ['No attempt selected'];
    const reasons: string[] = [];
    if (currentAttempt.legacy) return [currentAttempt.note || 'Old attempt; only its on-chain record is kept'];

    if (currentAttempt.status === 'missing' || currentAttempt.counts.missing > 0) {
      reasons.push('Mandatory evidence is incomplete (missing required monthly or annual documents).');
    }

    const openReds = currentAttempt.flags.filter(
      (f) => f.level === 'red' && !(redResolutions[f.id] || f.resolution)
    );
    if (openReds.length > 0) {
      reasons.push(
        `${openReds.length} Red fraud/discrepancy flag(s) must have an official auditor resolution reason entered.`
      );
    }

    const uncheckedYellows = currentAttempt.flags.filter(
      (f) => f.level === 'yellow' && !(yellowChecked.includes(f.id) || f.checked)
    );
    if (uncheckedYellows.length > 0) {
      reasons.push(
        `${uncheckedYellows.length} Yellow advisory notice(s) must be reviewed and marked checked.`
      );
    }

    return reasons;
  };

  const disabledReasons = getSigningDisabledReasons();
  const canSign = disabledReasons.length === 0;

  const handleSignMetaMask = async () => {
    if (!activeFile || !canSign) return;
    try {
      setSigning(true);
      setSigningMethod('metamask');

      const ethereum = (window as unknown as { ethereum?: { request: (args: unknown) => Promise<unknown> } }).ethereum;
      if (!ethereum) {
        throw new Error('MetaMask or Web3 browser extension not detected. Please install MetaMask or use the Demo Verifier Key.');
      }

      const accounts = (await ethereum.request({
        method: 'eth_requestAccounts',
      })) as string[];
      const verifierAddr = accounts[0];

      const typedData = await api.getTypedData(activeFile.file_key, selectedAttemptIndex);

      const signature = (await ethereum.request({
        method: 'eth_signTypedData_v4',
        params: [verifierAddr, JSON.stringify(typedData)],
      })) as string;

      const result = await api.verifyAttempt(activeFile.file_key, selectedAttemptIndex, {
        signature,
      });
      setMintResult(result);
      await loadFileDetail(activeFile.file_key);
      await loadQueue();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'MetaMask signing failed');
    } finally {
      setSigning(false);
      setSigningMethod(null);
    }
  };

  const handleSignDemo = async () => {
    if (!activeFile || !canSign) return;
    try {
      setSigning(true);
      setSigningMethod('demo');

      const result = await api.verifyAttempt(activeFile.file_key, selectedAttemptIndex, {
        demo_signer: true,
      });
      setMintResult(result);
      await loadFileDetail(activeFile.file_key);
      await loadQueue();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setSigning(false);
      setSigningMethod(null);
    }
  };

  // If viewing a file from queue
  if (fileKey && activeFile) {
    return (
      <div>
        <RoleGuide
          step={2}
          role="Accredited verifier"
          steps={['Open a file from the queue', 'Check every attempt, red ones included', 'Resolve the findings and sign to issue the passport']}
          next={{ label: 'See the passport', to: '/passport/2' }}
        />
        <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link to="/verifier" style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            ← Back to Verifier Queue
          </Link>
          <span style={{ color: 'var(--border-strong)' }}>/</span>
          <span className="font-mono" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Audit File: {activeFile.file_key.substring(0, 16)}...
          </span>
        </div>

        {/* Verifier Header Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  {activeFile.plant.name}
                </h1>
                <StatusBadge status={currentAttempt?.status || 'missing'} size="md" />
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
                Verifier: <strong>Demo Verification GmbH (fictional)</strong> &bull; Product:{' '}
                <strong>{activeFile.product.name}</strong> (CN {activeFile.product.cn_code}) &bull; Period:{' '}
                <strong>{activeFile.year}</strong>
              </p>
            </div>

            {activeFile.passport_id && (
              <Link to={`/passport/${activeFile.passport_id}`} className="btn btn-primary">
                View Issued Passport #{activeFile.passport_id} ↗
              </Link>
            )}
          </div>

          {/* Timeline representation: "3 attempts, 2 failed; the first declared 0 t pig iron" */}
          <div style={{ marginTop: '1.25rem', background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Attempt History Timeline:
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
              {activeFile.history_summary}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
              {activeFile.attempts.map((att, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedAttemptIndex(idx);
                    const reds: Record<string, string> = {};
                    const yellows: string[] = [];
                    for (const f of att.flags) {
                      if (f.level === 'red' && f.resolution) reds[f.id] = f.resolution;
                      if (f.level === 'yellow' && f.checked) yellows.push(f.id);
                    }
                    setRedResolutions(reds);
                    setYellowChecked(yellows);
                  }}
                  className={`btn ${selectedAttemptIndex === idx ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.25rem 0.65rem', fontSize: '0.8rem' }}
                >
                  Attempt {idx + 1} ({att.legacy ? 'OLD SET' : att.status.toUpperCase()})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sealed Document Evidence Section */}
        {currentAttempt && (
          <div className="card">
            <h2 className="card-title">
              <span>Sealed Primary Documents</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
                DocsRoot: <code className="font-mono">{currentAttempt.docs_root.substring(0, 16)}...</code>
              </span>
            </h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              {currentAttempt.legacy
                ? currentAttempt.note
                : 'The verifier reviews the original invoices, meter records, and weighbridge slips sealed into the attempt Merkle root.'}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
              {currentAttempt.documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    background: 'var(--bg-surface-subtle)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{doc.name || doc.doc_id}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      Type: {doc.type} &bull; Period: {doc.period}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }} className="font-mono">
                      {doc.sha256.substring(0, 20)}...
                    </div>
                  </div>
                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', width: '100%' }}
                      onClick={() => setActiveDoc(doc)}
                    >
                      Open PDF Evidence ↗
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flag Review & Explanation Panel */}
        {currentAttempt && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  Auditor Flag Review & Explanation Panel
                </h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Detailed rule diagnostics, physical formula values, verbatim quotes, and confidence scores.
                </p>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleSaveResolutions}
                disabled={savingResolutions}
              >
                {savingResolutions ? 'Saving...' : 'Save Auditor Resolutions'}
              </button>
            </div>

            {saveSuccessMsg && (
              <div style={{ padding: '0.65rem 1rem', background: '#ecfdf5', color: '#065f46', borderRadius: '4px', marginBottom: '1rem', fontSize: '0.85rem', fontWeight: 600 }}>
                ✓ {saveSuccessMsg}
              </div>
            )}

            {currentAttempt.flags.length === 0 ? (
              <div style={{ padding: '1.5rem', background: '#ecfdf5', borderRadius: '6px', color: '#065f46', fontSize: '0.9rem' }}>
                ✓ 0 active flags. All inputs, gas bills, and production balances verified without variance.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {currentAttempt.flags.map((flag) => (
                  <div
                    key={flag.id}
                    className={`flag-card level-${flag.level}`}
                    style={{ marginBottom: 0 }}
                  >
                    <div className="flag-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <StatusBadge status={flag.level} size="sm" />
                        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Rule: {flag.rule}</span>
                        <code style={{ fontSize: '0.75rem' }}>ID: {flag.id}</code>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span className="flag-source-badge">source: {flag.source}</span>
                        {flag.confidence && (
                          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                            Confidence: <strong>{(flag.confidence * 100).toFixed(1)}%</strong>
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)', margin: '0.35rem 0' }}>
                      {flag.message}
                    </div>

                    {/* Explanation Panel: "why this was flagged": rule, formula/values, quote, confidence */}
                    <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', padding: '0.85rem', borderRadius: '6px', margin: '0.75rem 0', fontSize: '0.85rem' }}>
                      <div style={{ fontWeight: 600, color: 'var(--primary)', marginBottom: '0.35rem' }}>
                        Diagnostic Explanation Panel:
                      </div>

                      {flag.values && (
                        <div style={{ marginBottom: '0.4rem' }}>
                          <strong>Checked Formula / Values:</strong>{' '}
                          <code className="font-mono" style={{ background: '#e2e8f0', padding: '2px 4px', borderRadius: '3px' }}>
                            {JSON.stringify(flag.values)}
                          </code>
                        </div>
                      )}

                      {flag.evidence && flag.evidence.length > 0 && (
                        <div>
                          <strong>Verbatim Quote:</strong>
                          {flag.evidence.map((ev, i) => (
                            <div key={i} className="evidence-quote" style={{ margin: '4px 0', fontSize: '0.8rem' }}>
                              [{ev.doc_id}] &ldquo;{ev.quote}&rdquo;
                            </div>
                          ))}
                        </div>
                      )}

                      {flag.ai_explanation && (
                        <div style={{ marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                          <strong>AI Rule Analysis:</strong> {flag.ai_explanation}
                        </div>
                      )}

                      {flag.exporter_explanation && (
                        <div style={{ marginTop: '0.5rem', padding: '0.5rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '4px', color: '#92400e' }}>
                          <strong>Exporter Stated Explanation:</strong> {flag.exporter_explanation}
                        </div>
                      )}
                    </div>

                    {/* Resolution Controls for Auditor */}
                    {flag.level === 'red' && (
                      <div style={{ marginTop: '0.75rem', background: '#fef2f2', border: '1px solid #fecaca', padding: '0.85rem', borderRadius: '6px' }}>
                        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: '#991b1b', marginBottom: '0.35rem' }}>
                          Auditor Resolution Reason (Required to Sign):
                        </label>
                        <p style={{ fontSize: '0.78rem', color: '#7f1d1d', marginBottom: '0.5rem' }}>
                          Red fraud or discrepancy flags require an explicit written audit determination before the cryptographic signature can be computed.
                        </p>
                        <input
                          type="text"
                          value={redResolutions[flag.id] ?? flag.resolution ?? ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            setRedResolutions((prev) => ({ ...prev, [flag.id]: val }));
                          }}
                          placeholder="e.g. Corrected via supplementary invoice batch INV-PIG-012b and physically inspected on-site."
                          style={{ width: '100%', fontSize: '0.88rem' }}
                        />
                      </div>
                    )}

                    {flag.level === 'yellow' && (
                      <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.65rem', background: '#fffbeb', border: '1px solid #fde68a', padding: '0.65rem 0.85rem', borderRadius: '6px' }}>
                        <input
                          type="checkbox"
                          id={`check-${flag.id}`}
                          checked={yellowChecked.includes(flag.id) || !!flag.checked}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            if (checked) {
                              setYellowChecked((prev) => [...prev, flag.id]);
                            } else {
                              setYellowChecked((prev) => prev.filter((id) => id !== flag.id));
                            }
                          }}
                          style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                        />
                        <label htmlFor={`check-${flag.id}`} style={{ fontSize: '0.88rem', fontWeight: 600, color: '#92400e', cursor: 'pointer' }}>
                          Mark as Checked &amp; Verified (Auditor has reviewed exporter operational explanation)
                        </label>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Verifier EIP-712 Sign & Mint Section */}
        {currentAttempt && (
          <div className="card" style={{ border: canSign ? '2px solid #059669' : '1px solid var(--border-color)' }}>
            <h2 className="card-title">
              <span>Cryptographic Attestation &amp; ZK Passport Minting</span>
              {canSign && <span style={{ color: '#059669', fontSize: '0.85rem' }}>✓ Ready for Verifier Signature</span>}
            </h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              Signing certifies the mass-balance calculation, document hashes, and Groth16 zero-knowledge proofs under EIP-712.
            </p>

            {/* If Sign is disabled, explain exactly why */}
            {!canSign && (
              <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '1rem', borderRadius: '6px', marginBottom: '1.25rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: '#991b1b', fontWeight: 700, marginBottom: '0.4rem' }}>
                  ⊘ Sign &amp; Issue Passport is Disabled
                </h4>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#7f1d1d' }}>
                  {disabledReasons.map((reason, idx) => (
                    <li key={idx} style={{ marginBottom: '0.25rem' }}>
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Signature Actions */}
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={handleSignMetaMask}
                disabled={!canSign || signing}
                style={{ padding: '0.65rem 1.25rem' }}
              >
                {signing && signingMethod === 'metamask' ? 'Waiting for MetaMask...' : 'Sign with MetaMask (EIP-712)'}
              </button>

              <button
                className="btn btn-secondary"
                onClick={handleSignDemo}
                disabled={!canSign || signing}
                style={{ padding: '0.65rem 1.25rem' }}
              >
                {signing && signingMethod === 'demo' ? 'Signing with Relayer...' : 'Sign with demo verifier key (fictional verifier)'}
              </button>
            </div>

            {/* Mint Success Modal / Feedback */}
            {mintResult && (
              <div style={{ marginTop: '1.5rem', background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '1.25rem', borderRadius: '6px' }}>
                <h3 style={{ fontSize: '1.1rem', color: '#065f46', fontWeight: 700, marginBottom: '0.35rem' }}>
                  ✓ Passport #{mintResult.passport_id} {mintResult.tx_hash ? 'Successfully Minted On-Chain!' : 'Issued Locally'}
                </h3>
                <p style={{ fontSize: '0.88rem', color: '#047857', marginBottom: '0.75rem', wordBreak: 'break-all' }}>
                  {mintResult.tx_hash ? (
                    <>Transaction sealed on Ethereum Sepolia: <code className="font-mono">{mintResult.tx_hash}</code></>
                  ) : (
                    <>Offline mode: no registry is set, so nothing was sent to Sepolia.</>
                  )}
                </p>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <Link to={`/passport/${mintResult.passport_id}`} className="btn btn-primary">
                    Open Public Passport #{mintResult.passport_id} →
                  </Link>
                  {mintResult.tx_hash && (
                    <a
                      href={`https://sepolia.etherscan.io/tx/${mintResult.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                    >
                      View on Etherscan ↗
                    </a>
                  )}
                </div>
              </div>
            )}
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

  // Verifier Queue Screen (/verifier)
  return (
    <div>
      <RoleGuide
        step={2}
        role="Accredited verifier"
        steps={['Open a file from the queue', 'Check every attempt, red ones included', 'Resolve the findings and sign to issue the passport']}
        next={{ label: 'See the passport', to: '/passport/2' }}
      />
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-main)' }}>
          Verifier Audit Queue
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Authorized verifier queue for <strong>Demo Verification GmbH (fictional)</strong>. Inspect primary documents, resolve flags, and issue passports.
        </p>
      </div>

      {loading && queue.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Loading verifier queue...
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
                <th>Product</th>
                <th>Current Status</th>
                <th>Attempts</th>
                <th>Workflow State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => (
                <tr key={item.file_key}>
                  <td>
                    <strong>{item.plant.name}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      ID: {item.plant.plant_id}
                    </div>
                  </td>
                  <td><strong>{item.year}</strong></td>
                  <td>
                    {item.product.name}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      CN {item.product.cn_code}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={item.status} size="sm" />
                  </td>
                  <td>
                    <strong>{item.attempt_count}</strong> attempt(s)
                  </td>
                  <td>
                    <span style={{ fontSize: '0.85rem', textTransform: 'capitalize' }}>
                      {item.state.replace(/_/g, ' ')}
                    </span>
                    {item.passport_id && (
                      <span style={{ display: 'block', fontSize: '0.75rem', color: '#065f46' }}>
                        Passport #{item.passport_id}
                      </span>
                    )}
                  </td>
                  <td>
                    <Link
                      to={`/verifier/files/${item.file_key}`}
                      className="btn btn-secondary"
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }}
                    >
                      Audit File →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
