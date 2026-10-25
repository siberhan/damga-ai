import React from 'react';
import { Link } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  return (
    <div style={{ maxWidth: '960px', margin: '2rem auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2.4rem', fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text-main)', marginBottom: '1rem' }}>
          Damga AI
        </h1>
        <p style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', maxWidth: '720px', margin: '0 auto', lineHeight: '1.6' }}>
          Cryptographic evidence-to-passport pipeline verifying Turkish scrap EAF steel declarations with European AI models, deterministic rules, and Zero-Knowledge proofs for EU CBAM compliance.
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.5rem',
        }}
      >
        {/* Card 1: Exporter */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'inline-block', padding: '0.25rem 0.5rem', background: 'var(--primary-subtle)', color: 'var(--primary)', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              Screen 1
            </div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Exporter Portal
            </h2>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '1.5rem' }}>
              Upload declarations and evidence documents. Review AI extractions, verbatim quote checks, mass balance flags, direct emissions vs EU defaults, and submit to your accredited verifier.
            </p>
          </div>
          <Link to="/exporter" className="btn btn-primary" style={{ textDecoration: 'none', width: '100%' }}>
            Open Exporter Portal →
          </Link>
        </div>

        {/* Card 2: Verifier */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'inline-block', padding: '0.25rem 0.5rem', background: '#fef3c7', color: '#92400e', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              Screen 2
            </div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Verifier Workspace
            </h2>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '1.5rem' }}>
              Auditor review queue. Inspect sealed PDF evidence, evaluate AI rules, record resolutions for red flags, check yellow notices, and sign the attestation with MetaMask or demo key.
            </p>
          </div>
          <Link to="/verifier" className="btn btn-primary" style={{ textDecoration: 'none', width: '100%' }}>
            Open Verifier Workspace →
          </Link>
        </div>

        {/* Card 3: Passport */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'inline-block', padding: '0.25rem 0.5rem', background: '#ecfdf5', color: '#065f46', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              Screen 3
            </div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Public Digital Passport
            </h2>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '1.5rem' }}>
              Mobile-first public passport. Verifies Zero-Knowledge claims (direct emissions limit and scrap share), GS1 Digital Link QR, and provides salt-disclosed importer view without exposing supplier secrets.
            </p>
          </div>
          <Link to="/passport/1" className="btn btn-primary" style={{ textDecoration: 'none', width: '100%' }}>
            View Sample Passport →
          </Link>
        </div>
      </div>

      <div style={{ marginTop: '3.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
        <div>
          Demo Plant: <strong>Aliağa Demo Steel Works (fictional)</strong> &bull; Verifier: <strong>Demo Verification GmbH (fictional)</strong>
        </div>
        <div>
          IEEE ClimateChain Global Hackathon 2026 &bull; Sepolia Testnet
        </div>
      </div>
    </div>
  );
};
