import React from "react";

export default function LiveMatches({ groupedLeagues, onOpenMatch }) {
  if (!groupedLeagues || groupedLeagues.length === 0) {
    return <div className="panel">No hay ligas disponibles</div>;
  }

  return (
    <div className="panel">
      <h2>⚽ EXPLORADOR DE PARTIDOS EN VIVO</h2>

      {groupedLeagues.map((group, index) => (
        <div key={index} className="league-block">
          <h3>
            🌍 {group.country} - {group.league}
          </h3>

          {group.items.map((match, i) => (
            <div key={i} className="match-row">
              <div>
                <strong>{match.partido || "Partido"}</strong>
                <p>
                  {match.score || "0-0"} | {match.minute || "-"}'
                </p>
              </div>

              <button
                className="open-button"
                onClick={() => onOpenMatch(match)}
              >
                Ver partido
              </button>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
