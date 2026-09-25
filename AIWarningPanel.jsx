import React from "react";
import "../styles/components.css";

const safeArray = (value) => {
  if (Array.isArray(value)) return value;
  return [];
};

const getTone = (value) => {
  const text = String(value || "").toUpperCase();

  if (
    text.includes("DANGER") ||
    text.includes("ALTO") ||
    text.includes("FAKE") ||
    text.includes("NO_REENTRY") ||
    text.includes("AVOID") ||
    text.includes("LOW_DATA") ||
    text.includes("WEAK")
  ) {
    return "danger";
  }

  if (
    text.includes("WAIT") ||
    text.includes("OBSERVE") ||
    text.includes("CONFIRM") ||
    text.includes("MEDIO")
  ) {
    return "warn";
  }

  if (
    text.includes("GOOD") ||
    text.includes("VALID") ||
    text.includes("CLEAR") ||
    text.includes("STRONG")
  ) {
    return "good";
  }

  return "neutral";
};

const translateWarning = (warning) => {
  const value = String(warning || "").toUpperCase();

  const dictionary = {
    LOW_DATA_QUALITY: "Calidad de datos baja",
    LEAGUE_UNSTABLE: "Liga inestable",
    LEAGUE_DANGER_HIGH: "Liga con peligro histórico alto",
    FAKE_PRESSURE_WARNING: "Posible presión falsa",
    LOW_ACTIVITY_CONTEXT: "Contexto de baja actividad",
    LEAGUE_HISTORY_DANGER: "Historial peligroso en esta liga",
    LEAGUE_HISTORY_WEAK: "Historial débil en esta liga",
    MARKET_HISTORY_DANGER: "Mercado históricamente peligroso",
    MARKET_HISTORY_WEAK: "Mercado históricamente débil",
    CONFIDENCE_REDUCTION_STRONG: "Reducción fuerte de confianza",
    CONFIDENCE_REDUCTION_LIGHT: "Reducción ligera de confianza",
    CONFIDENCE_SUPPORT: "Historial apoya la señal",
    FAKE_PRESSURE_DETECTED: "Presión falsa detectada",
    PRESSURE_WITHOUT_DEPTH: "Presión sin profundidad",
    LATE_COOLING_DETECTED: "Enfriamiento tardío",
    MATCH_MAY_BE_RESOLVED: "Partido posiblemente resuelto",
    SCORE_OVEREXTENDED: "Marcador sobreextendido",
    NO_REENTRY: "No reingresar",
    AVOID: "Evitar entrada",
  };

  return dictionary[value] || value.replaceAll("_", " ");
};

const collectWarnings = (match) => {
  if (!match) return [];

  return [
    ...safeArray(match.adaptive_warning_flags),
    ...safeArray(match.sports_ai_risk_flags),
    ...safeArray(match.deep_tactical_alerts),
    ...safeArray(match.risk_warnings),
    ...safeArray(match.decision_warnings),
    ...safeArray(match.revalidation_warnings),
  ].filter(Boolean);
};

export default function AIWarningPanel({ match }) {
  if (!match) return null;

  const warnings = [...new Set(collectWarnings(match))];

  const riskLevel =
    match.risk_level ||
    match.riskLevel ||
    match.pre_match_risk_level ||
    match.retention_risk_label ||
    "MEDIO";

  const finalDecision =
    match.final_decision ||
    match.master_decision_status ||
    match.live_entry_status ||
    "OBSERVE";

  if (warnings.length === 0) {
    return (
      <section className="glass-card ai-warning-panel">
        <div className="ai-warning-header">
          <div>
            <span className="ai-warning-eyebrow">ALERTAS IA</span>
            <h3>🛡️ Control de riesgo</h3>
            <p>No se detectan alertas críticas en este momento.</p>
          </div>

          <div className="ai-warning-status good">
            <span>ESTADO</span>
            <strong>LIMPIO</strong>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="glass-card ai-warning-panel">
      <div className="ai-warning-header">
        <div>
          <span className="ai-warning-eyebrow">ALERTAS IA</span>
          <h3>⚠️ Riesgos detectados</h3>
          <p>Advertencias operativas generadas por el sistema inteligente.</p>
        </div>

        <div className={`ai-warning-status ${getTone(riskLevel)}`}>
          <span>RIESGO</span>
          <strong>{riskLevel}</strong>
        </div>
      </div>

      <div className="ai-warning-main">
        <div className={`ai-warning-decision ${getTone(finalDecision)}`}>
          <span>Decisión actual</span>
          <strong>{finalDecision}</strong>
        </div>

        <div className="ai-warning-list">
          {warnings.slice(0, 10).map((warning, index) => (
            <b className={getTone(warning)} key={`${warning}-${index}`}>
              {translateWarning(warning)}
            </b>
          ))}
        </div>
      </div>
    </section>
  );
}
