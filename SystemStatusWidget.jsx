// src/v16/widgets/SystemStatusWidget.jsx

import React from "react";
import "../styles/components.css";

const safe = (v, fb = "N/A") => {
  if (v === undefined || v === null || v === "") return fb;
  return v;
};

const pct = (v) => {
  const n = Number(v);

  if (!Number.isFinite(n)) return "N/A";

  return `${n.toFixed(1)}%`;
};

export default function SystemStatusWidget({ status }) {
  if (!status) {
    return (
      <section className="system-status-widget glass-card">
        <h3>Estado del sistema</h3>

        <div className="system-loading">
          Esperando datos live...
        </div>
      </section>
    );
  }

  return (
    <section className="system-status-widget glass-card">
      <div className="widget-header">
        <h3>Estado del Sistema</h3>

        <div
          className={`widget-badge ${
            status.active ? "active" : "offline"
          }`}
        >
          {status.active ? "ONLINE" : "OFFLINE"}
        </div>
      </div>

      <div className="status-grid">
        <div className="status-item">
          <span>Señales activas</span>
          <strong>{safe(status.signalsActive, 0)}</strong>
        </div>

        <div className="status-item">
          <span>Precisión IA</span>
          <strong>{pct(status.precision)}</strong>
        </div>

        <div className="status-item">
          <span>ROI</span>
          <strong>{pct(status.roi)}</strong>
        </div>

        <div className="status-item">
          <span>Actualización</span>
          <strong>{safe(status.updatedAt)}</strong>
        </div>
      </div>
    </section>
  );
}
