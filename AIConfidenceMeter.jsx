import React from "react";
import "../styles/components.css";

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const clamp = (value) => Math.max(0, Math.min(100, num(value)));

const getTone = (value) => {
  const score = clamp(value);

  if (score >= 75) return "good";
  if (score >= 50) return "warn";
  return "danger";
};

const getLabel = (value) => {
  const score = clamp(value);

  if (score >= 85) return "PREMIUM";
  if (score >= 75) return "FUERTE";
  if (score >= 55) return "MEDIA";
  if (score >= 40) return "BAJA";
  return "RIESGO";
};

export default function AIConfidenceMeter({
  value = 0,
  title = "Confianza IA",
  subtitle = "Lectura combinada del sistema",
}) {
  const score = clamp(value);
  const tone = getTone(score);
  const label = getLabel(score);

  return (
    <section className="glass-card ai-confidence-meter">
      <div className="ai-confidence-head">
        <div>
          <span className="ai-confidence-eyebrow">MEDIDOR IA</span>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>

        <b className={tone}>{label}</b>
      </div>

      <div className="ai-confidence-body">
        <div
          className={`ai-confidence-ring ${tone}`}
          style={{
            "--ai-confidence": `${score}%`,
          }}
        >
          <strong>{score.toFixed(0)}%</strong>
          <span>{label}</span>
        </div>

        <div className="ai-confidence-scale">
          <div className="ai-confidence-track">
            <i style={{ width: `${score}%` }} />
          </div>

          <div className="ai-confidence-labels">
            <span>Riesgo</span>
            <span>Media</span>
            <span>Premium</span>
          </div>
        </div>
      </div>
    </section>
  );
            }
