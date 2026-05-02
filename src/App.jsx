import { useEffect, useMemo, useState } from "react";
import "./styles.css";

const API = "https://backend-tactico-lqok.onrender.com";

export default function App() {
  const [stats, setStats] = useState(null);
  const [signals, setSignals] = useState([]);
  const [history, setHistory] = useState([]);
  const [opportunities, setOpportunities] = useState({
    summary: {},
    sections: {
      over_candidates: [],
      under_candidates: [],
      observe: [],
      rejected: [],
    },
  });

  const [lastUpdate, setLastUpdate] = useState("");
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [activeTab, setActiveTab] = useState("results");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    loadAll();

    const interval = setInterval(() => {
      loadAll();
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  async function loadAll() {
    try {
      const [statsRes, signalsRes, historyRes, opportunitiesRes] =
        await Promise.all([
          fetch(`${API}/stats`, { cache: "no-store" }),
          fetch(`${API}/signals`, { cache: "no-store" }),
          fetch(`${API}/history`, { cache: "no-store" }),
          fetch(`${API}/opportunities`, { cache: "no-store" }),
        ]);

      const [statsData, signalsData, historyData, opportunitiesData] =
        await Promise.all([
          statsRes.json(),
          signalsRes.json(),
          historyRes.json(),
          opportunitiesRes.json(),
        ]);

      setStats(statsData?.stats || statsData || null);
      setSignals(normalizeItems(signalsData).map(normalizeMatchItem));
      setHistory(normalizeItems(historyData).map(normalizeMatchItem));

      const sections = opportunitiesData?.sections || {};

      setOpportunities({
        summary: opportunitiesData?.summary || {},
        sections: {
          over_candidates: normalizeList(sections.over_candidates),
          under_candidates: normalizeList(sections.under_candidates),
          observe: normalizeList(sections.observe),
          rejected: normalizeList(sections.rejected),
        },
      });

      setLastUpdate(new Date().toLocaleTimeString());
      setErrorMsg("");
    } catch (err) {
      console.error("Error cargando panel:", err);
      setStats(null);
      setSignals([]);
      setHistory([]);
      setErrorMsg("No se pudieron cargar los datos del panel.");
    }
  }

  const uniqueSignals = useMemo(() => {
    return dedupeItems(signals).sort((a, b) => getStrength(b) - getStrength(a));
  }, [signals]);

  const opportunitySections = useMemo(() => {
    return {
      over: dedupeItems(opportunities.sections.over_candidates).sort(
        (a, b) => getStrength(b) - getStrength(a)
      ),
      under: dedupeItems(opportunities.sections.under_candidates).sort(
        (a, b) => getStrength(b) - getStrength(a)
      ),
      observe: dedupeItems(opportunities.sections.observe).sort(
        (a, b) => getStrength(b) - getStrength(a)
      ),
    };
  }, [opportunities]);

  const featured =
    uniqueSignals[0] ||
    opportunitySections.over[0] ||
    opportunitySections.under[0] ||
    opportunitySections.observe[0] ||
    null;

  const selectedLiveMatch = useMemo(() => {
    if (!selectedMatch) return null;

    const selectedKey = getStableMatchKey(selectedMatch);

    const allItems = [
      ...uniqueSignals,
      ...opportunitySections.over,
      ...opportunitySections.under,
      ...opportunitySections.observe,
      ...history,
    ];

    return (
      allItems.find((item) => getStableMatchKey(item) === selectedKey) ||
      allItems.find(
        (item) =>
          item?.match_id &&
          selectedMatch?.match_id &&
          item.match_id === selectedMatch.match_id
      ) ||
      selectedMatch
    );
  }, [selectedMatch, uniqueSignals, opportunitySections, history]);

  const historySummary = useMemo(() => {
    const rows = Array.isArray(history) ? history : [];
    const total = rows.length;
    const wins = rows.filter((r) => resultType(r) === "win").length;
    const losses = rows.filter((r) => resultType(r) === "loss").length;
    const pending = rows.filter((r) =>
      ["pending", "active"].includes(resultType(r))
    ).length;
    const precision = wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0;

    return {
      total,
      wins,
      losses,
      pending,
      precision,
      streak: wins,
      roi: total > 0 ? wins * 1.25 - losses : 0,
    };
  }, [history]);

  const headerStats = {
    status: "ACTIVO",
    signals: uniqueSignals.length,
    liveMatches: Number(
      stats?.live_matches_count ??
        stats?.scanned_matches ??
        stats?.live_matches ??
        0
    ),
    accuracy: historySummary.precision,
    history: historySummary.total,
    updatedAt: lastUpdate || "--:--:--",
  };

  if (selectedMatch) {
    return (
      <div className="app">
        <div className="overlay">
          <div className="container">
            <div className="detail-topbar">
              <button className="back-btn" onClick={() => setSelectedMatch(null)}>
                ← Volver al panel
              </button>

              <div className="detail-update">
                Última actualización: {lastUpdate || "--:--:--"}
              </div>
            </div>

            <DetailView item={selectedLiveMatch || selectedMatch} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="overlay">
        <div className="container">
          <Header stats={headerStats} />

          <nav className="pro-nav">
            <NavButton id="signals" activeTab={activeTab} setActiveTab={setActiveTab} icon="⚡">
              Señales
            </NavButton>

            <NavButton id="opportunities" activeTab={activeTab} setActiveTab={setActiveTab} icon="🛡️">
              Oportunidades
            </NavButton>

            <NavButton id="results" activeTab={activeTab} setActiveTab={setActiveTab} icon="🏆">
              Resultados
            </NavButton>

            <NavButton id="stats" activeTab={activeTab} setActiveTab={setActiveTab} icon="📊">
              Estadísticas
            </NavButton>

            <NavButton id="config" activeTab={activeTab} setActiveTab={setActiveTab} icon="⚙️">
              Configuración
            </NavButton>
          </nav>

          {errorMsg ? <div className="empty-box">{errorMsg}</div> : null}

          {activeTab === "signals" && (
            <>
              {featured && <FeaturedSignal item={featured} />}

              <Section
                title="🔥 SEÑALES ACTIVAS"
                items={uniqueSignals}
                empty="No hay señales activas ahora mismo."
                onOpen={setSelectedMatch}
              />
            </>
          )}

          {activeTab === "opportunities" && (
            <>
              <Section
                title="🔥 OPORTUNIDADES OVER"
                items={opportunitySections.over}
                empty="No hay oportunidades OVER ahora mismo."
                onOpen={setSelectedMatch}
              />

              <Section
                title="❄️ POSIBLES UNDER"
                items={opportunitySections.under}
                empty="No hay oportunidades UNDER ahora mismo."
                onOpen={setSelectedMatch}
              />

              <Section
                title="👁 EN OBSERVACIÓN"
                items={opportunitySections.observe}
                empty="No hay partidos en observación."
                onOpen={setSelectedMatch}
              />
            </>
          )}

          {activeTab === "results" && (
            <ResultsProView history={history} summary={historySummary} />
          )}

          {activeTab === "stats" && <ComingSoon title="📊 Estadísticas" />}
          {activeTab === "config" && <ComingSoon title="⚙️ Configuración" />}
        </div>
      </div>
    </div>
  );
}

function Header({ stats }) {
  return (
    <header className="pro-header">
      <div className="brand">
        <div className="brand-icon">⚡</div>
        <div className="brand-title">
          JHONNY <span>ELITE</span> V16
        </div>
      </div>

      <div className="top-kpis">
        <TopKpi title="Estado" value={stats.status} tone="green" />
        <TopKpi title="Señales" value={stats.signals} />
        <TopKpi title="Partidos hoy" value={stats.liveMatches} />
        <TopKpi title="Aciertos" value={`${stats.accuracy.toFixed(1)}%`} tone="green" />
        <TopKpi title="Historial" value={stats.history} />
        <TopKpi title="Actualización" value={stats.updatedAt} tone="green" />
      </div>
    </header>
  );
}

function TopKpi({ title, value, tone = "" }) {
  return (
    <div className="top-kpi">
      <span>{title}</span>
      <b className={tone}>{value}</b>
    </div>
  );
}

function NavButton({ id, activeTab, setActiveTab, icon, children }) {
  return (
    <button
      className={`pro-nav-btn ${activeTab === id ? "active" : ""}`}
      onClick={() => setActiveTab(id)}
    >
      <span>{icon}</span>
      {children}
    </button>
  );
}

function ResultsProView({ history, summary }) {
  return (
    <section className="results-screen">
      <div className="panel-title-row">
        <h2>🏆 RENDIMIENTO DE SEÑALES IA</h2>
      </div>

      <div className="performance-grid">
        <PerformanceCard icon="✅" title="Aciertos" value={summary.wins} sub={`${summary.total ? ((summary.wins / summary.total) * 100).toFixed(1) : "0.0"}%`} tone="win" />
        <PerformanceCard icon="❌" title="Fallos" value={summary.losses} sub={`${summary.total ? ((summary.losses / summary.total) * 100).toFixed(1) : "0.0"}%`} tone="loss" />
        <PerformanceCard icon="⏳" title="Pendientes" value={summary.pending} sub={`${summary.total ? ((summary.pending / summary.total) * 100).toFixed(1) : "0.0"}%`} tone="pending" />
        <PerformanceCard icon="🎯" title="Precisión" value={`${summary.precision.toFixed(1)}%`} sub={`(${summary.wins} / ${summary.wins + summary.losses})`} tone="precision" />
        <PerformanceCard icon="📈" title="ROI" value={`${summary.roi >= 0 ? "+" : ""}${summary.roi.toFixed(2)}%`} sub="Beneficio" tone="roi" />
        <PerformanceCard icon="🔥" title="Racha actual" value={summary.streak} sub="Acertadas" tone="streak" />
      </div>

      <div className="history-panel-pro">
        <div className="history-panel-head">
          <h2>HISTORIAL DE SEÑALES</h2>

          <div className="history-filters">
            <button>📅 Filtrar fecha</button>
            <button>☰ Todos los estados</button>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="empty-box">No hay historial disponible todavía.</div>
        ) : (
          <div className="history-list-pro">
            {history.map((item, index) => (
              <HistoryRowPro key={buildKey(item, index)} item={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function PerformanceCard({ icon, title, value, sub, tone }) {
  return (
    <div className={`performance-card ${tone}`}>
      <div className="performance-icon">{icon}</div>
      <div>
        <span>{title}</span>
        <b>{value}</b>
        <small>{sub}</small>
      </div>
    </div>
  );
}

function HistoryRowPro({ item }) {
  const result = resultType(item);
  const confidence = getConfidence(item);
  const typeClass = safeTypeClass(item);

  return (
    <article className={`history-row-pro ${result}`}>
      <div className="history-teams-pro">
        <LeagueLine item={item} compact />

        <div className="teams-versus">
          <div className="team-side">
            <TeamLogo item={item} side="home" />
            <span>{safeText(item?.home)}</span>
          </div>

          <div className="versus">vs</div>

          <div className="team-side">
            <TeamLogo item={item} side="away" />
            <span>{safeText(item?.away)}</span>
          </div>
        </div>
      </div>

      <div className="history-signal-pro">
        <div className={`market-title ${typeClass}`}>{getTypeLabel(item)}</div>

        <div className="signal-subline">
          Min {safeText(item?.minute ?? "-")} · Marcador entrada{" "}
          {safeText(item?.entry_score || item?.score || "0-0")}
        </div>

        <div className="metric-boxes">
          <MiniMetric label="IA" value={formatNum(item?.ai_score)} />
          <MiniMetric label="Señal" value={formatNum(item?.signal_score)} />
          <MiniMetric label="Gol %" value={`${formatNum(item?.goal_probability)}%`} />
          <MiniMetric
            label={typeClass === "under" ? "Under %" : "Over %"}
            value={`${formatNum(
              typeClass === "under" ? item?.under_probability : item?.over_probability
            )}%`}
          />
          <MiniMetric label="Confianza" value={confidence.label} strong />
        </div>
      </div>

      <div className="final-score-pro">
        <span>Marcador final</span>
        <b>{safeText(item?.final_score || item?.score || "0-0")}</b>
        <small>{safeText(item?.resolved_at || item?.created_at || item?.timestamp || "")}</small>
      </div>

      <div className={`status-pro ${result}`}>
        <span>Estado</span>
        <b>{resultLabel(item)}</b>
        <small>{resultProfit(item)}</small>
      </div>
    </article>
  );
}

function MiniMetric({ label, value, strong = false }) {
  return (
    <div className={`mini-metric ${strong ? "strong" : ""}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function Section({ title, items, empty, onOpen }) {
  return (
    <section className="group">
      <h3 className="group-title">{title}</h3>

      <div className="cards">
        {items.length === 0 ? (
          <div className="empty-box">{empty}</div>
        ) : (
          items.map((item, index) => (
            <SignalCard
              key={buildKey(item, index)}
              item={item}
              onOpen={() => onOpen(item)}
            />
          ))
        )}
      </div>
    </section>
  );
}

function SignalCard({ item, onOpen }) {
  const typeClass = safeTypeClass(item);
  const confidence = getConfidence(item);

  return (
    <article className={`card pro-card ${typeClass}`}>
      <div className="card-topline">
        <LeagueLine item={item} compact />
        <div className={`tiny-pill ${typeClass}`}>{getTypeLabel(item)}</div>
      </div>

      <div className="card-teams-pro">
        <TeamLogo item={item} side="home" />

        <div className="card-team-text">
          <h3>{safeText(item?.match_name)}</h3>
          <span>
            <LiveMinute item={item} /> · {safeText(item?.score || "0-0")}
          </span>
        </div>

        <TeamLogo item={item} side="away" />
      </div>

      <div className={`confidence-badge ${confidence.class}`}>
        Confianza: {confidence.label}
      </div>

      <div className="card-metrics-pro">
        <MiniMetric label="IA" value={formatNum(item?.ai_score)} />
        <MiniMetric label="Gol %" value={`${formatNum(item?.goal_probability)}%`} />
        <MiniMetric label="Over %" value={`${formatNum(item?.over_probability)}%`} />
        <MiniMetric label="Señal" value={formatNum(item?.signal_score)} />
      </div>

      <div className="card-footer-pro">
        <span>
          {safeText(item?.rank || item?.signal_rank || item?.window_phase || "N/A")}
        </span>
        <button onClick={onOpen}>Ver partido</button>
      </div>
    </article>
  );
}

function FeaturedSignal({ item }) {
  const confidence = getConfidence(item);
  const typeClass = safeTypeClass(item);

  return (
    <section className={`featured pro-featured ${typeClass}`}>
      <div className="featured-left">
        <div className="featured-kicker">DIRECTOR DE SEÑAL</div>
        <LeagueLine item={item} />

        <div className="featured-pro-teams">
          <TeamLogo item={item} side="home" size="featured" />

          <div>
            <h2>{safeText(item?.match_name)}</h2>

            <div className="featured-score-pro">
              <b>{safeText(item?.score || "0-0")}</b>
              <LiveMinute item={item} />
            </div>
          </div>

          <TeamLogo item={item} side="away" size="featured" />
        </div>

        <div className={`confidence-badge big ${confidence.class}`}>
          Confianza: {confidence.label}
        </div>

        <p>
          {safeText(item?.rank || item?.signal_rank || "N/A")} ·{" "}
          {safeText(item?.window_reason || item?.reason || item?.window_phase || "N/A")}
        </p>
      </div>

      <div className="featured-right">
        <div className={`market-pill large ${typeClass}`}>{getTypeLabel(item)}</div>

        <div className="featured-metrics-grid">
          <MiniMetric label="IA" value={formatNum(item?.ai_score)} />
          <MiniMetric label="Gol %" value={`${formatNum(item?.goal_probability)}%`} />
          <MiniMetric label="Over %" value={`${formatNum(item?.over_probability)}%`} />
          <MiniMetric label="Señal" value={formatNum(item?.signal_score)} />
          <MiniMetric label="Gate" value={formatNum(item?.gate_score)} />
          <MiniMetric label="Rango" value={safeText(item?.rank || "N/A")} strong />
        </div>
      </div>
    </section>
  );
}

function DetailView({ item }) {
  const confidence = getConfidence(item);
  const typeClass = safeTypeClass(item);
  const recommendation = getFinalRecommendation(item, confidence);
  const events = Array.isArray(item?.events) ? item.events : [];

  return (
    <div className="detail-premium">
      <section className={`detail-premium-hero ${typeClass}`}>
        <div className="premium-topline">
          <LeagueLine item={item} />
          <div className={`premium-market ${typeClass}`}>{getTypeLabel(item)}</div>
        </div>

        <div className="premium-match">
          <div className="premium-team">
            <TeamLogo item={item} side="home" size="featured" />
            <strong>{safeText(item?.home)}</strong>
          </div>

          <div className="premium-score-box">
            <h1>{safeText(item?.score || "0-0")}</h1>
            <LiveMinute item={item} />
            <div className={`premium-confidence ${confidence.class}`}>
              Confianza: {confidence.label}
            </div>
          </div>

          <div className="premium-team">
            <TeamLogo item={item} side="away" size="featured" />
            <strong>{safeText(item?.away)}</strong>
          </div>
        </div>

        <div className="premium-kpis">
          <MiniMetric label="IA" value={formatNum(item?.ai_score)} />
          <MiniMetric label="Señal" value={formatNum(item?.signal_score)} />
          <MiniMetric label="Gol %" value={`${formatNum(item?.goal_probability)}%`} />
          <MiniMetric
            label={typeClass === "under" ? "Under %" : "Over %"}
            value={`${formatNum(
              typeClass === "under" ? item?.under_probability : item?.over_probability
            )}%`}
          />
          <MiniMetric label="Riesgo" value={safeText(item?.risk_level || "N/A")} strong />
        </div>
      </section>

      <section className="premium-grid">
        <div className={`premium-card premium-final ${recommendation.class}`}>
          <h2>Lectura final PRO</h2>

          <div className="premium-final-title">
            {getTypeLabel(item)} - {safeText(item?.rank || "OPERABLE")}
          </div>

          <ul>
            <li>{recommendation.reason}</li>
            <li>Mercado: {safeText(item?.market)}</li>
            <li>Línea: {safeText(item?.line || "AUTO")}</li>
            <li>Estado mercado: {safeText(item?.market_status || "N/A")}</li>
          </ul>
        </div>

        <div className="premium-card">
          <h2>Lectura IA</h2>
          <InfoRow label="Ventana" value={item?.window_phase} />
          <InfoRow label="Razón" value={item?.window_reason || item?.reason} />
          <InfoRow label="Contexto" value={item?.context_state} />
          <InfoRow label="Momentum" value={item?.momentum_label} />
          <InfoRow label="Dominancia" value={item?.dominance} />
          <InfoRow label="Lado ataque" value={item?.attack_side} />
          <InfoRow label="Calidad datos" value={item?.data_quality} />
          <InfoRow label="Calidad partido" value={item?.game_quality} />
        </div>

        <div className="premium-card">
          <h2>Probabilidades</h2>
          <StatBar label="Puntuación IA" value={item?.ai_score} />
          <StatBar label="Probabilidad de gol" value={item?.goal_probability} />
          <StatBar label="Probabilidad OVER" value={item?.over_probability} />
          <StatBar label="Probabilidad UNDER" value={item?.under_probability} />
          <StatBar label="Signal Score" value={item?.signal_score} />
        </div>

        <div className="premium-card">
          <h2>Estadísticas del partido</h2>
          <InfoRow label="Marcador" value={item?.score || "0-0"} />
          <InfoRow label="Tiros" value={item?.shots ?? "N/A"} />
          <InfoRow label="Tiros al arco" value={item?.shots_on_target ?? "N/A"} />
          <InfoRow label="Corners" value={item?.corners ?? "N/A"} />
          <InfoRow label="Ataques peligrosos" value={item?.dangerous_attacks ?? "N/A"} />
          <InfoRow label="xG" value={item?.xg || item?.xG || "N/A"} />
          <InfoRow label="Rojas" value={item?.red_cards ?? "N/A"} />
        </div>

        <div className="premium-card">
          <h2>Riesgo / Value</h2>
          <InfoRow label="Riesgo" value={item?.risk_level} />
          <InfoRow label="Risk Score" value={formatNum(item?.risk_score)} />
          <InfoRow label="Cuota" value={item?.odds || "N/A"} />
          <InfoRow label="Bookmaker" value={item?.bookmaker || "N/A"} />
          <InfoRow label="Edge" value={item?.value_edge ?? "N/A"} />
          <InfoRow label="Value Category" value={item?.value_category || "N/A"} />
        </div>

        <div className="premium-card">
          <h2>Eventos del partido</h2>
          {events.length === 0 ? (
            <div className="empty-box">No hay eventos disponibles para este partido.</div>
          ) : (
            <div className="event-list">
              {events.slice(-10).reverse().map((event, index) => (
                <EventRow key={index} event={event} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function EventRow({ event }) {
  const type = String(event?.type || event?.raw_type || "EVENTO").toUpperCase();
  const detail = event?.detail || event?.comentario || "";
  const minute =
    event?.minute ??
    event?.elapsed ??
    event?.time?.elapsed ??
    "-";

  let icon = "•";
  if (type.includes("GOAL")) icon = "⚽";
  else if (type.includes("RED")) icon = "🟥";
  else if (type.includes("CARD")) icon = "🟨";
  else if (type.includes("VAR")) icon = "📺";
  else if (type.includes("SUB")) icon = "🔁";

  return (
    <div className="event-row">
      <span>{icon}</span>
      <b>{minute}'</b>
      <small>{safeText(type)}</small>
      <em>{safeText(detail || "Evento del partido")}</em>
    </div>
  );
}

function LiveMinute({ item }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const baseMinute = Number(item?.minute ?? item?.minuto ?? 0);
  const receivedAt = Number(item?._panel_received_at || now);
  const elapsedSeconds = Math.max(0, Math.floor((now - receivedAt) / 1000));
  const liveMinute = Math.min(120, baseMinute + Math.floor(elapsedSeconds / 60));
  const liveSeconds = elapsedSeconds % 60;

  return (
    <span className={`live-minute ${elapsedSeconds > 45 ? "delayed" : ""}`}>
      EN VIVO · Min {liveMinute}:{String(liveSeconds).padStart(2, "0")}
    </span>
  );
}

function ComingSoon({ title }) {
  return (
    <section className="coming-soon">
      <h2>{title}</h2>
      <p>Esta sección está lista para conectarse al siguiente módulo.</p>
    </section>
  );
}

function TeamLogo({ item, side = "home", size = "normal" }) {
  const name = side === "home" ? item?.home : item?.away;

  const logo =
    side === "home"
      ? item?.home_logo || item?.home_team_logo || item?.local_logo
      : item?.away_logo || item?.away_team_logo || item?.visitor_logo;

  const fallbackLogo = getTeamAvatar(name);

  return (
    <div className={`team-logo ${size}`}>
      <img
        src={logo || fallbackLogo}
        alt={safeText(name)}
        onError={(e) => {
          e.currentTarget.src = fallbackLogo;
        }}
      />
    </div>
  );
}

function LeagueLine({ item, compact = false }) {
  const flag = item?.country_flag || item?.flag || item?.league_flag;
  const logo = item?.league_logo || item?.competition_logo;
  const league = item?.league || item?.liga || "Liga no disponible";
  const country = item?.country || item?.pais || "";

  const fallbackFlag = getFlagUrl(country);

  return (
    <div className={`league-line ${compact ? "compact" : ""}`}>
      <img
        src={flag || logo || fallbackFlag}
        alt={league}
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
      <span>{safeText(league)}</span>
    </div>
  );
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
    "ee.uu": "us",
    "ee.uu.": "us",
    eeuu: "us",
    usa: "us",
    "estados unidos": "us",
    "united states": "us",
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
    bolivia: "bo",
    venezuela: "ve",
    iraq: "iq",
  };

  const key = Object.keys(map).find((x) => c.includes(x));
  const code = key ? map[key] : "un";

  return `https://flagcdn.com/w40/${code}.png`;
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <b>{safeText(value || "N/A")}</b>
    </div>
  );
}

function StatBar({ label, value }) {
  const safe = Math.max(0, Math.min(100, Number(value || 0)));

  return (
    <div className="statbar">
      <div className="statbar-top">
        <span>{label}</span>
        <b>{safe.toFixed(1)}</b>
      </div>

      <div className="statbar-track">
        <div className="statbar-fill" style={{ width: `${safe}%` }} />
      </div>
    </div>
  );
}

function normalizeList(value) {
  return Array.isArray(value) ? value.map(normalizeMatchItem) : [];
}

function normalizeItems(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.signals)) return payload.signals;
  if (Array.isArray(payload?.history)) return payload.history;
  if (Array.isArray(payload)) return payload;
  return [];
}

function normalizeMatchItem(item = {}) {
  const home =
    item?.home_name ||
    item?.nombre_local ||
    item?.home_team ||
    item?.home ||
    item?.local ||
    extractHomeAway(item?.match_name || item?.partido || item?.nombre_partido).home ||
    "Local";

  const away =
    item?.away_name ||
    item?.nombre_visitante ||
    item?.nombre_visita ||
    item?.away_team ||
    item?.away ||
    item?.visitante ||
    extractHomeAway(item?.match_name || item?.partido || item?.nombre_partido).away ||
    "Visitante";

  const matchName =
    item?.match_name ||
    item?.nombre_partido ||
    item?.partido ||
    `${home} vs ${away}`;

  return {
    ...item,
    home,
    away,
    match_name: matchName,
    league: item?.league || item?.liga || "Liga no disponible",
    country: item?.country || item?.pais || item?.país || "",
    minute: item?.minute ?? item?.minuto ?? 0,
    score: buildScore(item),
    home_logo: item?.home_logo || item?.home_team_logo || item?.local_logo,
    away_logo: item?.away_logo || item?.away_team_logo || item?.visitor_logo,
    league_logo: item?.league_logo || item?.competition_logo,
    country_flag: item?.country_flag || item?.flag || item?.league_flag,
    _panel_received_at: Date.now(),
  };
}

function extractHomeAway(name = "") {
  const text = String(name || "");

  if (text.includes(" vs ")) {
    const [home, away] = text.split(" vs ");
    return { home: home || "", away: away || "" };
  }

  if (text.includes(" contra ")) {
    const [home, away] = text.split(" contra ");
    return { home: home || "", away: away || "" };
  }

  return { home: "", away: "" };
}

function dedupeItems(list) {
  const map = new Map();

  for (const item of Array.isArray(list) ? list : []) {
    const key =
      item?.active_key ||
      item?.signal_key ||
      item?.match_id ||
      item?.id ||
      `${item?.match_name || ""}-${item?.market || item?.type || ""}-${
        item?.minute || ""
      }`;

    if (!map.has(key)) {
      map.set(key, item);
    } else {
      const current = map.get(key);
      if (getStrength(item) > getStrength(current)) {
        map.set(key, item);
      }
    }
  }

  return Array.from(map.values());
}

function getStrength(item) {
  return (
    Number(item?.strength_score || 0) +
    Number(item?.confidence_score || 0) +
    Number(item?.signal_score || 0) +
    Number(item?.ai_score || 0) +
    Number(item?.goal_probability || 0) * 0.2
  );
}

function getConfidence(item) {
  if (item?.confidence || item?.confidence_label) {
    const label = String(item?.confidence || item?.confidence_label).toUpperCase();

    return {
      label,
      class: confidenceClass(label),
      score: Number(item?.confidence_score || 0),
    };
  }

  const ai = Number(item?.ai_score || 0);
  const signal = Number(item?.signal_score || 0);
  const goal = Number(item?.goal_probability || 0);
  const over = Number(item?.over_probability || 0);
  const under = Number(item?.under_probability || 0);
  const market = String(item?.market || item?.side || "").toUpperCase();
  const marketProbability = market.includes("UNDER") ? under : over;

  let score = ai * 0.3 + signal * 0.3 + goal * 0.2 + marketProbability * 0.15;
  score = Math.max(0, Math.min(100, score));

  let label = "MUY BAJA";
  if (score >= 85) label = "MUY ALTA";
  else if (score >= 72) label = "ALTA";
  else if (score >= 58) label = "MEDIA";
  else if (score >= 42) label = "BAJA";

  return {
    label,
    class: confidenceClass(label),
    score,
  };
}

function getFinalRecommendation(item, confidence) {
  const minute = Number(item?.minute || 0);
  const score = String(item?.score || "0-0");
  const signal = Number(item?.signal_score || 0);
  const goal = Number(item?.goal_probability || 0);
  const risk = String(item?.risk_level || "").toUpperCase();

  const totalGoals = score
    .split("-")
    .map((x) => Number(x.trim() || 0))
    .reduce((a, b) => a + b, 0);

  if (risk.includes("ALTO")) {
    return {
      label: "NO ENTRAR",
      reason: "Riesgo alto detectado. El sistema recomienda no tomar esta señal.",
      class: "danger",
    };
  }

  if (minute >= 80 && totalGoals >= 3) {
    return {
      label: "RIESGO TARDE",
      reason: "Partido avanzado y marcador movido. La señal puede tener menos margen.",
      class: "warning",
    };
  }

  if (confidence.label.includes("MUY ALTA") && signal >= 80 && goal >= 90) {
    return {
      label: `${getTypeLabel(item)} - ENTRAR AHORA`,
      reason: "Lectura fuerte, alta probabilidad y buen consenso del sistema.",
      class: "good",
    };
  }

  if (confidence.label.includes("ALTA") && signal >= 70) {
    return {
      label: `${getTypeLabel(item)} - OPERABLE`,
      reason: "Señal aceptable. Revisar minuto, marcador y ritmo antes de entrar.",
      class: "ok",
    };
  }

  if (confidence.label.includes("MEDIA") || signal >= 58) {
    return {
      label: "ESPERAR / MONITOREAR",
      reason: "La señal existe, pero todavía no tiene fuerza suficiente.",
      class: "neutral",
    };
  }

  return {
    label: "NO ENTRAR TODAVÍA",
    reason: "Lectura débil o insuficiente para tomar acción.",
    class: "danger",
  };
}

function confidenceClass(label) {
  const value = String(label || "").toUpperCase();

  if (value.includes("MUY ALTA")) return "conf-high";
  if (value.includes("ALTA")) return "conf-good";
  if (value.includes("MEDIA")) return "conf-mid";
  if (value.includes("BAJA") && !value.includes("MUY")) return "conf-low";

  return "conf-bad";
}

function safeTypeClass(item) {
  const market = String(item?.market || item?.side || "").toUpperCase();
  const type = String(item?.type || "").toUpperCase();
  const over = Number(item?.over_probability || 0);

  if (market.includes("UNDER") || type.includes("UNDER") || over <= 40) {
    return "under";
  }

  if (
    market.includes("OVER") ||
    market.includes("MÁS") ||
    market.includes("MAS") ||
    type.includes("OVER") ||
    over >= 60
  ) {
    return "over";
  }

  return "observe";
}

function getTypeLabel(item) {
  const type = safeTypeClass(item);

  if (type === "under") return "DEBAJO";
  if (type === "over") return "ENCIMA";

  return "OBSERVAR";
}

function resultType(item) {
  const text = String(
    item?.resultado_final ||
      item?.status ||
      item?.resultado ||
      item?.result ||
      item?.final_status ||
      item?.history_status ||
      ""
  ).toUpperCase();

  if (
    text.includes("WIN") ||
    text.includes("ACIERTO") ||
    text.includes("ACERTADA") ||
    text.includes("GAN")
  ) {
    return "win";
  }

  if (
    text.includes("LOSS") ||
    text.includes("FALLO") ||
    text.includes("FALLIDA") ||
    text.includes("PERD")
  ) {
    return "loss";
  }

  if (text.includes("ACTIVE") || text.includes("ACTIVO")) {
    return "active";
  }

  return "pending";
}

function resultLabel(item) {
  const type = resultType(item);

  if (type === "win") return "ACERTADA";
  if (type === "loss") return "FALLIDA";
  if (type === "active") return "ACTIVA";

  return "PENDIENTE";
}

function resultProfit(item) {
  const type = resultType(item);

  if (item?.profit) return `${item.profit} unidades`;
  if (type === "win") return "+1.25 unidades";
  if (type === "loss") return "-1.00 unidades";
  if (type === "active") return "En curso";

  return "En espera";
}

function buildScore(item) {
  const direct = item?.score || item?.marcador || item?.marcador_entrada;
  if (direct && String(direct).includes("-")) return String(direct);

  const homeScore =
    item?.home_score ??
    item?.local_score ??
    item?.marcador_local ??
    item?.score_home ??
    item?.puntuacion_local ??
    0;

  const awayScore =
    item?.away_score ??
    item?.visitor_score ??
    item?.marcador_visitante ??
    item?.score_away ??
    item?.puntuacion_visitante ??
    0;

  return `${homeScore}-${awayScore}`;
}

function getStableMatchKey(item) {
  return String(
    item?.active_key ||
      item?.signal_key ||
      item?.signal_id ||
      item?.opportunity_id ||
      item?.match_id ||
      item?.id ||
      `${item?.match_name || ""}-${item?.market || item?.type || ""}`
  );
}

function buildKey(item, index) {
  return (
    item?.active_key ||
    item?.signal_key ||
    item?.match_id ||
    item?.id ||
    `${item?.match_name || ""}-${item?.market || item?.type || ""}-${index}`
  );
}

function formatNum(value) {
  return Number(value || 0).toFixed(1);
}

function safeText(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  return String(value);
}

function getInitials(name) {
  return String(name || "T")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();
}

function countryToEmoji(country) {
  const c = String(country || "").toLowerCase();

  if (c.includes("argentina")) return "🇦🇷";
  if (c.includes("chile")) return "🇨🇱";
  if (c.includes("colombia")) return "🇨🇴";
  if (c.includes("mexico") || c.includes("méxico")) return "🇲🇽";
  if (c.includes("brazil") || c.includes("brasil")) return "🇧🇷";
  if (c.includes("usa") || c.includes("united states")) return "🇺🇸";
  if (c.includes("spain") || c.includes("españa")) return "🇪🇸";
  if (c.includes("england") || c.includes("inglaterra")) return "🏴";
  if (c.includes("ecuador")) return "🇪🇨";
  if (c.includes("paraguay")) return "🇵🇾";
  if (c.includes("peru") || c.includes("perú")) return "🇵🇪";
  if (c.includes("uruguay")) return "🇺🇾";
  if (c.includes("bolivia")) return "🇧🇴";
  if (c.includes("venezuela")) return "🇻🇪";

  return "🏳️";
}
