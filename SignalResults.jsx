export default function SignalResults({ summary, rows = [] }) {
  const safeSummary = summary || {
    aciertos: 0,
    fallos: 0,
    activas: 0,
  };

  return (
    <div className="results-view-wrap">
      <div className="results-main-box">
        <div className="results-title">⚡ RENDIMIENTO DE SEÑALES IA</div>

        <div className="results-summary-grid">
          <div className="results-summary-card success">
            <div className="results-summary-label">Aciertos</div>
            <div className="results-summary-value">{safeSummary.aciertos || 0}</div>
          </div>

          <div className="results-summary-card fail">
            <div className="results-summary-label">Fallos</div>
            <div className="results-summary-value">{safeSummary.fallos || 0}</div>
          </div>

          <div className="results-summary-card active">
            <div className="results-summary-label">Pendientes</div>
            <div className="results-summary-value">{safeSummary.activas || 0}</div>
          </div>
        </div>

        <div className="results-subtitle history">HISTORIAL DE PRONÓSTICOS</div>

        <div className="results-history-list pro">
          {!rows.length ? (
            <div className="empty-box">No hay historial disponible todavía.</div>
          ) : (
            rows.map((item, index) => {
              const state = normalizeHistoryState(item);
              const home = getHomeName(item);
              const away = getAwayName(item);
              const league = item.liga || item.league || "Sin liga";
              const country = item.pais || item.país || item.country || "";
              const minute = item.minuto ?? item.minute ?? "-";
              const score = item.marcador_entrada || item.score || "0-0";
              const market = item.mercado || item.market;

              return (
                <div
                  key={`${item.id || item.signal_key || item.match_id || index}`}
                  className={`history-pro-row ${state.className} ${marketCardClass(market)}`}
                >
                  <div className="history-pro-teams">
                    <div className="history-league-line">
                      <img src={getFlagUrl(country)} alt={country || "flag"} />
                      <span>{league}</span>
                    </div>

                    <div className="history-teams-box">
                      <TeamLogo name={home} logo={item.home_logo || item.local_logo} />
                      <div className="history-vs">VS</div>
                      <TeamLogo name={away} logo={item.away_logo || item.visitor_logo} />
                    </div>

                    <div className="history-team-names">
                      <span>{home}</span>
                      <span>{away}</span>
                    </div>
                  </div>

                  <div className="history-pro-signal">
                    <div className={`history-market-title ${getMarketType(market)}`}>
                      {formatMarketLabel(market)}
                    </div>

                    <div className="history-entry-line">
                      Min {minute} · Marcador entrada {score}
                    </div>

                    <div className="history-mini-grid">
                      <MetricBox label="IA" value={roundNum(item.ai_score || 0)} />
                      <MetricBox label="Señal" value={roundNum(item.signal_score || 0)} />
                      <MetricBox label="Gol %" value={`${roundNum(item.goal_probability || 0)}%`} />
                      <MetricBox label="Encima %" value={`${roundNum(item.over_probability || 0)}%`} />
                      <MetricBox
                        label="Confianza"
                        value={item.confidence || item.confidence_label || confidenceFromItem(item)}
                        strong
                      />
                    </div>
                  </div>

                  <div className="history-pro-score">
                    <span>Marcador final</span>
                    <b>{item.final_score || item.score || score}</b>
                    <small>{formatTimestamp(item.closed_at || item.created_at || item.timestamp)}</small>
                  </div>

                  <div className={`history-pro-status ${state.className}`}>
                    <span>Estado</span>
                    <b>{state.label}</b>
                    <small>{state.className === "activa" ? "En espera" : "Cerrada"}</small>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

function TeamLogo({ name, logo }) {
  const fallback = getTeamAvatar(name);

  return (
    <div className="team-logo history-logo">
      <img
        src={logo || fallback}
        alt={name || "team"}
        onError={(e) => {
          e.currentTarget.src = fallback;
        }}
      />
    </div>
  );
}

function MetricBox({ label, value, strong = false }) {
  return (
    <div className={`history-metric-box ${strong ? "strong" : ""}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function getHomeName(item) {
  return (
    item.home_name ||
    item.nombre_local ||
    item.home ||
    item.local ||
    extractHomeAway(item.partido || item.match_name).home ||
    "Local"
  );
}

function getAwayName(item) {
  return (
    item.away_name ||
    item.nombre_visitante ||
    item.nombre_visita ||
    item.away ||
    item.visitante ||
    extractHomeAway(item.partido || item.match_name).away ||
    "Visitante"
  );
}

function extractHomeAway(name = "") {
  const text = String(name || "");
  const parts = text.includes(" vs ")
    ? text.split(" vs ")
    : text.includes(" contra ")
      ? text.split(" contra ")
      : [];

  return {
    home: parts[0] || "",
    away: parts[1] || "",
  };
}

function getTeamAvatar(name) {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(
    name || "TEAM"
  )}&background=071827&color=00ffcc&size=128&bold=true&format=png`;
}

function getFlagUrl(country = "") {
  const c = String(country || "").toLowerCase();

  const map = {
    argentina: "ar",
    colombia: "co",
    chile: "cl",
    ecuador: "ec",
    mexico: "mx",
    méxico: "mx",
    "ee.uu.": "us",
    "eeuu": "us",
    usa: "us",
    "estados unidos": "us",
    brazil: "br",
    brasil: "br",
    spain: "es",
    españa: "es",
    italy: "it",
    italia: "it",
    england: "gb",
    inglaterra: "gb",
    france: "fr",
    francia: "fr",
    germany: "de",
    alemania: "de",
    portugal: "pt",
    paraguay: "py",
    peru: "pe",
    perú: "pe",
    uruguay: "uy",
    venezuela: "ve",
    iraq: "iq",
  };

  const key = Object.keys(map).find((x) => c.includes(x));
  const code = key ? map[key] : "un";

  return `https://flagcdn.com/w40/${code}.png`;
}

function normalizeHistoryState(item) {
  const value = String(
    item.resultado_final ||
      item.resultado ||
      item.status ||
      item.final_status ||
      "PENDIENTE"
  ).toUpperCase();

  if (["WIN", "ACERTADA", "GANADA", "CUMPLIDA"].includes(value)) {
    return { label: "ACERTADA", className: "acertada" };
  }

  if (["LOSS", "FALLIDA", "PERDIDA", "EXPIRADA"].includes(value)) {
    return { label: "FALLIDA", className: "fallida" };
  }

  if (value === "FINALIZADA") {
    return { label: "FINALIZADA", className: "finalizada" };
  }

  if (value === "DESCARTADA") {
    return { label: "DESCARTADA", className: "descartada" };
  }

  return { label: "PENDIENTE", className: "activa" };
}

function confidenceFromItem(item) {
  const ai = Number(item.ai_score || 0);
  const signal = Number(item.signal_score || 0);
  const goal = Number(item.goal_probability || 0);
  const over = Number(item.over_probability || 0);

  const score = ai * 0.3 + signal * 0.3 + goal * 0.2 + over * 0.2;

  if (score >= 85) return "MUY ALTA";
  if (score >= 70) return "ALTA";
  if (score >= 55) return "MEDIA";
  if (score >= 40) return "BAJA";
  return "MUY BAJA";
}

function roundNum(value) {
  return Number(value || 0).toFixed(1);
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "Sin fecha";

  try {
    const d = new Date(timestamp);
    if (Number.isNaN(d.getTime())) return String(timestamp);
    return d.toLocaleString();
  } catch {
    return String(timestamp);
  }
}

function getMarketType(market) {
  const value = String(market || "").toUpperCase();

  if (value.includes("UNDER") || value.includes("BAJO")) return "under";
  if (value.includes("OVER") || value.includes("MÁS") || value.includes("MAS")) return "over";
  return "neutral";
}

function marketCardClass(market) {
  return `market-${getMarketType(market)}`;
}

function formatMarketLabel(market) {
  const type = getMarketType(market);
  if (type === "under") return "DEBAJO";
  if (type === "over") return "ENCIMA";
  return String(market || "MERCADO");
}
