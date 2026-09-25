import React from "react";

import DeepAnalysisPanel from "./DeepAnalysisPanel";
import AIWarningPanel from "./AIWarningPanel";
import AIConfidenceMeter from "./AIConfidenceMeter";
import AdvancedMomentumPanel from "./AdvancedMomentumPanel";

import "../styles/components.css";

const num = (v, fallback = 0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

export default function AICommandCenter({ match }) {
  if (!match) return null;

  const confidence =
    num(match.confidence_score) ||
    num(match.signal_score) ||
    num(match.ai_score);

  const finalDecision =
    match.final_decision ||
    match.master_decision_status ||
    match.live_entry_status ||
    "OBSERVE";

  const projection =
    match.deep_projection_bias ||
    "NEUTRAL";

  const intensity =
    match.live_intensity ||
    0;

  return (
    <section className="ai-command-center">
      <div className="ai-command-header glass-card">
        <div>
          <span className="ai-command-eyebrow">
            AI COMMAND CENTER
          </span>

          <h2>🤖 Núcleo de inteligencia táctica</h2>

          <p>
            Centro avanzado de lectura IA en tiempo
            real con validación táctica, momentum,
            riesgo y análisis profundo.
          </p>
        </div>

        <div className="ai-command-status-grid">
          <StatusBox
            label="DECISIÓN"
            value={finalDecision}
          />

          <StatusBox
            label="PROYECCIÓN"
            value={projection}
          />

          <StatusBox
            label="INTENSIDAD"
            value={`${Math.round(intensity)}%`}
          />
        </div>
      </div>

      <div className="ai-command-layout">
        <div className="ai-command-left">
          <AIConfidenceMeter
            value={confidence}
            title="Confianza operativa IA"
            subtitle="Lectura combinada del sistema"
          />

          <AIWarningPanel match={match} />
        </div>

        <div className="ai-command-right">
          <AdvancedMomentumPanel match={match} />

          <DeepAnalysisPanel match={match} />
        </div>
      </div>
    </section>
  );
}

function StatusBox({ label, value }) {
  return (
    <div className="ai-command-status-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
