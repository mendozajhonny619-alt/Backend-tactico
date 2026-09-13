import React, { useMemo, useState } from "react";
import { Activity, BarChart3, History, RefreshCw, ShieldCheck, Target } from "lucide-react";
import { useV17LiveData } from "../hooks/useV17LiveData";
import StatCardV17 from "../components/StatCardV17";
import SectionPanelV17 from "../components/SectionPanelV17";
import HistoryPanelV17 from "../components/HistoryPanelV17";
import "../styles/v17-dashboard.css";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function dynamicLabel(value) {
  const key = String(value || "").toUpperCase();
  return ({ OPENING: "Abriéndose", OPEN: "Abierto", BALANCED: "Equilibrado", CLOSING: "Cerrándose", CLOSED: "Cerrado" })[key] || "Leyendo";
}

function LiveMatchStrip({ matches = [] }) {
  if (!matches.length) return <div className="v17-empty">No hay partidos live elegibles en este instante.</div>;

  return (
    <div className="v17-live-strip" aria-label="Partidos en vivo">
      {matches.slice(0, 30).map((match, index) => (
        <article className="v17-live-tile" key={match.match_id || match.fixture_id || index}>
          <div className="v17-live-tile-top">
            <span className="v17-live-dot">LIVE {safe(match.display_minute || match.api_minute, "")}'</span>
            <small>{safe(match.league)}</small>
          </div>
          <div className="v17-live-team"><span>{safe(match.home_team)}</span><b>{safe(match.home_score, 0)}</b></div>
          <div className="v17-live-team"><span>{safe(match.away_team)}</span><b>{safe(match.away_score, 0)}</b></div>
          <div className="v17-live-reading">
            <span>{safe(match.suggested_market, "OBSERVE")}</span>
            <strong>{Math.round(Number(match.candidate_score || match.official_confidence || 0))}%</strong>
          </div>
          <div className="v17-live-dynamics">
            <span>{dynamicLabel(match.dynamic_match_state)}</span>
            <strong>{match.dynamics_available ? `Amenaza ${Math.round(Number(match.recent_threat_score || 0))}%` : "Calibrando"}</strong>
          </div>
          {match.post_goal_reanalysis ? <div className="v17-live-recheck">Reanálisis post-gol</div> : null}
        </article>
      ))}
    </div>
  );
}

export default function DashboardV17() {
  const { data, stats, loading, error, lastFetchAt, reload } = useV17LiveData();
  const [tab, setTab] = useState("signals");

  const health = data.health || {};
  const statusOnline = !error && health.status !== "ERROR";
  const strongCount = useMemo(
    () => (data.top_signals || []).filter((x) => String(x.signal_strength || x.elite_rank || "").toUpperCase().includes("FUERTE")).length,
    [data.top_signals]
  );

  return (
    <main className="v17-dashboard">
      <header className="v17-appbar">
        <div className="v17-brand">
          <div className="v17-brand-mark">JE</div>
          <div>
            <span className="v17-kicker">FOOTBALL INTELLIGENCE</span>
            <h1>JHONNY ELITE <em>19</em></h1>
          </div>
        </div>

        <div className="v17-app-actions">
          <div className={`v17-system-pill ${statusOnline ? "online" : "offline"}`}>
            <span /> {statusOnline ? "LIVE" : "OFFLINE"}
          </div>
          <button className="v17-icon-button" onClick={reload} title="Actualizar">
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      <section className="v17-hero-summary">
        <div>
          <span className="v17-hero-label">Escaneo global</span>
          <h2>{stats.liveMatches} partidos en vivo</h2>
          <p>
            Live primero. Prepartido y cuota solo después de detectar un candidato real.
            OVER puede aparecer en cualquier minuto; UNDER se valida desde la ventana tardía.
          </p>
        </div>
        <div className="v17-hero-score">
          <small>SEÑALES AHORA</small>
          <strong>{stats.publishedSignals}</strong>
          <span>{strongCount} fuertes</span>
        </div>
      </section>

      {error ? <div className="v17-alert error">{error}</div> : null}
      {loading ? <div className="v17-loading">Sincronizando JHONNY ELITE...</div> : null}

      {!loading ? (
        <>
          <nav className="v17-desktop-nav" aria-label="Navegación del panel">
            <button className={tab === "signals" ? "active" : ""} onClick={() => setTab("signals")}><Target size={17}/>Señales</button>
            <button className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}><Activity size={17}/>En vivo</button>
            <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}><History size={17}/>Historial</button>
            <button className={tab === "system" ? "active" : ""} onClick={() => setTab("system")}><BarChart3 size={17}/>Sistema</button>
          </nav>

          {tab === "signals" ? (
            <>
              <section className="v17-stats-grid">
                <StatCardV17 label="Live" value={stats.liveMatches} />
                <StatCardV17 label="Señales" value={stats.publishedSignals} good />
                <StatCardV17 label="Fuertes" value={strongCount} good={strongCount > 0} />
                <StatCardV17 label="Observación" value={stats.observe} />
                <StatCardV17 label="Pendientes" value={stats.pending} />
                <StatCardV17 label="Aciertos" value={stats.wins} good={stats.wins > 0} />
                <StatCardV17 label="Fallos" value={stats.losses} danger={stats.losses > 0} />
                <StatCardV17 label="Precisión" value={`${stats.precision}%`} good={stats.precision > 0} />
              </section>

              <SectionPanelV17
                title="Mejores señales del momento"
                subtitle="Publicadas solo después de validar lectura live, riesgo, prepartido y cálculo matemático."
                items={data.top_signals}
                emptyText="No existe una señal con ventaja suficiente ahora. El escaneo sigue activo."
              />

              <SectionPanelV17
                title="Candidatos en observación"
                subtitle="Oportunidades reales que todavía no superan el umbral final."
                items={data.observe}
                compact
                emptyText="No hay candidatos parciales en este instante."
              />
            </>
          ) : null}

          {tab === "live" ? (
            <section className="v17-section-panel v17-live-section">
              <div className="v17-section-header">
                <div><h2>Todos los partidos live</h2><p>Lectura continua de ritmo, presión, amenaza, contexto y marcador.</p></div>
                <span>{data.live_matches.length}</span>
              </div>
              <LiveMatchStrip matches={data.live_matches} />
            </section>
          ) : null}

          {tab === "history" ? (
            <HistoryPanelV17
              pending={data.pending_signals}
              closed={data.closed_history}
              learning={data.performance_analysis}
            />
          ) : null}

          {tab === "system" ? (
            <>
              <div className="v17-system-grid">
                <div className="v17-message">
                  <strong><ShieldCheck size={16}/> Protocolo activo</strong>
                  <p>{data.message || "JHONNY ELITE activo."}</p>
                  <small>{lastFetchAt ? `Actualizado ${lastFetchAt.toLocaleTimeString()}` : "Sin sincronización"}</small>
                </div>
                <div className="v17-message">
                  <strong>Estado del motor</strong>
                  <p>{safe(health.protocol, "LIVE → CANDIDATE → PREMATCH → MATH → MASTER")}</p>
                  <small>Versión {safe(data.version, "JHONNY_ELITE_19.0")}</small>
                </div>
              </div>
              <SectionPanelV17 title="No Bet" subtitle="Sin ventaja suficiente para entrar." items={data.no_bet} compact emptyText="Sin NO_BET visibles." />
              <SectionPanelV17 title="Bloqueados" subtitle="Bloqueos críticos de datos, reloj o competición." items={data.blocked} compact emptyText="No hay bloqueos críticos." />
            </>
          ) : null}

          <nav className="v17-tabs-nav" aria-label="Navegación móvil">
            <button className={tab === "signals" ? "active" : ""} onClick={() => setTab("signals")}><Target size={20}/><strong>Señales</strong></button>
            <button className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}><Activity size={20}/><strong>En vivo</strong></button>
            <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}><History size={20}/><strong>Historial</strong></button>
            <button className={tab === "system" ? "active" : ""} onClick={() => setTab("system")}><BarChart3 size={20}/><strong>Sistema</strong></button>
          </nav>
        </>
      ) : null}
    </main>
  );
}
