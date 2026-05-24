import React from "react";
import ClockStatusBadge from "./ClockStatusBadge";

function pct(value) {
  if (value === null || value === undefined || value === "") return "0%";
  const n = Number(value);
  if (Number.isNaN(n)) return "0%";
  return `${n.toFixed(0)}%`;
}

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function getRankClass(rank) {
  const value = String(rank || "").toUpperCase();

  if (value.includes("PREMIUM")) return "premium";
  if (value.includes("FUERTE")) return "strong";
  if (value.includes("BUENA")) return "good";
  if (value.includes("OPERABLE")) return "operable";
  if (value.includes("OBSERVE")) return "observe";
  if (value.includes("BLOCKED")) return "blocked";

  return "neutral";
}

export default function SignalCardV17({ signal, compact = false }) {
  const rank = signal.elite_rank || signal.master_rank || "OBSERVE";
  const rankClass = getRankClass(rank);

  return (
    <article className={`v17-signal-card ${rankClass}`}>
      <div className="v17-signal-top">
        <div>
          <div className="v17-league">{safe(signal.league)}</div>
          <h3>
            {safe(signal.home_team)} <span>{safe(signal.scoreline || signal.current_score)}</span>{" "}
            {safe(signal.away_team)}
          </h3>
        </div>

        <div className="v17-rank-box">
          <span>{safe(rank)}</span>
          <strong>{pct(signal.elite_score || signal.master_confidence)}</strong>
        </div>
      </div>

      <div className="v17-signal-grid">
        <div>
          <small>Mercado</small>
          <strong>{safe(signal.market || signal.suggested_market)}</strong>
        </div>

        <div>
          <small>Decisión maestra</small>
          <strong>{safe(signal.master_status)}</strong>
        </div>

        <div>
          <small>Riesgo</small>
          <strong>{safe(signal.risk_status)}</strong>
        </div>

        <div>
          <small>Vida señal</small>
          <strong>{safe(signal.signal_life_label)}</strong>
        </div>
      </div>

      <ClockStatusBadge
        status={signal.clock_status}
        apiMinute={signal.api_minute}
        estimatedMinute={signal.estimated_minute}
        age={signal.data_age_seconds}
      />

      {!compact ? (
        <>
          <div className="v17-reading">
            <strong>Lectura principal</strong>
            <p>{safe(signal.main_reading)}</p>
          </div>

          <div className="v17-reading">
            <strong>Qué falta para entrar</strong>
            <p>{safe(signal.what_is_missing)}</p>
          </div>

          <div className="v17-mini-metrics">
            <span>OVER {pct(signal.over_score)}</span>
            <span>UNDER {pct(signal.under_score)}</span>
            <span>Presión {pct(signal.pressure_score)}</span>
            <span>Ritmo {pct(signal.rhythm_score)}</span>
            <span>Riesgo {pct(signal.risk_score)}</span>
          </div>

          {signal.probable_score ? (
            <div className="v17-probable-score">
              <span>Resultado probable</span>
              <strong>{safe(signal.probable_score.probable_score)}</strong>
              <small>{safe(signal.probable_score.reading)}</small>
            </div>
          ) : null}

          {Array.isArray(signal.failed_secondary_filters) &&
          signal.failed_secondary_filters.length > 0 ? (
            <div className="v17-tags warning">
              {signal.failed_secondary_filters.slice(0, 4).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          ) : null}

          {Array.isArray(signal.hard_blockers) && signal.hard_blockers.length > 0 ? (
            <div className="v17-tags blocked">
              {signal.hard_blockers.slice(0, 4).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
