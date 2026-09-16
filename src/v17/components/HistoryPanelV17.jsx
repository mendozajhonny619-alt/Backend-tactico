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

function labelForGroup(key) {
  if (key === "HOY") return "Hoy · hasta 23:30";
  if (key === "AYER") return "Ayer";
  if (key === "HACE_1_SEMANA") return "Hace 1 semana";
  if (key === "HACE_2_SEMANAS") return "Hace 2 semanas";
  const match = String(key || "").match(/^HACE_(\d+)_DIAS$/);
  if (match) return `Hace ${match[1]} días`;
  return key;
}

function HistoryRows({ items = [], onDetail }) {
  return (
    <div className="v17-history-list">
      {items.map((item, index) => (
        <div className="v17-history-row" key={item.signal_id || item.signal_key || `${item.fixture_id}-${index}`}>
          <div className="v17-history-main">
            <strong>{safe(item.home_team)} vs {safe(item.away_team)}</strong>
            <span>{safe(item.market)} {safe(item.official_line ?? item.line, "")} · entrada min {safe(item.entry_minute)} · {safe(item.entry_score)}</span>
            <small>Marcador final/actual: <b>{safe(item.current_score || item.final_score)}</b></small>
            {(item.official_odds || item.odds) ? <small>Cuota: <b>{Number(item.official_odds || item.odds).toFixed(2)}</b> · {safe(item.odds_source || item.odds_provider, "mercado")}</small> : null}
          </div>
          <div className="v17-history-result">
            <span className={`v17-result ${resultClass(item.result_status)}`}>{safe(item.result_label || item.result_status, "PENDIENTE")}</span>
            <small>{safe(item.result_reason)}</small>
            {onDetail ? <button type="button" onClick={() => onDetail(item)}>Detalle <ChevronRight size={14}/></button> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function HistoryPanelV17({ pending = [], closed = [], groups = {}, learning = {}, onDetail, title = "Historial de señales" }) {
  const groupEntries = Object.entries(groups || {}).filter(([, items]) => Array.isArray(items) && items.length);
  const fallbackHistory = [...pending, ...closed].slice(0, 120);
  const total = pending.length + (groupEntries.length ? groupEntries.reduce((n, [, items]) => n + items.length, 0) : closed.length);

  return (
    <section className="v17-history-panel">
      <div className="v17-section-header">
        <div><h2>{title}</h2><p>Resultados oficiales persistentes: entrada, cierre, marcador y resultado. El día cambia a las 23:30 (Bolivia).</p></div>
        <span>{total}</span>
      </div>

      {learning?.recommendation ? (
        <div className="v17-learning-box">
          <strong>Aprendizaje</strong>
          <p>{safe(learning.recommendation)}</p>
        </div>
      ) : null}

      {pending.length ? (
        <div className="v17-history-day-block">
          <div className="v17-history-day-title"><strong>Pendientes</strong><span>{pending.length}</span></div>
          <HistoryRows items={pending} onDetail={onDetail}/>
        </div>
      ) : null}

      {groupEntries.length ? groupEntries.map(([key, items]) => (
        <div className="v17-history-day-block" key={key}>
          <div className="v17-history-day-title"><strong>{labelForGroup(key)}</strong><span>{items.length}</span></div>
          <HistoryRows items={items} onDetail={onDetail}/>
        </div>
      )) : (!pending.length && fallbackHistory.length ? <HistoryRows items={fallbackHistory} onDetail={onDetail}/> : null)}

      {!pending.length && !groupEntries.length && !fallbackHistory.length ? <div className="v17-empty">Todavía no hay señales oficiales registradas.</div> : null}
    </section>
  );
}
