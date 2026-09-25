// src/v16/components/LiveMatchCard.jsx

import React from "react";

import "../styles/components.css";

const LiveMatchCard = ({ match }) => {
  if (!match) return null;

  const {
    home,
    away,
    score,
    minute,

    ai_score,
    goal_probability,
    over_probability,
    under_probability,

    pressure_index,
    rhythm_index,

    state,
    dominance,

    next_goal_bias,
  } = match;

  return (
    <div className="glass-card live-match-card">
      {/* HEADER */}
      <div className="match-card-top">
        <span className="live-badge">
          ● LIVE
        </span>

        <span className="minute">
          {minute || 0}'
        </span>
      </div>

      {/* EQUIPOS */}
      <div className="teams-wrapper">
        <div className="team-side">
          <div className="team-logo-placeholder">
            {home?.charAt(0) || "H"}
          </div>

          <h3>{home}</h3>
        </div>

        <div className="score-center">
          <div className="score">
            {score || "0-0"}
          </div>

          <span className="match-state">
            {state || "LIVE"}
          </span>
        </div>

        <div className="team-side">
          <div className="team-logo-placeholder">
            {away?.charAt(0) || "A"}
          </div>

          <h3>{away}</h3>
        </div>
      </div>

      {/* KPIs */}
      <div className="metrics-grid">
        <Metric
          label="IA"
          value={ai_score}
          color="cyan"
        />

        <Metric
          label="GOL"
          value={`${goal_probability || 0}%`}
          color="green"
        />

        <Metric
          label="OVER"
          value={`${over_probability || 0}%`}
          color="yellow"
        />

        <Metric
          label="UNDER"
          value={`${under_probability || 0}%`}
          color="orange"
        />
      </div>

      {/* BARRAS */}
      <div className="bars-section">
        <Bar
          label="Presión"
          value={pressure_index || 0}
          className="pressure"
        />

        <Bar
          label="Ritmo"
          value={rhythm_index || 0}
          className="rhythm"
        />
      </div>

      {/* FOOTER */}
      <div className="card-footer">
        <span>
          Dominancia:
          <strong> {dominance || "N/A"}</strong>
        </span>

        <span>
          Próximo gol:
          <strong> {next_goal_bias || "N/A"}</strong>
        </span>
      </div>
    </div>
  );
};

function Metric({ label, value, color }) {
  return (
    <div className={`metric-box ${color}`}>
      <span>{label}</span>
      <strong>{value || 0}</strong>
    </div>
  );
}

function Bar({ label, value, className }) {
  return (
    <div className="bar-wrapper">
      <div className="bar-label">
        <span>{label}</span>
        <strong>{Number(value || 0).toFixed(0)}</strong>
      </div>

      <div className="bar-bg">
        <div
          className={`bar-fill ${className}`}
          style={{
            width: `${Math.min(100, Number(value || 0))}%`,
          }}
        />
      </div>
    </div>
  );
}

export default LiveMatchCard;
