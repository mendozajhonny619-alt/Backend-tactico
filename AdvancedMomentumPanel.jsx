import React from "react";
import "../styles/components.css";

const num = (v, fallback = 0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

const clamp = (v) => Math.max(0, Math.min(100, num(v)));

const getTone = (value) => {
  if (value >= 75) return "danger";
  if (value >= 45) return "warn";
  return "good";
};

export default function AdvancedMomentumPanel({ match }) {
  if (!match) return null;

  const pressure =
    clamp(
      match.pressure_index ??
        match.pressureIndex ??
        0
    );

  const rhythm =
    clamp(
      match.rhythm_index ??
        match.rhythmIndex ??
        0
    );

  const intensity =
    clamp(
      match.live_intensity ??
        match.intensity ??
        0
    );

  const goalWindow =
    clamp(
      match.goal_window_score ??
        0
    );

  const overWindow =
    clamp(
      match.over_window_score ??
        0
    );

  const underTransition =
    clamp(
      match.under_transition_score ??
        0
    );

  const momentumState =
    match.momentum_state ||
    "ESTABLE";

  const visualState =
    match.visual_state ||
    "NORMAL";

  return (
    <section className="glass-card advanced-momentum-panel">
      <div className="advanced-momentum-header">
        <div>
          <span className="advanced-eyebrow">
            LIVE MOMENTUM
          </span>

          <h3>📈 Momentum avanzado</h3>

          <p>
            Lectura dinámica del ritmo y presión
            ofensiva del partido.
          </p>
        </div>

        <div className={`advanced-state ${getTone(intensity)}`}>
          <span>ESTADO</span>
          <strong>{visualState}</strong>
        </div>
      </div>

      <div className="advanced-main-grid">
        <Gauge
          label="Presión"
          value={pressure}
        />

        <Gauge
          label="Ritmo"
          value={rhythm}
        />

        <Gauge
          label="Intensidad"
          value={intensity}
        />
      </div>

      <div className="advanced-bars">
        <Bar
          label="Ventana de gol"
          value={goalWindow}
        />

        <Bar
          label="Ventana OVER"
          value={overWindow}
        />

        <Bar
          label="Transición UNDER"
          value={underTransition}
        />
      </div>

      <div className="advanced-footer">
        <div className="advanced-tag">
          <span>Momentum</span>
          <strong>{momentumState}</strong>
        </div>

        <div className="advanced-tag">
          <span>Dominancia</span>
          <strong>
            {match.dominance || "BALANCED"}
          </strong>
        </div>

        <div className="advanced-tag">
          <span>Lado ataque</span>
          <strong>
            {match.attack_side || "BALANCED"}
          </strong>
        </div>
      </div>
    </section>
  );
}

function Gauge({ label, value }) {
  const tone = getTone(value);

  return (
    <div className="advanced-gauge">
      <div
        className={`advanced-gauge-ring ${tone}`}
        style={{
          "--gauge-value": `${value}%`,
        }}
      >
        <strong>{value.toFixed(0)}%</strong>
      </div>

      <span>{label}</span>
    </div>
  );
}

function Bar({ label, value }) {
  const tone = getTone(value);

  return (
    <div className="advanced-bar">
      <div className="advanced-bar-top">
        <span>{label}</span>
        <b>{value.toFixed(0)}%</b>
      </div>

      <div className="advanced-bar-track">
        <i
          className={tone}
          style={{
            width: `${value}%`,
          }}
        />
      </div>
    </div>
  );
          }
