// src/v16/pages/MatchDetailPage.jsx

import React from "react";

import MatchStatsGrid from "../components/MatchStatsGrid";
import LiveSignalFeed from "../components/LiveSignalFeed";
import RiskMeter from "../components/RiskMeter";

import "../styles/components.css";
import "../styles/Dashboard.css";

const num = (v, fb = 0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fb;
};

const text = (v, fb = "N/A") => {
  if (v === undefined || v === null || v === "") return fb;
  return String(v);
};

const getScoreParts = (match) => {
  if (match?.score && String(match.score).includes("-")) {
    const [home, away] = String(match.score).split("-");
    return {
      homeScore: home.trim() || "0",
      awayScore: away.trim() || "0",
    };
  }

  return {
    homeScore: match?.home_score ?? match?.homeScore ?? 0,
    awayScore: match?.away_score ?? match?.awayScore ?? 0,
  };
};

const getTacticalReading = (match) => {
  const shots = num(match?.shots);
  const shotsOnTarget = num(match?.shotsOnTarget ?? match?.shots_on_target);
  const corners = num(match?.corners);
  const attacks = num(match?.dangerousAttacks ?? match?.dangerous_attacks);
  const goal = num(match?.goalProbability ?? match?.goal_probability);

  const items = [];

  if (shots >= 10) items.push("El partido presenta volumen ofensivo alto.");
  if (shotsOnTarget >= 4) items.push("Hay tiros al arco suficientes para validar peligro real.");
  if (corners >= 5) items.push("La presión por bandas y pelota parada está activa.");
  if (attacks >= 30) items.push("Se detecta acumulación de ataques peligrosos.");
  if (goal >= 70) items.push("La probabilidad de próximo gol se mantiene elevada.");

  if (items.length === 0) {
    return [
      "El sistema mantiene el partido en observación.",
      "Todavía faltan señales ofensivas claras para validar una entrada.",
      "Conviene esperar más presión, tiros al arco o ataques peligrosos.",
    ];
  }

  return items;
};

export default function MatchDetailPage({ match, events = [], onBack }) {
  if (!match) {
    return (
      <section className="v16-screen">
        <button className="v16-back-btn" onClick={onBack}>
          ← Volver al panel
        </button>

        <div className="glass-card">
          <h2>Sin partido seleccionado</h2>
          <p>Selecciona un partido en vivo para ver el análisis táctico.</p>
        </div>
      </section>
    );
  }

  const home = text(match?.home, "Local");
  const away = text(match?.away, "Visitante");
  const league = text(match?.league, "Liga no disponible");
  const country = text(match?.country, "");
  const minute = num(match?.minute);
  const market = text(match?.market, "LECTURA IA");
  const rank = text(match?.rank, "OBSERVACIÓN");
  const risk = text(match?.riskLevel ?? match?.risk_level, "MEDIO");
  const goalProb = num(match?.goalProbability ?? match?.goal_probability);
  const { homeScore, awayScore } = getScoreParts(match);

  const homeLogo = match?.homeLogo || match?.home_logo;
  const awayLogo = match?.awayLogo || match?.away_logo;
  const flag = match?.countryFlag || match?.country_flag;
  const reading = getTacticalReading(match);

  return (
    <section className="match-detail-page">
      <button className="v16-back-btn" onClick={onBack}>
        ← Volver al panel
      </button>

      <section className="match-detail-hero glass-card">
        <div className="match-detail-league">
          <div>
            {flag && <img src={flag} alt={country || league} />}
            <span>{league}</span>
          </div>
          <strong>{country || "Fútbol en vivo"}</strong>
        </div>

        <div className="match-detail-scoreboard">
          <TeamBlock name={home} logo={homeLogo} label="Local" />

          <div className="match-detail-score">
            <strong>
              {homeScore} - {awayScore}
            </strong>
            <span>EN VIVO · MIN. {minute}</span>
          </div>

          <TeamBlock name={away} logo={awayLogo} label="Visitante" />
        </div>

        <div className="match-detail-tags">
          <InfoPill label="Mercado detectado" value={market} />
          <InfoPill label="Confianza IA" value={rank} />
          <InfoPill label="Riesgo" value={risk} />
          <InfoPill label="Prob. próximo gol" value={`${goalProb}%`} />
        </div>
      </section>

      <section className="match-detail-grid">
        <div className="glass-card tactical-reading-card">
          <h3>🧠 Lectura IA explicada</h3>
          <p className="reading-subtitle">
            Interpretación táctica del partido en tiempo real.
          </p>

          <ul>
            {reading.map((item, index) => (
              <li key={index}>✔ {item}</li>
            ))}
          </ul>
        </div>

        <div className="glass-card recommendation-card">
          <h3>🎯 Recomendación IA</h3>

          <div className="recommendation-market">{market}</div>

          <div className="recommendation-row">
            <span>Confianza</span>
            <strong>{rank}</strong>
          </div>

          <div className="recommendation-row">
            <span>Riesgo</span>
            <strong>{risk}</strong>
          </div>

          <div className="recommendation-row">
            <span>Probabilidad</span>
            <strong>{goalProb}%</strong>
          </div>

          <p>
            La recomendación se valida con marcador, minuto, presión ofensiva,
            tiros, corners y contexto táctico del partido.
          </p>
        </div>
      </section>

      <section className="match-detail-grid">
        <MatchStatsGrid stats={match} />

        <RiskMeter risk={risk} />
      </section>

      <section className="match-detail-grid">
        <div className="glass-card tactical-summary-card">
          <h3>📌 Resumen táctico</h3>

          <div className="summary-grid">
            <InfoPill label="Tiros" value={num(match?.shots)} />
            <InfoPill label="Tiros al arco" value={num(match?.shotsOnTarget ?? match?.shots_on_target)} />
            <InfoPill label="Corners" value={num(match?.corners)} />
            <InfoPill label="Ataques" value={num(match?.dangerousAttacks ?? match?.dangerous_attacks)} />
          </div>
        </div>

        <LiveSignalFeed events={events} />
      </section>
    </section>
  );
}

function TeamBlock({ name, logo, label }) {
  return (
    <div className="match-detail-team">
      <div className="match-detail-logo">
        {logo ? <img src={logo} alt={name} /> : <span>{String(name).slice(0, 2).toUpperCase()}</span>}
      </div>

      <h2>{name}</h2>
      <small>{label}</small>
    </div>
  );
}

function InfoPill({ label, value }) {
  return (
    <div className="match-info-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
      }
