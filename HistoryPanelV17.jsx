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


function summarize(items = []) {
  const settled = (items || []).filter((x) => ["WON", "LOST", "VOID"].includes(String(x?.result_status || "").toUpperCase()));
  const wins = settled.filter((x) => String(x?.result_status || "").toUpperCase() === "WON").length;
  const losses = settled.filter((x) => String(x?.result_status || "").toUpperCase() === "LOST").length;
  const voids = settled.filter((x) => String(x?.result_status || "").toUpperCase() === "VOID").length;
  const precision = wins + losses ? (wins / (wins + losses)) * 100 : null;
  return { wins, losses, voids, closed: settled.length, precision };
}

function periodRows(groups = {}, closed = []) {
  const today = Array.isArray(groups.HOY) ? groups.HOY : [];
  const yesterday = Array.isArray(groups.AYER) ? groups.AYER : [];
  const weekKeys = ["HOY", "AYER", "HACE_2_DIAS", "HACE_3_DIAS", "HACE_4_DIAS", "HACE_5_DIAS", "HACE_6_DIAS"];
  const week = weekKeys.flatMap((key) => Array.isArray(groups[key]) ? groups[key] : []);
  if (!Object.keys(groups || {}).length) {
    return { today: [], yesterday: [], week: [] };
  }
  return { today, yesterday, week };
}

function PeriodCard({ label, items }) {
  const summary = summarize(items);
  return (
    <div className="v17-history-period-card">
      <small>{label}</small>
      <strong>{summary.closed} cerradas</strong>
      <span><b className="won-text">{summary.wins} A</b> · <b className="lost-text">{summary.losses} F</b>{summary.voids ? ` · ${summary.voids} V` : ""}</span>
      <em>{summary.precision === null ? "N/A" : `${summary.precision.toFixed(1)}%`}</em>
    </div>
  );
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
  const periods = periodRows(groups, closed);

  return (
    <section className="v17-history-panel">
      <div className="v17-section-header">
        <div><h2>{title}</h2><p>Resultados oficiales persistentes: entrada, cierre, marcador y resultado. El día cambia a las 23:30 (Bolivia).</p></div>
        <span>{total}</span>
      </div>

      <div className="v17-history-period-grid">
        <PeriodCard label="HOY" items={periods.today} />
        <PeriodCard label="AYER" items={periods.yesterday} />
        <PeriodCard label="ÚLTIMOS 7 DÍAS" items={periods.week} />
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
