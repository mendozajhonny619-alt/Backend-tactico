import React from "react";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function resultClass(status) {
  const value = String(status || "").toUpperCase();

  if (value === "WON") return "won";
  if (value === "LOST") return "lost";
  if (value === "VOID") return "void";
  if (value === "PENDING") return "pending";

  return "pending";
}

export default function HistoryPanelV17({ pending = [], closed = [], learning = {} }) {
  const history = [...pending, ...closed].slice(0, 20);

  return (
    <section className="v17-history-panel">
      <div className="v17-section-header">
        <div>
          <h2>Historial V17</h2>
          <p>Seguimiento de señales, aciertos, fallos y aprendizaje.</p>
        </div>
        <span>{history.length}</span>
      </div>

      <div className="v17-learning-box">
        <strong>Aprendizaje</strong>
        <p>{safe(learning?.recommendation || "Todavía no hay suficiente historial cerrado.")}</p>
      </div>

      {history.length > 0 ? (
        <div className="v17-history-list">
          {history.map((item, index) => (
            <div className="v17-history-row" key={item.signal_key || index}>
              <div>
                <strong>
                  {safe(item.home_team)} vs {safe(item.away_team)}
                </strong>
                <span>
                  {safe(item.market)} · Entrada min {safe(item.entry_minute)} ·{" "}
                  {safe(item.entry_score)}
                </span>
              </div>

              <div>
                <span className={`v17-result ${resultClass(item.result_status)}`}>
                  {safe(item.result_label)}
                </span>
                <small>{safe(item.result_reason)}</small>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="v17-empty">Todavía no hay señales en seguimiento.</div>
      )}
    </section>
  );
                             }
