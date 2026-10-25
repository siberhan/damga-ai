import React from 'react';
import type { AttemptStatus, FlagLevel, PassportStatus } from '../types';

interface StatusBadgeProps {
  status: AttemptStatus | FlagLevel | PassportStatus | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md', showIcon = true }) => {
  const normalized = status.toLowerCase();

  let className = 'status-pill ';
  let icon = '';
  let label = status;

  switch (normalized) {
    case 'green':
    case 'active':
    case 'pass':
      className += 'status-green';
      icon = '✓';
      label = normalized === 'active' ? 'Active' : 'Green / Passed';
      break;
    case 'yellow':
    case 'warn':
      className += 'status-yellow';
      icon = '⚠';
      label = 'Yellow / Review';
      break;
    case 'red':
    case 'fail':
      className += 'status-red';
      icon = '✕';
      label = 'Red / Fraud Flag';
      break;
    case 'missing':
      className += 'status-missing';
      icon = '⊘';
      label = 'Missing / Incomplete';
      break;
    case 'info':
      className += 'status-info';
      icon = 'ℹ';
      label = 'Info / Screened';
      break;
    case 'revoked':
      className += 'status-red';
      icon = '⊘';
      label = 'Revoked';
      break;
    case 'disputed':
      className += 'status-yellow';
      icon = '⚖';
      label = 'Disputed';
      break;
    case 'superseded':
      className += 'status-missing';
      icon = '↺';
      label = 'Superseded';
      break;
    default:
      className += 'status-missing';
      icon = '•';
      label = status;
  }

  const sizeStyle: React.CSSProperties =
    size === 'sm'
      ? { fontSize: '0.72rem', padding: '2px 6px' }
      : size === 'lg'
      ? { fontSize: '0.95rem', padding: '0.35rem 0.85rem' }
      : {};

  return (
    <span className={className} style={sizeStyle} title={`Status: ${label}`}>
      {showIcon && <span aria-hidden="true" style={{ fontWeight: 800 }}>{icon}</span>}
      <span>{label}</span>
    </span>
  );
};
