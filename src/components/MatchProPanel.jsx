export default function MatchProPanel({ item }) {
  if (!item) return null;

  const market = String(item?.market || item?.type || "OVER").toUpperCase();
  const isUnder = market.includes("UNDER");
  const score = item?.score || "0-0";

  const confidence =
    item?.confidence ||
    item?.confidence_label ||
    item?.rank ||
    "MEDIA";

  const nextGoalBias = item?.next_goal_bias || "NEUTRAL";
  const nextGoalConfidence = Number(item?.next_goal_confidence || 0);
  const holdProbability = Number(item?.score_hold_probability || 0);

  return (
    <section className="match-pro-panel">
      <div className="match-pro-main">
        <div className="match-pro-league">
          <span>🏆</span>
          {item?.league || "Liga no disponible"}
        </div>

        <div className="match-pro-teams">
          <div className="match-pro-team">
            <TeamLogoMini logo={item?.home_logo} name={item?.home} />
            <strong>{item?.home || "Local"}</strong>
            <small>Local</small>
          </div>

          <div className="match-pro-score">
            <b>{score}</b>
            <span>EN VIVO · Min {item?.minute || 0}</span>
          </div>

          <div className="match-pro-team">
            <TeamLogoMini logo={item?.away_logo} name={item?.away} />
            <strong>{item?.away || "Visitante"}</strong>
            <small>Visitante</small>
          </div>
        </div>

        <div className="match-pro-strip">
          <ProMiniBox label="Mercado" value={isUnder ? "UNDER" : "OVER"} />
          <ProMiniBox label="Rango" value={item?.rank || "BUENA"} accent />
          <ProMiniBox label="Confianza" value={confidence} />
          <ProMiniBox label="Estado" value={item?.next_goal_status || "CONFIRMATION"} green />
        </div>
      </div>

      <div className="match-pro-cards">
        <InfoPanel title="🔥 Lectura del partido">
          <InfoLine label="Presión" value={item?.reading_strength || item?.context_state || "MEDIA"} />
          <InfoLine label="Ritmo" value={item?.match_temperature || item?.momentum_label || "N/A"} />
          <InfoLine label="Dominio" value={item?.dominance || "N/A"} />
          <InfoLine label="Calidad datos" value={item?.data_quality || "N/A"} />
          <p>{item?.reading_advice || "Lectura pendiente del partido."}</p>
        </InfoPanel>

        <InfoPanel title="🎯 Lectura próximo gol">
          <InfoLine label="Sesgo" value={nextGoalBias} />
          <BarLine label="Prob. próximo gol" value={nextGoalConfidence} />
          <BarLine label="Mantener marcador" value={holdProbability} />
          <InfoLine label="Soporte" value={item?.next_goal_support || "N/A"} />
          <p>{item?.next_goal_helper_advice || "Lectura auxiliar sin modificar la señal."}</p>
        </InfoPanel>

        <InfoPanel title="🛡 Riesgo">
          <InfoLine label="Nivel" value={item?.risk_level || "N/A"} />
          <InfoLine label="Risk Score" value={item?.risk_score || "0.0"} />
          <InfoLine label="Señal" value={item?.signal_score || "0.0"} />
          <InfoLine label="AI" value={item?.ai_score || "0.0"} />
          <p>{item?.next_goal_helper_warning || "Sin advertencias fuertes."}</p>
        </InfoPanel>
      </div>
    </section>
  );
}

function TeamLogoMini({ logo, name }) {
  const fallback = `https://ui-avatars.com/api/?name=${encodeURIComponent(
    name || "TEAM"
  )}&background=071827&color=00ffcc&size=128&bold=true&format=png`;

  return (
    <div className="match-pro-logo">
      <img src={logo || fallback} alt={name || "team"} />
    </div>
  );
}

function ProMiniBox({ label, value, accent = false, green = false }) {
  return (
    <div className={`pro-mini-box ${accent ? "accent" : ""} ${green ? "green" : ""}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function InfoPanel({ title, children }) {
  return (
    <div className="match-info-panel">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function InfoLine({ label, value }) {
  return (
    <div className="match-info-line">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function BarLine({ label, value }) {
  const safe = Math.max(0, Math.min(100, Number(value || 0)));

  return (
    <div className="bar-line">
      <div>
        <span>{label}</span>
        <b>{safe.toFixed(0)}%</b>
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${safe}%` }} />
      </div>
    </div>
  );
      }
