import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { Header } from './components/Header';
import { ExporterPage } from './pages/ExporterPage';
import { VerifierPage } from './pages/VerifierPage';
import { PassportPage } from './pages/PassportPage';
import { initApiClient } from './api';

// GS1 Digital Link resolver redirect helper
const GS1Resolver: React.FC = () => {
  const { gtin, lot } = useParams<{ gtin: string; lot: string }>();
  console.log(`Resolving GS1 Digital Link: GTIN=${gtin}, LOT=${lot}`);
  // In demo setup, GTIN 00200000000014 maps to passport #1
  return <Navigate to="/passport/1" replace />;
};

export const App: React.FC = () => {
  useEffect(() => {
    initApiClient();
  }, []);

  return (
    <BrowserRouter>
      <div className="app-container">
        <Header />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ScrollLanding />} />
            <Route path="/exporter" element={<ExporterPage />} />
            <Route path="/exporter/files/:fileKey" element={<ExporterPage />} />
            <Route path="/verifier" element={<VerifierPage />} />
            <Route path="/verifier/files/:fileKey" element={<VerifierPage />} />
            <Route path="/passport/:id" element={<PassportPage />} />
            {/* GS1 Digital Link route */}
            <Route path="/01/:gtin/10/:lot" element={<GS1Resolver />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

// The scroll landing page is plain HTML (web/public/landing), served by the backend at "/"
function ScrollLanding() {
  window.location.replace('/landing/');
  return null;
}

export default App;
