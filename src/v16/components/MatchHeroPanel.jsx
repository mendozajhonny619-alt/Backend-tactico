// src/v16/components/MatchHeroPanel.jsx

import React from "react";

export default function MatchHeroPanel({ match, onOpen }) {
  const home = match?.home || match?.home_name || match?.homeTeam || "Equipo Local";
  const away = match?.away || match?.away_name || match?.awayTeam || "Equipo Visitante";

  const homeScore =
    match?.home_score ??
    match?.homeScore ??
    match?.score_home ??
    0;

  const awayScore =
    match?.away_score ??
    match?.awayScore ??
    match?.score_away ??
    0;

  const minute = match?.minute || match?.minuto || 0;
  const market = match?.market || "ENCIMA";
  const confidence = match?.confidence || match?.confidence_label || "FUERTE";
  const goalProb = match?.goal_probability || match?.goalProbability || 92;
  const risk = match?.risk_level || match?.riskLevel || "BAJO";

  return (
    <section className="match-hero-panel">
      <div className="match-hero-glow" />

      <div className="match-hero-top">
        <div className="hero-team left">
          <div className="hero-logo">{home.slice(0, 2).toUpperCase()}</div>
          <div>
            <h2>{home}</h2>
            <span>Local</span>
          </div>
        </div>

        <div className="hero-score">
          <strong>{homeScore} - {awayScore}</strong>
          <span>EN VIVO · MIN. {minute}</span>
        </div>

        <div className="hero-team right">
          <div>
            <h2>{away}</h2>
            <span>Visitante</span>
          </div>
          <div className="hero-logo green">{away.slice(0, 2).toUpperCase()}</div>
        </div>
      </div>

      <div className="match-hero-tags">
        <div>
          <span>MERCADO</span>
          <strong>{market}</strong>
        </div>

        <div>
          <span>RIESGO</span>
          <strong className="green">{risk}</strong>
        </div>

        <div>
          <span>CONFIANZA</span>
          <strong className="green">{confidence}</strong>
        </div>

        <div>
          <span>PROB. PRÓXIMO GOL</span>
          <strong>{goalProb}%</strong>
        </div>
      </div>

      <div className="hero-main-grid">
        <div className="hero-card">
          <h3>📈 MOMENTUM DEL PARTIDO</h3>
          <div className="hero-momentum">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <p>Presión ofensiva sostenida, ritmo alto y ventana táctica abierta.</p>
        </div>

        <div className="hero-card hero-prob">
          <h3>🎯 OPORTUNIDAD EN VENTANA</h3>
          <div className="hero-ring">
            <strong>{goalProb}%</strong>
            <span>IA</span>
          </div>
          <b>OVER 1.5 GOLES</b>
        </div>

        <div className="hero-card hero-risk">
          <h3>🛡️ ANÁLISIS DE RIESGO</h3>
          <div className="risk-gauge">
            <i />
          </div>
          <strong>{risk}</strong>
          <p>Riesgo controlado según presión, ritmo y contexto del partido.</p>
        </div>
      </div>

      <button className="hero-detail-btn" onClick={onOpen}>
        Ver detalle del partido
      </button>
    </section>
  );
    }
