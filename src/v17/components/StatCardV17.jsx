import React from "react";

export default function StatCardV17({ label, value, hint, danger = false, good = false, onClick, active = false }) {
  const className = `v17-stat-card ${danger ? "danger" : ""} ${good ? "good" : ""} ${onClick ? "clickable" : ""} ${active ? "active" : ""}`;
  const content = (
    <>
      <div className="v17-stat-label">{label}</div>
      <div className="v17-stat-value">{value}</div>
      {hint ? <div className="v17-stat-hint">{hint}</div> : null}
      {onClick ? <div className="v17-stat-open">Ver partidos</div> : null}
    </>
  );

  return onClick ? (
    <button type="button" className={className} onClick={onClick} aria-pressed={active}>
      {content}
    </button>
  ) : (
    <div className={className}>{content}</div>
  );
}
