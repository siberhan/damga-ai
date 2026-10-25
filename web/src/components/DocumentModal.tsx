import React from 'react';
import type { DocumentMeta, DocumentExtraction } from '../types';

interface DocumentModalProps {
  doc: DocumentMeta;
  extractions?: DocumentExtraction;
  onClose: () => void;
}

export const DocumentModal: React.FC<DocumentModalProps> = ({ doc, extractions, onClose }) => {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: '750px',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          backgroundColor: '#fff',
          margin: 0,
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)' }}>
              Document: {doc.name || doc.doc_id}
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Type: <strong>{doc.type}</strong> | Period: <strong>{doc.period}</strong>
            </p>
          </div>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '0.3rem 0.6rem' }}>
            ✕ Close
          </button>
        </div>

        <div style={{ marginBottom: '1.25rem', background: 'var(--bg-surface-subtle)', padding: '0.75rem 1rem', borderRadius: '4px', fontSize: '0.82rem' }}>
          <div><strong>SHA-256 Digest:</strong> <code className="font-mono">{doc.sha256}</code></div>
          <div style={{ marginTop: '0.25rem' }}>
            <strong>Doc Endpoint:</strong> <a href={doc.url} target="_blank" rel="noopener noreferrer">{doc.url}</a>
          </div>
        </div>

        {extractions && extractions.fields.length > 0 ? (
          <div>
            <h4 style={{ fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Verbatim Extractions & Quotes
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {extractions.fields.map((f, i) => (
                <div key={i} style={{ border: '1px solid var(--border-color)', borderRadius: '6px', padding: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{f.key}</span>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Confidence: {(f.confidence * 100).toFixed(1)}% | Quote Check: <strong>{f.quote_check.toUpperCase()}</strong>
                    </span>
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.35rem' }}>
                    {f.value} {f.unit || ''}
                  </div>
                  <div className="evidence-quote" style={{ margin: '0.25rem 0' }}>
                    &ldquo;{f.quote}&rdquo;
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
            No extracted individual fields recorded for this document type (e.g. process flow or qualitative specification).
          </p>
        )}

        {extractions?.injection_screen && extractions.injection_screen.removed.length > 0 && (
          <div style={{ marginTop: '1.25rem', border: '1px solid #fed7aa', background: '#fff7ed', padding: '0.75rem', borderRadius: '6px' }}>
            <h4 style={{ fontSize: '0.9rem', color: '#9a3412', marginBottom: '0.35rem' }}>
              ⚠ Prompt Injection Screen Intercepts ({extractions.injection_screen.removed.length})
            </h4>
            {extractions.injection_screen.removed.map((item, idx) => (
              <div key={idx} style={{ fontSize: '0.85rem', color: '#7c2d12', marginTop: '0.25rem' }}>
                <code>{item.text}</code> (Reason: {item.reason})
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '1.5rem', textAlign: 'right' }}>
          <a
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none' }}
          >
            Open Raw PDF Stream ↗
          </a>
        </div>
      </div>
    </div>
  );
};
