import React from "react";

export default function StatCardV17({ label, value, hint, danger = false, good = false }) {
  return (
    <div className={`v17-stat-card ${danger ? "danger" : ""} ${good ? "good" : ""}`}>
      <div className="v17-stat-label">{label}</div>
      <div className="v17-stat-value">{value}</div>
      {hint ? <div className="v17-stat-hint">{hint}</div> : null}
    </div>
  );
}
