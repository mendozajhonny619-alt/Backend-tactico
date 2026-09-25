// src/v16/components/MatchStatsGrid.jsx

import React from "react";
import "../styles/components.css";

const safe = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

const MatchStatsGrid = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="glass-card stats-grid">
      <div className="card-header">
        <h3>📊 Estadísticas Live</h3>
        <span className="live-mini-badge">LIVE</span>
      </div>

      <div className="stats-grid-content">
        <StatItem
          label="Posesión"
          value={`${safe(stats.possession)}%`}
          glow="cyan"
        />

        <StatItem
          label="Tiros"
          value={safe(stats.shots)}
          glow="green"
        />

        <StatItem
          label="Corners"
          value={safe(stats.corners)}
          glow="yellow"
        />

        <StatItem
          label="Ataques"
          value={safe(
            stats.dangerousAttacks ||
            stats.dangerous_attacks
          )}
          glow="orange"
        />

        <StatItem
          label="xG"
          value={safe(stats.xg).toFixed(2)}
          glow="purple"
        />

        <StatItem
          label="Presión"
          value={safe(stats.pressure_index)}
          glow="red"
        />
      </div>
    </div>
  );
};

function StatItem({ label, value, glow }) {
  return (
    <div className={`stat-item ${glow}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default MatchStatsGrid;
