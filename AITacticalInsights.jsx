import React from "react";
import "../styles/components.css";

const safe = (value, fallback = "N/A") => {
  if (value === undefined || value === null || value === "") return fallback;
  return value;
};

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const pct = (value) => `${num(value).toFixed(0)}%`;

const getTone = (value) => {
  const text = String(value || "").toUpperCase();

  if (
    text.includes("OVER") ||
    text.includes("ACTIVE") ||
    text.includes("ALTO") ||
    text.includes("RISING") ||
    text.includes("VALID")
  ) {
    return "good";
  }

  if (
    text.includes("UNDER") ||
    text.includes("RETENTION") ||
    text.includes("BAJO") ||
    text.includes("FALLING") ||
    text.includes("MUERTO")
  ) {
    return "warn";
  }

  if (
    text.includes("CHAOS") ||
    text.includes("VOLATILE") ||
    text.includes("FAKE") ||
    text.includes("NO_REENTRY") ||
    text.includes("DANGER")
  ) {
    return "danger";
  }

  return "neutral";
};

const translateAlert = (alert) => {
  const value = String(alert || "").toUpperCase();

  const dictionary = {
    RED_ALERT_ACTIVE: "Alerta roja activa",
    LATE_REACTIVATION: "Reactivación tardía",
    CHAOS_MODE_ACTIVE: "Modo caos activo",
    FAKE_PRESSURE_DETECTED: "Presión falsa detectada",
    PRESSURE_WITHOUT_DEPTH: "Presión sin profundidad",
    RECENT_RED_CARD_VOLATILITY: "Volatilidad por roja reciente",
    RECENT_SUBSTITUTIONS_TACTICAL_SHIFT: "Cambio táctico por sustituciones",
    LATE_PRESSURE_STILL_ACTIVE: "Presión tardía activa",
    LATE_COOLING_DETECTED: "Enfriamiento tardío",
    MATCH_MAY_BE_RESOLVED: "Partido posiblemente resuelto",
    SCORE_OVEREXTENDED: "Marcador sobreextendido",
    DOMINANT_SIDE_ALIGNED: "Dominio alineado",
    RECENT_SHOT_ON_TARGET: "Remate reciente al arco",
    RECENT_CORNER_PRESSURE: "Presión reciente por córner",
    DANGEROUS_ATTACKS_ACCUMULATING: "Ataques peligrosos acumulados",
    LOW_ACTIVITY_CONTEXT: "Contexto de baja actividad",
  };

  return dictionary[value] || value.replaceAll("_", " ");
};

export default function AITacticalInsights({ match }) {
  if (!match) return null;

  const projectionBias =
    match.deep_projection_bias ||
    match.deepProjectionBias ||
    "NEUTRAL";

  const projectionConfidence = num(
    match.deep_projection_confidence ??
      match.deepProjectionConfidence
  );

  const projectionWindow =
    match.deep_projection_window ||
    match.deepProjectionWindow ||
    "SIN_VENTANA";

  const lateGoalRisk =
    match.late_goal_risk ||
    match.lateGoalRisk ||
    "NORMAL";

  const retentionRisk =
    match.retention_risk_label ||
    match.retentionRiskLabel ||
    "BAJO";

  const signalLife =
    match.deep_signal_life_status ||
    match.signal_life_status ||
    match.signalLifeStatus ||
    "UNKNOWN";

  const pressureTrend =
    match.deep_pressure_trend ||
    match.pressure_trend ||
    match.pressureTrend ||
    "UNKNOWN";

  const rhythmTrend =
    match.deep_rhythm_trend ||
    match.rhythm_trend ||
    match.rhythmTrend ||
    "UNKNOWN";

  const goalThreatTrend =
    match.deep_goal_threat_trend ||
    match.goal_threat_trend ||
    match.goalThreatTrend ||
    "UNKNOWN";

  const summary =
    match.deep_analysis_summary ||
    match.deepAnalysisSummary ||
    "Sin lectura profunda disponible.";

  const alerts =
    match.deep_tactical_alerts ||
    match.deepTacticalAlerts ||
    [];

  return (
    <section className="glass-card ai-tactical-insights">
      <div className="ai-tactical-header">
        <div>
          <span className="ai-tactical-eyebrow">LECTURA TÁCTICA IA</span>
          <h3>🧩 Inteligencia profunda del partido</h3>
          <p>
            Detección de presión, retención, riesgo tardío, tendencia y vida de
            la señal.
          </p>
        </div>

        <div className={`ai-tactical-main ${getTone(projectionBias)}`}>
          <span>PROYECCIÓN</span>
          <strong>{projectionBias}</strong>
          <small>{pct(projectionConfidence)}</small>
        </div>
      </div>

      <div className="ai-tactical-kpis">
        <TacticalKpi
          label="Ventana"
          value={projectionWindow}
          tone={getTone(projectionWindow)}
        />

        <TacticalKpi
          label="Gol tardío"
          value={lateGoalRisk}
          tone={getTone(lateGoalRisk)}
        />

        <TacticalKpi
          label="Retención"
          value={retentionRisk}
          tone={getTone(retentionRisk)}
        />

        <TacticalKpi
          label="Vida señal"
          value={signalLife}
          tone={getTone(signalLife)}
        />

        <TacticalKpi
          label="Presión"
          value={pressureTrend}
          tone={getTone(pressureTrend)}
        />

        <TacticalKpi
          label="Amenaza gol"
          value={goalThreatTrend}
          tone={getTone(goalThreatTrend)}
        />
      </div>

      <div className="ai-tactical-summary">
        <span>Resumen táctico</span>
        <p>{summary}</p>
      </div>

      <div className="ai-tactical-trends">
        <TrendRow label="Presión" value={pressureTrend} />
        <TrendRow label="Ritmo" value={rhythmTrend} />
        <TrendRow label="Amenaza de gol" value={goalThreatTrend} />
      </div>

      {Array.isArray(alerts) && alerts.length > 0 && (
        <div className="ai-tactical-alerts">
          <span>Alertas tácticas</span>

          <div>
            {alerts.slice(0, 8).map((alert, index) => (
              <b className={getTone(alert)} key={`${alert}-${index}`}>
                {translateAlert(alert)}
              </b>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function TacticalKpi({ label, value, tone = "neutral" }) {
  return (
    <div className={`ai-tactical-kpi ${tone}`}>
      <span>{label}</span>
      <strong>{safe(value)}</strong>
    </div>
  );
}

function TrendRow({ label, value }) {
  const tone = getTone(value);

  return (
    <div className={`ai-tactical-trend ${tone}`}>
      <span>{label}</span>
      <strong>{safe(value)}</strong>
    </div>
  );
    }
