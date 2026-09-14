import React from "react";
import { ChevronRight } from "lucide-react";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function resultClass(status) {
  const value = String(status || "").toUpperCase();
  if (value === "WON") return "won";
  if (value === "LOST") return "lost";
  if (value === "VOID") return "void";
  return "pending";
}

export default function HistoryPanelV17({ pending = [], closed = [], learning = {}, onDetail, title = "Historial de señales" }) {
  const history = [...pending, ...closed].slice(0, 80);
  return (
    <section className="v17-history-panel">
      <div className="v17-section-header">
        <div><h2>{title}</h2><p>Seguimiento real: marcador de entrada, cierre y resultado.</p></div>
        <span>{history.length}</span>
      </div>

      {learning?.recommendation ? (
        <div className="v17-learning-box">
          <strong>Aprendizaje</strong>
          <p>{safe(learning.recommendation)}</p>
        </div>
      ) : null}

      {history.length ? (
        <div className="v17-history-list">
          {history.map((item, index) => (
            <div className="v17-history-row" key={item.signal_key || index}>
              <div className="v17-history-main">
                <strong>{safe(item.home_team)} vs {safe(item.away_team)}</strong>
                <span>{safe(item.market)} · entrada min {safe(item.entry_minute)} · {safe(item.entry_score)}</span>
                <small>Marcador final/actual: <b>{safe(item.current_score)}</b></small>
              </div>
              <div className="v17-history-result">
                <span className={`v17-result ${resultClass(item.result_status)}`}>{safe(item.result_label || item.result_status, "PENDIENTE")}</span>
                <small>{safe(item.result_reason)}</small>
                {onDetail ? <button type="button" onClick={() => onDetail(item)}>Detalle <ChevronRight size={14}/></button> : null}
              </div>
            </div>
          ))}
        </div>
      ) : <div className="v17-empty">Todavía no hay señales en seguimiento.</div>}
    </section>
  );
}
