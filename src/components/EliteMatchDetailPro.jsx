import React from "react";

const n = (v, fallback = "No disponible") =>
  v === undefined || v === null || v === "" ? fallback : v;

const pct = (v) => {
  if (v === undefined || v === null || v === "") return "No disponible";
  const num = Number(v);
  if (Number.isNaN(num)) return v;
  return `${Math.round(num)}%`;
};

const translate = (value) => {
  const map = {
    OVER: "Encima / Más goles",
    UNDER: "Debajo / Menos goles",
    HOME: "Local",
    AWAY: "Visitante",
    BALANCED: "Equilibrado",
    NEUTRAL: "Neutral",
    PREMIUM: "Premium",
    FUERTE: "Fuerte",
    BUENA: "Buena",
    OPERABLE: "Operable",
    OBSERVACION: "Observación",
    NO_BET: "No entrar",
    HIGH: "Alta",
    MEDIUM: "Media",
    LOW: "Baja",
    BAJO: "Bajo",
    MEDIO: "Medio",
    ALTO: "Alto",
    INTERNAL_ONLY: "Mercado interno",
    PENDING: "Mercado pendiente",
    AUTO: "Línea automática",
    SCORE_HOLD: "Retención",
    UNCLEAR: "No claro",
    WAIT_CONFIRMATION: "Esperar confirmación",
    AVOID: "Evitar",
    ENTER_OK: "Entrada válida",
    MUY_CALIENTE: "Muy caliente",
    CALIENTE: "Caliente",
    TIBIO: "Tibio",
    CONTROLADO: "Controlado",
    FRIO: "Frío",
    MUERTO: "Muerto",
  };

  return map[value] || value || "No disponible";
};

const splitScore = (score) => {
  if (!score) return ["-", "-"];
  const clean = String(score).replace(/\s/g, "");
  if (clean.includes("-")) return clean.split("-");
  if (clean.includes(":")) return clean.split(":");
  return [score, ""];
};

function StatRow({ label, home, away }) {
  return (
    <div className="elite-stat-row">
      <span>{n(home, "-")}</span>
      <strong>{label}</strong>
      <span>{n(away, "-")}</span>
    </div>
  );
}

function InfoPill({ label, value, tone = "neutral" }) {
  return (
    <div className={`elite-pill elite-pill-${tone}`}>
      <small>{label}</small>
      <b>{n(value)}</b>
    </div>
  );
}

export default function EliteMatchDetailPro({ item }) {
  if (!item) {
    return (
      <section className="elite-detail-pro empty">
        <h2>Selecciona un partido</h2>
        <p>El detalle táctico aparecerá cuando selecciones una señal o partido en observación.</p>
      </section>
    );
  }

  const home =
    item.home_name ||
    item.home ||
    item.local ||
    item.nombre_local ||
    "Local";

  const away =
    item.away_name ||
    item.away ||
    item.visitante ||
    item.nombre_visitante ||
    "Visitante";

  const [homeScore, awayScore] = splitScore(item.score);

  const risk = translate(item.risk_level);
  const market = translate(item.market);
  const rank = translate(item.rank || item.confidence_label);
  const nextGoal = translate(item.next_goal_bias);
  const context = translate(item.context_state || item.tactical_state);
  const momentum = translate(item.momentum_label);

  const explainRisk =
    item.risk_reducer_reason ||
    item.decision_reason ||
    "El sistema evalúa riesgo combinando calidad de datos, ritmo, presión, ventana del partido y señales de enfriamiento.";

  const explainSignal =
    item.decision_advice ||
    item.revalidation_advice ||
    item.technical_summary ||
    item.deep_analysis_summary ||
    "La lectura se genera al cruzar IA, presión ofensiva, ritmo, mercado, ventana operativa y riesgo actual.";

  const explainNextGoal =
    item.next_goal_helper_advice ||
    item.next_goal_support ||
    item.next_goal_warning ||
    "La tendencia lateral indica qué equipo tiene mayor inclinación ofensiva relativa, pero no garantiza gol.";

  const events = Array.isArray(item.events) ? item.events.slice(-6).reverse() : [];

  return (
    <section className="elite-detail-pro">
      <div className="elite-hero-card">
        <div className="elite-league-line">
          <span>{n(item.country)}</span>
          <b>{n(item.league)}</b>
          <span>{item.data_quality ? `Datos: ${translate(item.data_quality)}` : "Datos live"}</span>
        </div>

        <div className="elite-scoreboard">
          <div className="elite-team">
            {item.home_logo && <img src={item.home_logo} alt={home} />}
            <h3>{home}</h3>
          </div>

          <div className="elite-score-center">
            <div className="elite-live-minute">{n(item.minute, "LIVE")}'</div>
            <div className="elite-score">
              <span>{homeScore}</span>
              <em>-</em>
              <span>{awayScore}</span>
            </div>
            <div className="elite-market-main">{market}</div>
          </div>

          <div className="elite-team">
            {item.away_logo && <img src={item.away_logo} alt={away} />}
            <h3>{away}</h3>
          </div>
        </div>
      </div>

      <div className="elite-grid-pro">
        <div className="elite-card-pro elite-main-reading">
          <h3>Lectura táctica IA</h3>
          <p>{explainSignal}</p>

          <div className="elite-pill-grid">
            <InfoPill label="Rango" value={rank} tone="blue" />
            <InfoPill label="Confianza" value={pct(item.confidence || item.confidence_score)} tone="green" />
            <InfoPill label="IA Score" value={item.ai_score} tone="cyan" />
            <InfoPill label="Signal Score" value={item.signal_score || item.decision_score} tone="purple" />
          </div>
        </div>

        <div className="elite-card-pro">
          <h3>Probabilidades</h3>
          <div className="elite-prob-list">
            <InfoPill label="Gol" value={pct(item.goal_probability)} tone="green" />
            <InfoPill label="OVER" value={pct(item.over_probability)} tone="blue" />
            <InfoPill label="UNDER" value={pct(item.under_probability)} tone="yellow" />
            <InfoPill label="Retención" value={pct(item.score_hold_probability || item.retention_risk)} tone="red" />
          </div>
        </div>

        <div className="elite-card-pro">
          <h3>Momentum y contexto</h3>
          <div className="elite-mini-table">
            <p><b>Estado:</b> {context}</p>
            <p><b>Momentum:</b> {momentum}</p>
            <p><b>Dominio:</b> {translate(item.dominance)}</p>
            <p><b>Ritmo:</b> {n(item.rhythm_index)}</p>
            <p><b>Presión:</b> {n(item.pressure_index)}</p>
          </div>
        </div>

        <div className="elite-card-pro">
          <h3>Próximo gol / retención</h3>
          <p>{explainNextGoal}</p>
          <div className="elite-pill-grid">
            <InfoPill label="Tendencia" value={nextGoal} tone="cyan" />
            <InfoPill label="Confianza" value={pct(item.next_goal_confidence)} tone="green" />
            <InfoPill label="Local presión" value={item.home_next_goal_pressure || item.home_pressure} tone="blue" />
            <InfoPill label="Visitante presión" value={item.away_next_goal_pressure || item.away_pressure} tone="purple" />
          </div>
        </div>

        <div className="elite-card-pro elite-stats-card">
          <h3>Estadísticas comparativas</h3>
          <StatRow label="Posesión" home={item.possession_home} away={item.possession_away} />
          <StatRow label="Tiros" home={item.home_stats?.shots || item.shots?.home} away={item.away_stats?.shots || item.shots?.away} />
          <StatRow label="Tiros al arco" home={item.home_stats?.shots_on_target || item.shots_on_target?.home} away={item.away_stats?.shots_on_target || item.shots_on_target?.away} />
          <StatRow label="Corners" home={item.home_stats?.corners || item.corners?.home} away={item.away_stats?.corners || item.corners?.away} />
          <StatRow label="Ataques peligrosos" home={item.home_stats?.dangerous_attacks || item.dangerous_attacks?.home} away={item.away_stats?.dangerous_attacks || item.dangerous_attacks?.away} />
          <StatRow label="xG" home={item.home_stats?.xg || item.xg?.home || item.xG?.home} away={item.away_stats?.xg || item.xg?.away || item.xG?.away} />
        </div>

        <div className="elite-card-pro">
          <h3>Riesgo y value</h3>
          <p>{explainRisk}</p>
          <div className="elite-pill-grid">
            <InfoPill label="Riesgo" value={risk} tone="red" />
            <InfoPill label="Risk Score" value={item.risk_score} tone="yellow" />
            <InfoPill label="Value" value={translate(item.value_category)} tone="green" />
            <InfoPill label="Edge" value={item.value_edge} tone="cyan" />
          </div>
        </div>

        <div className="elite-card-pro">
          <h3>Mercado</h3>
          <div className="elite-mini-table">
            <p><b>Estado:</b> {translate(item.market_status)}</p>
            <p><b>Línea:</b> {n(item.line)}</p>
            <p><b>Cuota:</b> {n(item.odds)}</p>
            <p><b>Bookmaker:</b> {n(item.bookmaker)}</p>
          </div>
          <small className="elite-note">
            Si no existe mercado real validado, el panel debe tratarlo como lectura interna o pendiente.
          </small>
        </div>

        <div className="elite-card-pro">
          <h3>Eventos recientes</h3>
          {events.length === 0 ? (
            <p className="elite-muted">No hay eventos recientes entregados por la API.</p>
          ) : (
            <div className="elite-events">
              {events.map((ev, i) => (
                <div key={i} className="elite-event-row">
                  <b>{n(ev.time?.elapsed || ev.minute, "-")}'</b>
                  <span>{n(ev.type || ev.detail)}</span>
                  <small>{n(ev.team?.name || ev.team)}</small>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
      }
