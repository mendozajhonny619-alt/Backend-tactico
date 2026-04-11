import React from "react";

export default function MatchView({ match, onBack }) {
  if (!match) {
    return <div className="panel">No hay partido seleccionado</div>;
  }

  return (
    <div className="panel">
      <button onClick={onBack}>⬅ Volver</button>

      <h2>{match.partido || "Partido"}</h2>
      <h3>{match.score || "0-0"} | {match.minute || "-"}'</h3>

      <p>IA Score: {match.ai_score || 0}</p>
      <p>Gol %: {match.goal_probability || 0}%</p>
      <p>Riesgo: {match.risk_level || "MEDIO"}</p>
    </div>
  );
}
