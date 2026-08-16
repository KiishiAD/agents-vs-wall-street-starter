import React from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import Workspaces from "./pages/Workspaces.jsx";
import Company from "./pages/Company.jsx";
import Signal from "./pages/Signal.jsx";
import Run from "./pages/Run.jsx";
import { LiveIndicator } from "./ui.jsx";

export default function App() {
  const loc = useLocation();
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark">◈</span> CENTURION
          <span className="brand-sub">forecasting agents</span>
        </Link>
        <div className="topbar-right">
          <LiveIndicator />
        </div>
      </header>
      <main key={loc.pathname}>
        <Routes>
          <Route path="/" element={<Workspaces />} />
          <Route path="/c/:slug" element={<Company />} />
          <Route path="/c/:slug/signals/:signalId" element={<Signal />} />
          <Route path="/c/:slug/runs/:runId" element={<Run />} />
        </Routes>
      </main>
    </div>
  );
}
