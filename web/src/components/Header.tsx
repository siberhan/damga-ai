import React, { useEffect, useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { isDemoMode, subscribeDemoMode } from '../api';

export const Header: React.FC = () => {
  const [demo, setDemo] = useState(isDemoMode());

  useEffect(() => {
    return subscribeDemoMode((val) => setDemo(val));
  }, []);

  return (
    <header className="app-header">
      <div className="brand-section">
        <Link to="/" className="brand-logo">
          <span>Damga AI</span>
          <span className="badge-seal">CBAM Registry</span>
        </Link>
        {demo && (
          <span className="demo-data-badge" title="Running in simulated offline demo mode">
            ● Demo Data
          </span>
        )}
      </div>

      <nav className="nav-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Home
        </NavLink>
        <NavLink to="/exporter" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          1 · Exporter
        </NavLink>
        <NavLink to="/verifier" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          2 · Verifier
        </NavLink>
        <NavLink to="/passport/2" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          3 · Passport #2
        </NavLink>
      </nav>
    </header>
  );
};
