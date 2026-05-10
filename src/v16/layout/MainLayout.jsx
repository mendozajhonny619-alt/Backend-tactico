// src/v16/layout/MainLayout.jsx

import React from "react";
import "../styles/dashboard.css";

export default function MainLayout({ children }) {
  return (
    <div className="main-layout">
      <header className="main-header">
        <div>
          <h1 className="logo">
            JHONNY <span>ELITE</span> V16
          </h1>

          <p className="subtitle">
            Lectura táctica y predicción contextual en tiempo real
          </p>
        </div>

        <div className="system-status">
          <div className="status-dot" />
          <span>SISTEMA ACTIVO</span>
        </div>
      </header>

      <main className="main-content">
        {children}
      </main>

      <footer className="main-footer">
        <span>
          Arquitectura inteligente • Panel premium • IA táctica live
        </span>
      </footer>
    </div>
  );
}
