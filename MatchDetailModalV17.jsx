import React from "react";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function num(value, fallback = 0) {
  const n = Number(value);
  return Number.isNaN(n) ? fallback : n;
}

function pct(value, fallback = 0) {
  const n = Number(value);
  const finalValue = Number.isNaN(n) ? fallback : n;
  return `${Math.max(0, Math.min(100, finalValue)).toFixed(0)}%`;
}

function scoreText(item) {
  if (item.current_score) return item.current_score;
  const home = safe(item.home_score ?? item.marcador_local ?? item.entry_home_score, 0);
  const away = safe(item.away_score ?? item.marcador_away ?? item.entry_away_score, 0);
  return `${home}-${away}`;
}

function probableScore(item) {
  if (item?.probable_score?.probable_score) return item.probable_score.probable_score;
  if (item?.probable_score?.current_score) return item.probable_score.current_score;
  return safe(item.resultado_probable, scoreText(item));
}

function mainDecision(item) {
  return safe(item.master_action || item.decision_maestra || item.accion_maestro, "OBSERVE");
}

function marketLabel(item) {
  return safe(item.market || item.mercado || item.market_type, "OBSERVE");
}

function confidenceValue(item) {
  return num(item.master_confidence ?? item.elite_score ?? item.confianza_maestra, 0);
}

function goalProbability(item) {
  return num(item.goal_probability ?? item.goal_prob ?? item.prob_gol ?? item.probabilidad_gol, 0);
}

function riskLabel(item) {
  return safe(item.risk_label || item.estado_riesgo || item.riesgo || "MEDIO");
}

function contextLabel(item) {
  return safe(item.main_reading || item.lectura_principal || item.category_context || "Lectura táctica en evaluación.");
}

function rhythmValue(item) {
  const raw = num(item.ritmo ?? item.rhythm_score ?? item.puntuacion_ritmo, 0);
  return raw > 10 ? raw / 10 : raw;
}

function pressureValue(item) {
  return num(item.pressure_score ?? item.puntuacion_presion_profunda ?? item.presion ?? 0, 0);
}

function xgHome(item) {
  return num(item.xg_home ?? item.home_xg ?? item.xg_local ?? 0, 0);
}

function xgAway(item) {
  return num(item.xg_away ?? item.away_xg ?? item.xg_visitante ?? 0, 0);
}

function shotsHome(item) {
  return num(item.shots_home ?? item.home_shots ?? item.remates_local ?? 0, 0);
}

function shotsAway(item) {
  return num(item.shots_away ?? item.away_shots ?? item.remates_visitante ?? 0, 0);
}

function sotHome(item) {
  return num(item.sot_home ?? item.home_sot ?? item.tiros_arco_local ?? 0, 0);
}

function sotAway(item) {
  return num(item.sot_away ?? item.away_sot ?? item.tiros_arco_visitante ?? 0, 0);
}

function attacksHome(item) {
  return num(item.attacks_home ?? item.home_dangerous_attacks ?? item.ataques_peligrosos_local ?? 0, 0);
}

function attacksAway(item) {
  return num(item.attacks_away ?? item.away_dangerous_attacks ?? item.ataques_peligrosos_visitante ?? 0, 0);
}

function possessionHome(item) {
  return num(item.possession_home ?? item.home_possession ?? item.posesion_local ?? 50, 50);
}

function possessionAway(item) {
  return num(item.possession_away ?? item.away_possession ?? item.posesion_visitante ?? 50, 50);
}

function cornersHome(item) {
  return num(item.corners_home ?? item.home_corners ?? item.corners_local ?? 0, 0);
}

function cornersAway(item) {
  return num(item.corners_away ?? item.away_corners ?? item.corners_visitante ?? 0, 0);
}

function overValue(item) {
  return num(item.over_probability ?? item.over ?? item.puntuacion_sobre ?? 0, 0);
}

function underValue(item) {
  return num(item.under_probability ?? item.under ?? item.puntuacion_bajo ?? 0, 0);
}

function nextGoalHome(item) {
  const v = num(item.home_next_goal_prob ?? item.proximo_gol_local ?? 0, 0);
  if (v > 0) return v;
  return goalProbability(item);
}

function nextGoalAway(item) {
  const v = num(item.away_next_goal_prob ?? item.proximo_gol_visitante ?? 0, 0);
  if (v > 0) return v;
  return Math.max(0, 100 - nextGoalHome(item));
}

function statPair(label, home, away) {
  return { label, home: num(home, 0), away: num(away, 0) };
}

function TeamLogo({ src, name }) {
  const initials =
    String(name || "FC")
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((x) => x[0])
      .join("")
      .toUpperCase() || "FC";

  if (src) {
    return (
      <div className="v17-team-logo">
        <img src={src} alt={name || "team"} />
      </div>
    );
  }

  return <div className="v17-team-logo fallback">{initials}</div>;
}

function MetricBox({ label, value, subtitle, tone = "cyan" }) {
  return (
    <div className={`v17-detail-metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {subtitle ? <small>{subtitle}</small> : null}
    </div>
  );
}

function CompareStat({ label, home, away }) {
  const total = Math.max(home + away, 1);
  const homeWidth = (home / total) * 100;
  const awayWidth = (away / total) * 100;

  return (
    <div className="v17-compare-stat">
      <div className="v17-compare-head">
        <strong>{home}</strong>
        <span>{label}</span>
        <strong>{away}</strong>
      </div>

      <div className="v17-compare-bar">
        <div className="home" style={{ width: `${homeWidth}%` }} />
        <div className="away" style={{ width: `${awayWidth}%` }} />
      </div>
    </div>
  );
}

function ProbabilityBar({ leftLabel, leftValue, rightLabel, rightValue }) {
  const lv = Math.max(0, Math.min(100, num(leftValue, 0)));
  const rv = Math.max(0, Math.min(100, num(rightValue, 0)));

  return (
    <div className="v17-probability-box">
      <div className="v17-probability-head">
        <div>
          <span>{leftLabel}</span>
          <strong>{pct(lv)}</strong>
        </div>
        <div className="right">
          <span>{rightLabel}</span>
          <strong>{pct(rv)}</strong>
        </div>
      </div>

      <div className="v17-dual-bar">
        <div className="left" style={{ width: `${lv}%` }} />
        <div className="right" style={{ width: `${rv}%` }} />
      </div>
    </div>
  );
}

function AlertList({ items = [] }) {
  const clean = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!clean.length) {
    return <div className="v17-alert-item ok">Sin alertas críticas activas.</div>;
  }

  return (
    <div className="v17-alert-list">
      {clean.slice(0, 5).map((item, idx) => (
        <div key={idx} className="v17-alert-item">
          {String(item)}
        </div>
      ))}
    </div>
  );
}

export default function MatchDetailModalV17({ match, onClose }) {
  if (!match) return null;

  const stats = [
    statPair("Remates totales", shotsHome(match), shotsAway(match)),
    statPair("Remates al arco", sotHome(match), sotAway(match)),
    statPair("Ataques peligrosos", attacksHome(match), attacksAway(match)),
    statPair("xG", xgHome(match), xgAway(match)),
    statPair("Posesión", possessionHome(match), possessionAway(match)),
    statPair("Tiros de esquina", cornersHome(match), cornersAway(match)),
  ];

  const homeTeam = safe(match.home_team || match.local || match.team_home, "Local");
  const awayTeam = safe(match.away_team || match.visitante || match.team_away, "Visitante");

  const homeLogo = match.home_logo || match.home_team_logo || match.local_logo || null;
  const awayLogo = match.away_logo || match.away_team_logo || match.visitante_logo || null;

  const mainReading = contextLabel(match);
  const probable = probableScore(match);
  const over = overValue(match);
  const under = underValue(match);

  const clockLabel =
    match.clock_status === "CLOCK_STALE" || match.clock_status === "BLOCKED_CLOCK"
      ? "RELOJ EN ALERTA"
      : "RELOJ OK";

  const missing =
    match.what_is_missing ||
    (Array.isArray(match.soft_warnings) && match.soft_warnings.length
      ? match.soft_warnings.join(" | ")
      : "Sin faltantes críticos.");

  const alerts = [
    ...(Array.isArray(match.clock_warnings) ? match.clock_warnings : []),
    ...(Array.isArray(match.market_warnings) ? match.market_warnings : []),
    ...(Array.isArray(match.risk_warnings) ? match.risk_warnings : []),
    ...(Array.isArray(match.tactical_warnings) ? match.tactical_warnings : []),
  ];

  return (
    <div className="v17-detail-overlay">
      <div className="v17-detail-modal">
        <div className="v17-detail-topbar">
          <div className="v17-detail-topbar-left">
            <button className="v17-back-btn" onClick={onClose}>
              ← Volver
            </button>

            <div className="v17-brand-detail">
              <strong>JHONNY ELITE V17</strong>
              <span>Match Center</span>
            </div>

            <div className="v17-top-chip">
              <strong>{safe(match.league, "Liga")}</strong>
              <span>{safe(match.country, "País")}</span>
            </div>

            <div className="v17-top-chip">
              <strong>{safe(match.country_flag || match.country, "Bandera")}</strong>
              <span>{safe(match.country, "Ubicación")}</span>
            </div>

            <div className="v17-top-chip">
              <strong>{safe(match.round || match.jornada, "En juego")}</strong>
              <span>Ronda</span>
            </div>
          </div>

          <div className="v17-detail-topbar-right">
            <div className="v17-status-chip green">Sistema ACTIVO</div>
            <div className="v17-status-chip blue">Live Sync</div>
          </div>
        </div>

        <div className="v17-detail-scoreboard">
          <div className="v17-team-block">
            <TeamLogo src={homeLogo} name={homeTeam} />
            <div>
              <h3>{homeTeam}</h3>
              <span>Local</span>
            </div>
          </div>

          <div className="v17-score-center">
            <div className="v17-live-tag">EN VIVO</div>
            <div className="v17-minute-live">
              {safe(match.minute_api ?? match.minuto_api ?? match.entry_minute, 0)}'
            </div>
            <div className="v17-big-score">{scoreText(match)}</div>
            <div className="v17-score-sub">
              API {safe(match.minute_api ?? match.minuto_api, 0)} · EST {safe(match.estimated_minute ?? match.minuto_estimado ?? match.minute_api, 0)}
            </div>
          </div>

          <div className="v17-team-block away">
            <div>
              <h3>{awayTeam}</h3>
              <span>Visitante</span>
            </div>
            <TeamLogo src={awayLogo} name={awayTeam} />
          </div>

          <div className="v17-right-summary">
            <div className="v17-summary-pill purple">
              <span>Señal principal</span>
              <strong>{marketLabel(match)}</strong>
              <small>Confianza {pct(confidenceValue(match))}</small>
            </div>

            <div className="v17-summary-pill blue">
              <span>Ranking de señal</span>
              <strong>{safe(match.master_rank || match.elite_rank, "FUERTE")}</strong>
            </div>
          </div>
        </div>

        <div className="v17-detail-metrics-grid">
          <MetricBox
            label="Puntuación IA"
            value={`${confidenceValue(match).toFixed(0)}/100`}
            subtitle="Muy alta"
            tone="purple"
          />

          <MetricBox
            label="Probabilidad de gol"
            value={pct(goalProbability(match))}
            subtitle="Próximo gol"
            tone="green"
          />

          <MetricBox
            label="Riesgo global"
            value={riskLabel(match)}
            subtitle="Riesgo operativo"
            tone="yellow"
          />

          <MetricBox
            label="Estado del contexto"
            value={safe(match.context_state || match.estado_contexto || "FAVORABLE")}
            subtitle="Lectura contextual"
            tone="cyan"
          />

          <MetricBox
            label="Decisión final"
            value={mainDecision(match)}
            subtitle={marketLabel(match)}
            tone="lime"
          />

          <MetricBox
            label="Resultado más probable"
            value={probable}
            subtitle="Lectura proyectada"
            tone="green"
          />
        </div>

        <div className="v17-detail-main-grid">
          <div className="v17-panel">
            <div className="v17-panel-title">Estadísticas del partido</div>

            <div className="v17-compare-list">
              {stats.map((row) => (
                <CompareStat
                  key={row.label}
                  label={row.label}
                  home={row.home}
                  away={row.away}
                />
              ))}
            </div>
          </div>

          <div className="v17-panel">
            <div className="v17-panel-title">Momentum & presión del partido</div>

            <div className="v17-momentum-placeholder">
              <div className="v17-momentum-legend">
                <span className="red-dot">{homeTeam}</span>
                <span className="blue-dot">{awayTeam}</span>
              </div>

              <div className="v17-wave-grid">
                <div className="wave red" />
                <div className="wave blue" />
              </div>
            </div>

            <div className="v17-triple-metrics">
              <div className="v17-mini-box">
                <span>Presión</span>
                <strong>{pct(pressureValue(match))}</strong>
              </div>

              <div className="v17-mini-box">
                <span>Intensidad</span>
                <strong>{rhythmValue(match).toFixed(1)}/10</strong>
              </div>

              <div className="v17-mini-box">
                <span>Control del partido</span>
                <strong>{pct(possessionHome(match))}</strong>
              </div>
            </div>

            <div className="v17-reading-box hot">
              <span>Lectura del partido</span>
              <strong>{safe(match.context_label || match.estado_contexto || "PARTIDO EN LECTURA")}</strong>
              <p>{mainReading}</p>
            </div>
          </div>

          <div className="v17-panel">
            <div className="v17-panel-title">Lectura IA & decisión</div>

            <ProbabilityBar
              leftLabel={homeTeam}
              leftValue={nextGoalHome(match)}
              rightLabel={awayTeam}
              rightValue={nextGoalAway(match)}
            />

            <div className="v17-side-stack">
              <div className="v17-reading-box green">
                <span>Decisión recomendada</span>
                <strong>{mainDecision(match)}</strong>
                <p>{marketLabel(match)} · Confianza {pct(confidenceValue(match))}</p>
              </div>

              <div className="v17-reading-box orange">
                <span>Alertas de riesgo</span>
                <AlertList items={alerts} />
              </div>

              <div className="v17-reading-box blue">
                <span>Lectura alternativa</span>
                <strong>{under >= over ? "UNDER" : "OVER"}</strong>
                <p>Alternativa secundaria según el equilibrio del partido.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="v17-detail-bottom-grid">
          <div className="v17-panel">
            <div className="v17-panel-title">Mercado & valor</div>

            <ProbabilityBar
              leftLabel="OVER"
              leftValue={over}
              rightLabel="UNDER"
              rightValue={under}
            />

            <div className="v17-chip-row">
              <span className="v17-data-chip">OVER {pct(over)}</span>
              <span className="v17-data-chip">UNDER {pct(under)}</span>
              <span className="v17-data-chip">Presión {pct(pressureValue(match))}</span>
              <span className="v17-data-chip">Ritmo {rhythmValue(match).toFixed(1)}/10</span>
            </div>
          </div>

          <div className="v17-panel">
            <div className="v17-panel-title">Resultado probable</div>
            <div className="v17-probable-score-box">
              <strong>{probable}</strong>
              <span>
                {safe(
                  match?.probable_score?.reading ||
                    match.result_probability_reading ||
                    "Lectura del marcador más probable."
                )}
              </span>
            </div>
          </div>

          <div className="v17-panel">
            <div className="v17-panel-title">Qué falta para entrar</div>
            <div className="v17-reading-box dark">
              <strong>{safe(missing, "Sin faltantes críticos.")}</strong>
              <p>
                Estado del reloj: {clockLabel}. Señal: {safe(match.signal_life_label || match.signal_life_state, "SEÑAL FRESCA")}.
              </p>
            </div>
          </div>

          <div className="v17-panel">
            <div className="v17-panel-title">Reloj y sincronía</div>
            <div className={`v17-clock-box ${clockLabel.includes("ALERTA") ? "alert" : "ok"}`}>
              <strong>{clockLabel}</strong>
              <span>
                API {safe(match.minute_api ?? match.minuto_api, 0)} · EST {safe(match.estimated_minute ?? match.minuto_estimado, 0)}
              </span>
              <small>
                data_age {safe(match.data_age_seconds, 0)}s · frozen {String(
                  safe(match.clock_frozen, false)
                )}
              </small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
                    }
