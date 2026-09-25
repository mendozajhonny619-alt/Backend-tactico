import React from "react";

const val = (v, fb = "N/A") =>
  v === undefined || v === null || v === "" ? fb : v;

const num = (v, fb = 0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fb;
};

const pct = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "N/A";
  return `${n.toFixed(0)}%`;
};

const marketLabel = (item) => {
  const market = String(item?.market || item?.type || "").toUpperCase();
  if (market.includes("UNDER")) return "DEBAJO / MENOS GOLES";
  if (market.includes("OVER") || market.includes("MAS") || market.includes("MÁS"))
    return "ENCIMA / MÁS GOLES";
  return "OBSERVAR";
};

const stateSpanish = (v) => {
  const text = String(v || "").toUpperCase();

  const map = {
    PREMIUM: "PREMIUM",
    FUERTE: "FUERTE",
    BUENA: "BUENA",
    OPERABLE: "OPERABLE",
    OBSERVACION: "OBSERVACIÓN",
    HIGH: "ALTA",
    MEDIUM: "MEDIA",
    LOW: "BAJA",
    BAJO: "BAJO",
    MEDIO: "MEDIO",
    ALTO: "ALTO",
    MUY_CALIENTE: "MUY CALIENTE",
    CALIENTE: "CALIENTE",
    TIBIO: "TIBIO",
    CONTROLADO: "CONTROLADO",
    FRIO: "FRÍO",
    MUERTO: "MUERTO",
    HOME: "LOCAL",
    AWAY: "VISITANTE",
    NEUTRAL: "NEUTRAL",
    BALANCED: "EQUILIBRADO",
    ENTER_OK: "ENTRADA VÁLIDA",
    WAIT_CONFIRMATION: "ESPERAR CONFIRMACIÓN",
    NO_REENTRY: "NO REENTRAR",
    AVOID: "EVITAR",
    INTERNAL_ONLY: "MERCADO INTERNO",
    PENDING: "MERCADO PENDIENTE",
  };

  return map[text] || text || "N/A";
};

function buildLiveReading(item) {
  const ai = num(item?.ai_score);
  const signal = num(item?.signal_score || item?.decision_score);
  const goal = num(item?.goal_probability);
  const over = num(item?.over_probability);
  const under = num(item?.under_probability);
  const risk = num(item?.risk_score);
  const pressure = num(item?.pressure_index || item?.home_next_goal_pressure || item?.away_next_goal_pressure);
  const rhythm = num(item?.rhythm_index);

  const market = String(item?.market || "").toUpperCase();
  const marketProb = market.includes("UNDER") ? under : over;

  let temperature = "NEUTRAL";
  if (goal >= 85 && signal >= 75) temperature = "MUY CALIENTE";
  else if (goal >= 70 && signal >= 65) temperature = "CALIENTE";
  else if (goal >= 58 || signal >= 58) temperature = "TIBIO";
  else if (goal <= 45 && signal <= 50) temperature = "FRÍO";

  let riskText = "MEDIO";
  if (risk <= 3.5) riskText = "BAJO";
  else if (risk >= 7) riskText = "ALTO";

  let recommendation = "OBSERVAR";
  if (riskText === "ALTO") recommendation = "EVITAR";
  else if (ai >= 70 && signal >= 70 && goal >= 70 && marketProb >= 65) {
    recommendation = "SEÑAL VALIDADA";
  } else if (ai >= 60 && signal >= 60) {
    recommendation = "ESPERAR CONFIRMACIÓN";
  }

  return {
    ai,
    signal,
    goal,
    over,
    under,
    risk,
    pressure,
    rhythm,
    marketProb,
    temperature,
    riskText,
    recommendation,
  };
}

export default function EliteDashboardPro({
  featured,
  uniqueSignals = [],
  opportunitySections = {},
  onOpen,
}) {
  const item = featured || uniqueSignals?.[0] || null;

  if (!item) {
    return (
      <section className="champions-dashboard empty">
        <div className="champions-empty-card">
          <h1>JHONNY ELITE V16</h1>
          <p>No hay señales activas ahora mismo.</p>
          <span>El sistema seguirá escaneando partidos en vivo.</span>
        </div>
      </section>
    );
  }

  const reading = buildLiveReading(item);

  const liveSignals = [
    ...(uniqueSignals || []),
    ...(opportunitySections?.over || []),
    ...(opportunitySections?.under || []),
  ].slice(0, 6);

  return (
    <section className="champions-dashboard">
      <div className="champions-hero">
        <div className="hero-bg-glow" />

        <div className="champions-header-line">
          <div>
            <h1>JHONNY <span>ELITE</span> V16</h1>
            <p>Lectura táctica y predicción contextual en tiempo real</p>
          </div>

          <div className="system-kpis">
            <Kpi title="Sistema" value="ACTIVO" tone="green" />
            <Kpi title="Señales" value={uniqueSignals.length} />
            <Kpi title="Temperatura" value={reading.temperature} tone="orange" />
            <Kpi title="Riesgo" value={reading.riskText} tone={reading.riskText === "ALTO" ? "red" : "green"} />
          </div>
        </div>

        <div className="match-stage">
          <TeamBlock
            logo={item?.home_logo}
            name={item?.home || item?.home_name || "Local"}
            label="Local"
          />

          <div className="score-center">
            <div className="league-pill">
              {val(item?.country)} · {val(item?.league || item?.liga)}
            </div>

            <div className="score-big">{val(item?.score || "0-0")}</div>

            <div className="live-minute">
              EN VIVO · MIN {val(item?.minute || item?.minuto || 0)}
            </div>

            <div className="market-pill-main">
              {marketLabel(item)}
            </div>
          </div>

          <TeamBlock
            logo={item?.away_logo}
            name={item?.away || item?.away_name || "Visitante"}
            label="Visitante"
          />
        </div>

        <div className="decision-band">
          <InfoBox label="Rango" value={stateSpanish(item?.rank || item?.signal_rank)} />
          <InfoBox label="IA" value={reading.ai.toFixed(1)} />
          <InfoBox label="Señal" value={reading.signal.toFixed(1)} />
          <InfoBox label="Gol" value={pct(reading.goal)} />
          <InfoBox label="Decisión" value={reading.recommendation} highlight />
        </div>
      </div>

      <div className="champions-grid">
        <Panel title="Lectura del partido" icon="🔥">
          <Row label="Contexto" value={stateSpanish(item?.context_state)} />
          <Row label="Momentum" value={stateSpanish(item?.momentum_label)} />
          <Row label="Dominio" value={stateSpanish(item?.dominance)} />
          <Row label="Presión" value={reading.pressure ? reading.pressure.toFixed(1) : "N/A"} />
          <Row label="Ritmo" value={reading.rhythm ? reading.rhythm.toFixed(1) : "N/A"} />

          <p className="panel-explain">
            {item?.decision_advice ||
              item?.revalidation_advice ||
              item?.deep_analysis_summary ||
              "La lectura se calcula con presión, ritmo, probabilidad de gol, riesgo y estado de la señal."}
          </p>
        </Panel>

        <Panel title="Probabilidad próximo gol" icon="🎯">
          <div className="circle-prob">
            <strong>{pct(item?.next_goal_confidence || item?.goal_probability)}</strong>
            <span>{stateSpanish(item?.next_goal_bias || "NEUTRAL")}</span>
          </div>

          <Row label="Soporte" value={stateSpanish(item?.next_goal_support)} />
          <Row label="Retención marcador" value={pct(item?.score_hold_probability)} />

          <p className="panel-explain">
            {item?.next_goal_helper_advice ||
              "El sistema compara presión local/visitante, ritmo y tendencia ofensiva para estimar el próximo escenario."}
          </p>
        </Panel>

        <Panel title="Estadísticas en vivo" icon="📊">
          <Compare label="Tiros" home={item?.home_stats?.shots} away={item?.away_stats?.shots} />
          <Compare label="Tiros al arco" home={item?.home_stats?.shots_on_target} away={item?.away_stats?.shots_on_target} />
          <Compare label="Corners" home={item?.home_stats?.corners} away={item?.away_stats?.corners} />
          <Compare label="Ataques peligrosos" home={item?.home_stats?.dangerous_attacks} away={item?.away_stats?.dangerous_attacks} />
          <Compare label="Posesión" home={item?.possession_home || item?.home_stats?.possession} away={item?.possession_away || item?.away_stats?.possession} />
        </Panel>

        <Panel title="Validación de la señal" icon="✅">
          <Check label="Ventana táctica" value={stateSpanish(item?.window_phase)} />
          <Check label="Revalidación" value={stateSpanish(item?.revalidation_status)} />
          <Check label="Vida de señal" value={stateSpanish(item?.signal_life_status || item?.signal_decay_status)} />
          <Check label="Mercado" value={stateSpanish(item?.market_status)} />
          <Check label="Riesgo" value={reading.riskText} />

          <button className="open-detail-btn" onClick={() => onOpen?.(item)}>
            Ver detalle táctico
          </button>
        </Panel>

        <Panel title="Análisis de riesgo" icon="🛡️">
          <div className={`risk-meter risk-${reading.riskText.toLowerCase()}`}>
            <span>BAJO</span>
            <div>
              <i style={{ width: `${Math.min(100, reading.risk * 10)}%` }} />
            </div>
            <span>ALTO</span>
          </div>

          <p className="panel-explain">
            {item?.risk_reducer_reason ||
              item?.next_goal_helper_warning ||
              "El riesgo se interpreta con base en minuto, presión real, enfriamiento, retención de marcador y calidad de datos."}
          </p>
        </Panel>

        <Panel title="Señales live actuales" icon="⚡">
          <div className="live-list">
            {liveSignals.length === 0 ? (
              <span className="no-live">No hay señales live.</span>
            ) : (
              liveSignals.map((s, i) => (
                <button key={i} onClick={() => onOpen?.(s)}>
                  <span>{val(s?.match_name || `${s?.home} vs ${s?.away}`)}</span>
                  <b>{marketLabel(s)}</b>
                  <em>{num(s?.signal_score || s?.decision_score).toFixed(1)}</em>
                </button>
              ))
            )}
          </div>
        </Panel>
      </div>
    </section>
  );
}

function Kpi({ title, value, tone = "" }) {
  return (
    <div className={`champions-kpi ${tone}`}>
      <span>{title}</span>
      <b>{value}</b>
    </div>
  );
}

function TeamBlock({ logo, name, label }) {
  const fallback = `https://ui-avatars.com/api/?name=${encodeURIComponent(
    name || "TEAM"
  )}&background=06182c&color=00ffcc&bold=true&size=128`;

  return (
    <div className="team-block-champions">
      <img src={logo || fallback} alt={name} />
      <h2>{name}</h2>
      <span>{label}</span>
    </div>
  );
}

function InfoBox({ label, value, highlight }) {
  return (
    <div className={`decision-box ${highlight ? "highlight" : ""}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function Panel({ title, icon, children }) {
  return (
    <div className="champions-panel">
      <h3>{icon} {title}</h3>
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="champions-row">
      <span>{label}</span>
      <b>{val(value)}</b>
    </div>
  );
}

function Compare({ label, home, away }) {
  const h = num(home);
  const a = num(away);
  const total = h + a;
  const hp = total > 0 ? (h / total) * 100 : 50;
  const ap = total > 0 ? (a / total) * 100 : 50;

  return (
    <div className="compare-row">
      <div>
        <b>{val(home, "-")}</b>
        <span>{label}</span>
        <b>{val(away, "-")}</b>
      </div>

      <section>
        <i style={{ width: `${hp}%` }} />
        <em style={{ width: `${ap}%` }} />
      </section>
    </div>
  );
}

function Check({ label, value }) {
  return (
    <div className="check-row">
      <span>✓</span>
      <b>{label}</b>
      <em>{val(value)}</em>
    </div>
  );
    }
