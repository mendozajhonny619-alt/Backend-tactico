import React from "react";
import "../styles/components.css";

const safeArray = (value) => {
  if (Array.isArray(value)) return value;
  return [];
};

const tone = (value) => {
  const text = String(value || "").toUpperCase();

  if (
    text.includes("OVER") ||
    text.includes("HIGH") ||
    text.includes("ALTO") ||
    text.includes("CHAOS")
  ) {
    return "danger";
  }

  if (
    text.includes("UNDER") ||
    text.includes("LOW") ||
    text.includes("BAJO")
  ) {
    return "good";
  }

  return "warn";
};

export default function DeepAnalysisPanel({ match }) {
  if (!match) return null;

  const projection =
    match.deep_projection_bias ||
    "NEUTRAL";

  const confidence =
    Number(match.deep_projection_confidence || 0);

  const summary =
    match.deep_analysis_summary ||
    "Sin análisis profundo disponible.";

  const tacticalAlerts = safeArray(
    match.deep_tactical_alerts
  );

  const eventProfile =
    match.deep_event_profile || {};

  return (
    <section className="glass-card deep-analysis-panel">
      <div className="deep-analysis-header">
        <div>
          <span className="deep-analysis-eyebrow">
            DEEP AI ANALYSIS
          </span>

          <h3>🧠 Análisis profundo</h3>

          <p>
            Lectura táctica avanzada del comportamiento
            en vivo del partido.
          </p>
        </div>

        <div className={`deep-analysis-bias ${tone(projection)}`}>
          <span>PROYECCIÓN</span>
          <strong>{projection}</strong>
        </div>
      </div>

      <div className="deep-analysis-grid">
        <div className="deep-analysis-box">
          <span>Confianza IA</span>
          <strong>{confidence.toFixed(0)}%</strong>
        </div>

        <div className="deep-analysis-box">
          <span>Ventana</span>
          <strong>
            {match.deep_projection_window || "N/A"}
          </strong>
        </div>

        <div className="deep-analysis-box">
          <span>Riesgo gol tardío</span>
          <strong>
            {match.late_goal_risk || "NORMAL"}
          </strong>
        </div>

        <div className="deep-analysis-box">
          <span>Riesgo retención</span>
          <strong>
            {match.retention_risk_label || "MEDIO"}
          </strong>
        </div>
      </div>

      <div className="deep-analysis-trends">
        <Trend
          label="Presión"
          value={match.deep_pressure_trend}
        />

        <Trend
          label="Ritmo"
          value={match.deep_rhythm_trend}
        />

        <Trend
          label="Amenaza gol"
          value={match.deep_goal_threat_trend}
        />

        <Trend
          label="Vida señal"
          value={match.deep_signal_life_status}
        />
      </div>

      <div className="deep-analysis-summary">
        <p>{summary}</p>
      </div>

      {tacticalAlerts.length > 0 && (
        <div className="deep-analysis-alerts">
          {tacticalAlerts.slice(0, 8).map((alert, index) => (
            <b
              key={`${alert}-${index}`}
              className={tone(alert)}
            >
              {String(alert).replaceAll("_", " ")}
            </b>
          ))}
        </div>
      )}

      <div className="deep-analysis-events">
        <MiniBox
          label="Eventos recientes"
          value={eventProfile.recent_events_count || 0}
        />

        <MiniBox
          label="Goles recientes"
          value={eventProfile.recent_goals_count || 0}
        />

        <MiniBox
          label="Tarjetas recientes"
          value={eventProfile.recent_cards_count || 0}
        />

        <MiniBox
          label="Sustituciones"
          value={eventProfile.recent_substitutions || 0}
        />
      </div>
    </section>
  );
}

function Trend({ label, value }) {
  return (
    <div className={`deep-trend ${tone(value)}`}>
      <span>{label}</span>
      <strong>{value || "UNKNOWN"}</strong>
    </div>
  );
}

function MiniBox({ label, value }) {
  return (
    <div className="deep-mini-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
    }
