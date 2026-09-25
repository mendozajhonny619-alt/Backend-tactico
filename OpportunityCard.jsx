// src/v16/components/OpportunityCard.jsx

import React from "react";
import "../styles/components.css";

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const percent = (value) => `${num(value).toFixed(1)}%`;

const logoText = (name) => String(name || "?").slice(0, 2).toUpperCase();

function TeamLogo({ logo, name }) {
  return (
    <div className="opportunity-team-logo">
      {logo ? <img src={logo} alt={name} /> : <span>{logoText(name)}</span>}
    </div>
  );
}

export default function OpportunityCard({ match, onOpen }) {
  if (!match) return null;

  const home = match?.home || "Local";
  const away = match?.away || "Visitante";

  const market = match?.market || "LECTURA IA";
  const confidence = match?.confidenceLabel || match?.confidence_label || match?.rank || "OBSERVACIÓN";
  const risk = match?.riskLevel || match?.risk_level || "MEDIO";

  const ai = num(match?.aiScore ?? match?.ai_score);
  const signal = num(match?.signalScore ?? match?.signal_score);
  const goal = num(match?.goalProbability ?? match?.goal_probability);
  const over = num(match?.overProbability ?? match?.over_probability);

  return (
    <article className="glass-card opportunity-card-premium">
      <div className="opportunity-card-head">
        <div>
          <span className="opportunity-league">
            {match?.countryFlag && <img src={match.countryFlag} alt={match?.country || "flag"} />}
            {match?.league || "Liga no disponible"}
          </span>
          <strong className="opportunity-minute">
            Min. {match?.minute || 0} · Marcador {match?.score || "0-0"}
          </strong>
        </div>

        <span className={`opportunity-risk ${String(risk).toLowerCase()}`}>
          {risk}
        </span>
      </div>

      <div className="opportunity-teams">
        <div className="opportunity-team">
          <TeamLogo logo={match?.homeLogo || match?.home_logo} name={home} />
          <h3>{home}</h3>
        </div>

        <div className="opportunity-score">
          <strong>{match?.score || "0-0"}</strong>
          <span>EN VIVO</span>
        </div>

        <div className="opportunity-team">
          <TeamLogo logo={match?.awayLogo || match?.away_logo} name={away} />
          <h3>{away}</h3>
        </div>
      </div>

      <div className="opportunity-market">
        <span>MERCADO RECOMENDADO</span>
        <strong>{market}</strong>
      </div>

      <div className="opportunity-metrics">
        <Metric label="IA" value={ai.toFixed(1)} />
        <Metric label="SEÑAL" value={signal.toFixed(1)} />
        <Metric label="GOL" value={percent(goal)} />
        <Metric label="OVER" value={percent(over)} />
      </div>

      <div className="opportunity-confidence">
        <span>CONFIANZA IA</span>
        <strong>{confidence}</strong>
      </div>

      <button className="opportunity-open-btn" onClick={onOpen}>
        Ver partido
      </button>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="opportunity-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
                                         }
