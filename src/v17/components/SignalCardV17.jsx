import React from "react";
import { Flame, Snowflake, TrendingUp } from "lucide-react";
import ClockStatusBadge from "./ClockStatusBadge";

function pct(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(0)}%` : "—";
}

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function rankClass(value) {
  const v = String(value || "").toUpperCase();
  if (v.includes("FUERTE") || v.includes("PREMIUM")) return "strong";
  if (v.includes("MEDIA")) return "good";
  if (v.includes("BLOCK")) return "blocked";
  return "observe";
}

function dynamicState(value) {
  const state = String(value || "").toUpperCase();
  const labels = {
    OPENING: "ABRIÉNDOSE",
    OPEN: "ABIERTO",
    BALANCED: "EQUILIBRADO",
    CLOSING: "CERRÁNDOSE",
    CLOSED: "CERRADO",
    UNKNOWN: "SIN HISTORIAL",
  };
  return labels[state] || state || "—";
}

function dominantTeam(signal) {
  const side = String(signal.recent_dominant_team || "").toUpperCase();
  if (side === "HOME") return signal.home_team || "Local";
  if (side === "AWAY") return signal.away_team || "Visitante";
  if (side === "BALANCED") return "Equilibrado";
  return safe(signal.recent_dominant_team, "Sin dominio");
}

export default function SignalCardV17({ signal, compact = false }) {
  const market = String(signal.market !== "OTHER" ? signal.market : signal.suggested_market || "OBSERVE").toUpperCase();
  const strength = signal.signal_strength || signal.elite_rank || signal.master_rank || (signal.can_publish ? "MEDIA" : "OBSERVE");
  const confidence = signal.official_confidence ?? signal.master_confidence ?? signal.elite_score ?? signal.candidate_score;
  const isOver = market === "OVER";
  const score = signal.scoreline || signal.current_score || `${safe(signal.home_score, 0)}-${safe(signal.away_score, 0)}`;

  return (
    <article className={`v17-signal-card ${rankClass(strength)}`}>
      <div className="v17-signal-accent" />
      <div className="v17-signal-top">
        <div className="v17-match-title">
          <div className="v17-league">{safe(signal.country)} · {safe(signal.league)}</div>
          <h3>{safe(signal.home_team)} <span>{score}</span> {safe(signal.away_team)}</h3>
        </div>
        <div className="v17-rank-box">
          <span>{safe(strength)}</span>
          <strong>{pct(confidence)}</strong>
        </div>
      </div>

      <div className={`v17-market-banner ${isOver ? "over" : market === "UNDER" ? "under" : "observe"}`}>
        <div>{isOver ? <Flame size={18}/> : market === "UNDER" ? <Snowflake size={18}/> : <TrendingUp size={18}/>}</div>
        <div><small>LECTURA</small><strong>{market}</strong></div>
        <div><small>LÍNEA</small><strong>{signal.line ? Number(signal.line).toFixed(1) : "AUTO"}</strong></div>
        <div><small>CUOTA</small><strong>{signal.odds_available ? Number(signal.odds).toFixed(2) : "—"}</strong></div>
      </div>

      <ClockStatusBadge status={signal.clock_status} apiMinute={signal.api_minute} estimatedMinute={signal.estimated_minute} age={signal.data_age_seconds} />

      <div className="v17-signal-grid">
        <div><small>Próx. gol</small><strong>{pct(signal.probability_next_goal)}</strong></div>
        <div><small>Sin más gol</small><strong>{pct(signal.probability_no_more_goals)}</strong></div>
        <div><small>Riesgo</small><strong>{safe(signal.risk_status || signal.risk_level)}</strong></div>
        <div><small>Valor</small><strong>{signal.odds_available ? `${Number(signal.value_edge || 0).toFixed(1)} pp` : "N/D"}</strong></div>
      </div>

      {signal.dynamics_available ? (
        <div className="v17-dynamics-strip">
          <div><small>Ritmo reciente</small><strong>{pct(signal.recent_threat_score)}</strong></div>
          <div><small>Partido</small><strong>{dynamicState(signal.dynamic_match_state)}</strong></div>
          <div><small>Empuja</small><strong>{dominantTeam(signal)}</strong></div>
          {signal.post_goal_reanalysis ? <span className="v17-post-goal">REANÁLISIS POST-GOL</span> : null}
        </div>
      ) : null}

      {!compact ? (
        <>
          <div className="v17-score-prediction">
            <div><small>Resultado principal</small><strong>{safe(signal.primary_final_score || signal.official_probable_score || signal.prediction_final_score)}</strong></div>
            <div><small>Próximo gol</small><strong>{safe(signal.official_next_goal_team, "Sin ventaja de equipo")}</strong></div>
          </div>

          {Array.isArray(signal.alternative_scores) && signal.alternative_scores.length > 0 ? (
            <div className="v17-alternatives">
              <small>Alternativos por inestabilidad</small>
              <div>{signal.alternative_scores.slice(0, 2).map((x) => <span key={x.score}>{x.score} · {pct(x.probability)}</span>)}</div>
            </div>
          ) : null}

          <div className="v17-reading"><strong>Lectura principal</strong><p>{safe(signal.main_reading)}</p></div>

          <div className="v17-evidence-grid">
            <div><small>Live</small><strong>{pct(signal.candidate_score)}</strong></div>
            <div><small>Prepartido</small><strong>{signal.pre_match_triggered ? (signal.pre_match_available ? "VALIDADO" : "SIN DATO") : "NO REQUERIDO"}</strong></div>
            <div><small>xG restante</small><strong>{Number(signal.expected_goals_remaining || 0).toFixed(2)}</strong></div>
            <div><small>Inestabilidad</small><strong>{pct(signal.dynamic_instability_score)}</strong></div>
          </div>

          {Array.isArray(signal.support_points) && signal.support_points.length ? (
            <div className="v17-tags support">{signal.support_points.slice(0, 5).map((x) => <span key={x}>{x}</span>)}</div>
          ) : null}
          {Array.isArray(signal.caution_points) && signal.caution_points.length ? (
            <div className="v17-tags warning">{signal.caution_points.slice(0, 4).map((x) => <span key={x}>{x}</span>)}</div>
          ) : null}
          {Array.isArray(signal.hard_blockers) && signal.hard_blockers.length ? (
            <div className="v17-tags blocked">{signal.hard_blockers.slice(0, 4).map((x) => <span key={x}>{x}</span>)}</div>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
