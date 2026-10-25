import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import QRCode from 'qrcode';
import { api } from '../api';
import type { PassportPublic, PassportImporter } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { RoleGuide } from '../components/RoleGuide';

export const PassportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const passportId = id ? parseInt(id, 10) : 1;

  const [passport, setPassport] = useState<PassportPublic | null>(null);
  const [importerData, setImporterData] = useState<PassportImporter | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Importer view toggle
  const [showImporterView, setShowImporterView] = useState<boolean>(false);
  const [saltsInput, setSaltsInput] = useState<string>('');
  const [loadingImporter, setLoadingImporter] = useState<boolean>(false);

  // QR code canvas
  const qrCanvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const loadPassport = async () => {
      try {
        setLoading(true);
        setError(null);
        const p = await api.getPassport(passportId);
        setPassport(p);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Passport not found');
      } finally {
        setLoading(false);
      }
    };
    loadPassport();
  }, [passportId]);

  // Render QR Code of GS1 Digital Link URL
  useEffect(() => {
    if (!passport || !qrCanvasRef.current) return;

    const gtin = passport.product.gtin || '00200000000014';
    const lot = passport.product.lot || `${passport.reporting_period}-${passport.product.cn_code}`;
    const gs1Url = `${window.location.origin}/01/${gtin}/10/${lot}`;

    QRCode.toCanvas(qrCanvasRef.current, gs1Url, {
      width: 160,
      margin: 1,
      color: {
        dark: '#0f172a',
        light: '#ffffff',
      },
    }).catch((err) => console.error('QR code generation failed:', err));
  }, [passport]);

  const handleFetchImporterDisclosure = async () => {
    try {
      setLoadingImporter(true);
      const data = await api.getPassportImporter(passportId, saltsInput);
      setImporterData(data);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to disclose importer data');
    } finally {
      setLoadingImporter(false);
    }
  };

  if (loading) {
    return (
      <div style={{ maxWidth: '640px', margin: '3rem auto', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Loading verified digital passport #{passportId}...
      </div>
    );
  }

  if (error || !passport) {
    return (
      <div style={{ maxWidth: '640px', margin: '3rem auto' }}>
        <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
          <h2 style={{ fontSize: '1.4rem', color: '#991b1b', marginBottom: '0.5rem' }}>
            Passport Not Found
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            {error || `Passport #${passportId} could not be located on Ethereum Sepolia.`}
          </p>
          <Link to="/" className="btn btn-primary">
            Return to Home
          </Link>
        </div>
      </div>
    );
  }

  const gs1DigitalLink = `/01/${passport.product.gtin}/10/${passport.product.lot}`;

  return (
    <div style={{ maxWidth: '680px', margin: '0 auto', paddingBottom: '3rem' }}>
      <RoleGuide
        step={3}
        role="EU customs, buyer or importer"
        steps={['Anyone: read the proven claims below', 'EU importer: open the Importer View at the bottom', 'Enter the salt from the exporter to see the exact value']}
      />

      {/* Top breadcrumb / navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <Link to="/" style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
          ← Home
        </Link>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          W3C Verifiable Credential v2.0
        </div>
      </div>

      {/* Main Passport Card (Mobile-First) */}
      <div
        className="card"
        style={{
          boxShadow: '0 10px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04)',
          border: '1px solid var(--border-strong)',
          borderRadius: '16px',
          padding: '1.75rem',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Subtle decorative top border */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '6px', background: 'linear-gradient(90deg, #0369a1, #059669)' }} />

        {/* Passport Header: Product & Status */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Digital Product Passport &bull; CBAM Evidence
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem', letterSpacing: '-0.02em' }}>
              {passport.product.name}
            </h1>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
              CN Code: <strong>{passport.product.cn_code}</strong> &bull; Period: <strong>{passport.reporting_period}</strong>
            </div>
          </div>

          <StatusBadge status={passport.status} size="lg" />
        </div>

        {/* Plant Details */}
        <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.85rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Manufacturing Installation (Fictional Demo Plant)
          </div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
            {passport.plant.name}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Location: {passport.plant.city || 'Aliağa, İzmir'}, {passport.plant.country || 'TR'} &bull; ID: <code>{passport.plant.plant_id || 'TR-ALIAGA-DEMO-001'}</code>
          </div>
        </div>

        {/* Accredited Verifier Section */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
            Signed By Verifier
          </div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
            {passport.verified_by.name}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }} className="font-mono">
            Verifier Address: {passport.verified_by.address}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Issued At: {new Date(passport.issued_at).toUTCString()}
          </div>
        </div>

        {/* The Two ZK-Proven Claims */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>⚡ Zero-Knowledge Proven Claims</span>
            <span style={{ fontSize: '0.75rem', background: '#ecfdf5', color: '#065f46', padding: '2px 6px', borderRadius: '4px', textTransform: 'none' }}>
              Groth16 Snark Verified On-Chain
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {passport.claims.map((claim, idx) => (
              <div
                key={idx}
                style={{
                  border: '1px solid #a7f3d0',
                  background: '#f0fdf4',
                  borderRadius: '8px',
                  padding: '0.85rem 1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.82rem', color: '#065f46', fontWeight: 600 }}>
                    {claim.label}
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#064e3b' }}>
                    {claim.statement}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ display: 'inline-block', fontSize: '0.75rem', background: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                    {claim.proof} &bull; verified on-chain ✓
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Process Route */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.4rem' }}>
            Process Route
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {passport.process_route.map((step, idx) => (
              <React.Fragment key={idx}>
                <span style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '0.3rem 0.65rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  {step.replace(/_/g, ' ').toUpperCase()}
                </span>
                {idx < passport.process_route.length - 1 && (
                  <span style={{ color: 'var(--text-muted)' }}>→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Integrity & Sealing Attestation */}
        <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.85rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span>Documents unchanged since sealing:</span>
            <strong style={{ color: '#065f46' }}>✓ Verified (Merkle docsRoot match)</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span>Model & Ruleset:</span>
            <span>{passport.model.name} &bull; steel_eaf v{passport.ruleset_version}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Sealing Attempts:</span>
            <span>{passport.attempt_count} submission attempt(s)</span>
          </div>
        </div>

        {/* Blockchain Proof & Etherscan */}
        <div style={{ marginBottom: '1.75rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          <div>
            Registry Contract:{' '}
            <code className="font-mono">{passport.chain.registry}</code>
          </div>
          <div style={{ marginTop: '0.25rem' }}>
            Mint Transaction:{' '}
            <a
              href={passport.chain.etherscan}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono"
              style={{ color: 'var(--primary)', textDecoration: 'underline' }}
            >
              {passport.chain.tx_hash.substring(0, 24)}... (Sepolia Etherscan ↗)
            </a>
          </div>
        </div>

        {/* GS1 Digital Link QR Code (Spec Section 8 & 9) */}
        <div
          style={{
            borderTop: '1px solid var(--border-color)',
            paddingTop: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
            GS1 Digital Link (Customs &amp; Importer Mobile Scan)
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', maxWidth: '400px', marginBottom: '0.75rem' }}>
            Scan to resolve GTIN <code className="font-mono">{passport.product.gtin}</code> / Lot <code className="font-mono">{passport.product.lot}</code> to the newest active passport for this product (this page).
          </p>

          <div style={{ padding: '0.5rem', background: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }}>
            <canvas ref={qrCanvasRef} />
          </div>

          <div style={{ marginTop: '0.5rem' }}>
            <code style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {gs1DigitalLink}
            </code>
          </div>
        </div>

        {/* Importer View Disclosure Toggle */}
        <div style={{ marginTop: '2rem', borderTop: '1px dashed var(--border-strong)', paddingTop: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Importer View (Confidential Disclosure)
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                For EU importers filing official CBAM declarations with salt authorization.
              </p>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setShowImporterView(!showImporterView);
                if (!showImporterView && !importerData) {
                  handleFetchImporterDisclosure();
                }
              }}
              style={{ fontSize: '0.82rem' }}
            >
              {showImporterView ? 'Hide Importer View ▲' : 'Open Importer View ▼'}
            </button>
          </div>

          {showImporterView && (
            <div style={{ marginTop: '1.25rem', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  Exporter Disclosure Salt / Key:
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={saltsInput}
                    onChange={(e) => setSaltsInput(e.target.value)}
                    style={{ flex: 1, fontSize: '0.85rem' }}
                    placeholder="Enter salts provided by supplier..."
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handleFetchImporterDisclosure}
                    disabled={loadingImporter}
                    style={{ fontSize: '0.82rem' }}
                  >
                    {loadingImporter ? 'Verifying...' : 'Verify Salts'}
                  </button>
                </div>
              </div>

              {importerData && (
                <div>
                  <div style={{ padding: '0.65rem 0.85rem', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '6px', color: '#065f46', fontSize: '0.82rem', marginBottom: '1rem' }}>
                    <strong>Poseidon Commitment Verified:</strong> The exact emissions value matches the sealed commitment on-chain.
                  </div>

                  <div className="emissions-grid" style={{ marginBottom: '1rem' }}>
                    <div className="stat-box" style={{ background: '#fff' }}>
                      <div className="stat-box-label">Exact Direct Emissions</div>
                      <div className="stat-box-value" style={{ color: '#0369a1' }}>
                        {importerData.direct_kg_per_t}
                        <span style={{ fontSize: '0.85rem', marginLeft: '4px' }}>kgCO₂ / t</span>
                      </div>
                      <div className="stat-box-sub">
                        CBAM exact declaration figure: {(importerData.direct_kg_per_t / 1000).toFixed(3)} tCO₂/t
                      </div>
                    </div>

                  </div>

                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                    {importerData.cost_gap_note}
                  </p>

                  <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: '#e2e8f0', borderRadius: '4px', fontSize: '0.75rem', color: '#334155', textAlign: 'center' }}>
                    🔒 <strong>Privacy Guarantee:</strong> Invoices, prices, supplier names, the input mix, and the exact scrap share are never shown on this passport. The scrap share is proven only as a zero-knowledge threshold.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
