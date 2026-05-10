// src/v16/widgets/EliteHeader.jsx

import React from "react";
import "../styles/components.css";

export default function EliteHeader() {
  return (
    <section className="elite-header glass-card">
      <div className="elite-header-overlay" />

      <div className="elite-header-content">
        <div>
          <h1 className="elite-title">
            JHONNY <span>ELITE</span> V16
          </h1>

          <p className="elite-subtitle">
            Lectura táctica y predicción contextual en tiempo real
          </p>
        </div>

        <div className="elite-status-live">
          <div className="live-dot" />
          <span>SISTEMA ACTIVO</span>
        </div>
      </div>
    </section>
  );
}
