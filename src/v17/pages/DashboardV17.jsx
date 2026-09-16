import React, { useMemo, useState } from "react";
import { Activity, BarChart3, ChevronRight, History, RefreshCw, ShieldCheck, Target } from "lucide-react";
import { useV17LiveData } from "../hooks/useV17LiveData";
import StatCardV17 from "../components/StatCardV17";
import SectionPanelV17 from "../components/SectionPanelV17";
import HistoryPanelV17 from "../components/HistoryPanelV17";
import MatchDetailModal from "../components/MatchDetailModal";
import "../styles/v17-dashboard.css";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function dynamicLabel(value) {
  const key = String(value || "").toUpperCase();
  return ({ OPENING: "Abriéndose", OPEN: "Abierto", BALANCED: "Equilibrado", CLOSING: "Cerrándose", CLOSED: "Cerrado" })[key] || "Leyendo";
}

function isStrong(item) {
  const value = String(item?.signal_strength || item?.elite_rank || item?.master_rank || "").toUpperCase();
  return value.includes("FUERTE") || value.includes("PREMIUM");
}

function resultIs(item, wanted) {
  const value = String(item?.result_status || item?.result_label || "").toUpperCase();
  if (wanted === "WON") return value.includes("WON") || value.includes("WIN") || value.includes("ACIERTO");
  if (wanted === "LOST") return value.includes("LOST") || value.includes("LOSS") || value.includes("FALLO");
  return value === wanted;
}

function LiveMatchStrip({ matches = [], onDetail }) {
  if (!matches.length) return <div className="v17-empty">No hay partidos live elegibles en este instante.</div>;

  return (
    <div className="v17-live-strip" aria-label="Partidos en vivo">
      {matches.map((match, index) => (
        <article className="v17-live-tile" key={match.match_id || match.fixture_id || index}>
          <div className="v17-live-tile-top">
            <span className="v17-live-dot">LIVE {safe(match.display_minute || match.api_minute, "")}'</span>
            <small>{safe(match.league)}</small>
          </div>
          <div className="v17-live-team"><span>{safe(match.home_team)}</span><b>{safe(match.home_score, 0)}</b></div>
          <div className="v17-live-team"><span>{safe(match.away_team)}</span><b>{safe(match.away_score, 0)}</b></div>
          <div className="v17-live-reading">
            <span>{safe(match.suggested_market, "OBSERVE")}</span>
            <strong>{Math.round(Number(match.official_confidence ?? match.candidate_score ?? 0))}%</strong>
          </div>
          <div className="v17-live-dynamics">
            <span>{dynamicLabel(match.dynamic_match_state)}</span>
            <strong>{match.dynamics_available ? `Amenaza ${Math.round(Number(match.recent_threat_score || 0))}%` : "Calibrando"}</strong>
          </div>
          {match.post_goal_reanalysis ? <div className="v17-live-recheck">Reanálisis post-gol</div> : null}
          <button type="button" className="v17-live-detail" onClick={() => onDetail?.(match)}>Ver detalle <ChevronRight size={14}/></button>
        </article>
      ))}
    </div>
  );
}

function FocusPanel({ focus, data, onDetail, onClose }) {
  if (!focus) return null;
  const closed = data.today_results || [];
  const config = {
    signals: { title: "Todas las señales activas", items: data.top_signals || [], type: "signals" },
    strong: { title: "Señales fuertes", items: (data.top_signals || []).filter(isStrong), type: "signals" },
    observe: { title: "Partidos en observación", items: data.observe || [], type: "signals" },
    pending: { title: "Señales pendientes", items: data.pending_signals || [], type: "history" },
    wins: { title: "Aciertos", items: closed.filter((x) => resultIs(x, "WON")), type: "history" },
    losses: { title: "Fallos", items: closed.filter((x) => resultIs(x, "LOST")), type: "history" },
  }[focus];
  if (!config) return null;

  return (
    <section className="v17-focus-wrap">
      <div className="v17-focus-head"><strong>{config.title}</strong><button type="button" onClick={onClose}>Cerrar</button></div>
      {config.type === "history" ? (
        <HistoryPanelV17 pending={focus === "pending" ? config.items : []} closed={focus === "pending" ? [] : config.items} onDetail={onDetail} title={config.title}/>
      ) : (
        <SectionPanelV17 title={config.title} subtitle="Toca Ver detalle para abrir toda la lectura del motor." items={config.items} compact onDetail={onDetail}/>
      )}
    </section>
  );
}

export default function DashboardV17() {
  const { data, stats, loading, error, lastFetchAt, reload } = useV17LiveData();
  const [tab, setTab] = useState("signals");
  const [focus, setFocus] = useState(null);
  const [selected, setSelected] = useState(null);

  const health = data.health || {};
  const statusOnline = !error && health.status !== "ERROR";
  const strongSignals = useMemo(() => (data.top_signals || []).filter(isStrong), [data.top_signals]);
  const quota = data.stats?.api_quota || {};
  const leagueFilter = data.stats?.league_filter || data.summary?.league_filter || {};

  const openFocus = (name) => {
    setTab("signals");
    setFocus((current) => current === name ? null : name);
  };

  return (
    <main className="v17-dashboard">
      <header className="v17-appbar">
        <div className="v17-brand">
          <div className="v17-brand-mark">JE</div>
          <div>
            <span className="v17-kicker">FOOTBALL INTELLIGENCE</span>
            <h1>JHONNY ELITE <em>20</em></h1>
          </div>
        </div>

        <div className="v17-app-actions">
          <div className={`v17-system-pill ${statusOnline ? "online" : "offline"}`}>
            <span /> {statusOnline ? "LIVE" : "OFFLINE"}
          </div>
          <button className="v17-icon-button" onClick={reload} title="Actualizar"><RefreshCw size={18} /></button>
        </div>
      </header>

      <section className="v17-hero-summary">
        <div>
          <span className="v17-hero-label">Master Protocol · Economy</span>
          <h2>{stats.liveMatches} partidos elegibles en vivo</h2>
          <p>Primera/segunda división y copas prioritarias. DataTruth, memoria 5/10/15, IA táctica, matemática y value alimentan una sola autoridad: MasterDecisionAI.</p>
        </div>
        <div className="v17-hero-score"><small>SEÑALES AHORA</small><strong>{stats.publishedSignals}</strong><span>{strongSignals.length} fuertes</span></div>
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
                <StatCardV17 label="Live" value={stats.liveMatches} onClick={() => { setTab("live"); setFocus(null); }} />
                <StatCardV17 label="Señales" value={stats.publishedSignals} good onClick={() => openFocus("signals")} active={focus === "signals"}/>
                <StatCardV17 label="Fuertes" value={strongSignals.length} good={strongSignals.length > 0} onClick={() => openFocus("strong")} active={focus === "strong"}/>
                <StatCardV17 label="Observación" value={stats.observe} onClick={() => openFocus("observe")} active={focus === "observe"}/>
                <StatCardV17 label="Pendientes" value={stats.pending} onClick={() => openFocus("pending")} active={focus === "pending"}/>
                <StatCardV17 label="Aciertos" value={stats.wins} good={stats.wins > 0} onClick={() => openFocus("wins")} active={focus === "wins"}/>
                <StatCardV17 label="Fallos" value={stats.losses} danger={stats.losses > 0} onClick={() => openFocus("losses")} active={focus === "losses"}/>
                <StatCardV17 label="Precisión" value={`${stats.precision}%`} good={stats.precision > 0} onClick={() => { setTab("history"); setFocus(null); }}/>
              </section>

              <FocusPanel focus={focus} data={data} onDetail={setSelected} onClose={() => setFocus(null)}/>

              <SectionPanelV17
                title="Mejores señales del momento"
                subtitle="Vista compacta: solo lo esencial. Abre el detalle para ver toda la evidencia."
                items={data.top_signals}
                dense
                limit={8}
                onDetail={setSelected}
                onViewAll={() => openFocus("signals")}
                emptyText="No existe una señal con ventaja suficiente ahora. El escaneo sigue activo."
              />

              <SectionPanelV17
                title="Observación prioritaria"
                subtitle="Candidatos que todavía no superan el umbral final."
                items={data.observe}
                dense
                limit={4}
                onDetail={setSelected}
                onViewAll={() => openFocus("observe")}
                emptyText="No hay candidatos parciales en este instante."
              />
            </>
          ) : null}

          {tab === "live" ? (
            <section className="v17-section-panel v17-live-section">
              <div className="v17-section-header">
                <div><h2>Partidos elegibles en vivo</h2><p>Solo alcance competitivo permitido; el detalle se abre sin gastar una llamada nueva al proveedor.</p></div>
                <span>{data.live_matches.length}</span>
              </div>
              <LiveMatchStrip matches={data.live_matches} onDetail={setSelected}/>
            </section>
          ) : null}

          {tab === "history" ? <HistoryPanelV17 pending={data.pending_signals} closed={data.closed_history} groups={data.history_groups} learning={data.performance_analysis} onDetail={setSelected}/> : null}

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
                  <small>Versión {safe(data.version, "JHONNY_ELITE_20.0")}</small>
                </div>
              </div>

              <section className="v17-economy-panel">
                <div className="v17-section-header"><div><h2>Economía de API</h2><p>Telemetría obtenida de las mismas respuestas; medir cuota no gasta llamadas extra.</p></div><span>{data.stats?.api_economy_mode === false ? "FULL" : "ECO"}</span></div>
                <div className="v17-detail-grid">
                  <div className="v17-detail-metric accent"><small>Créditos restantes</small><strong>{safe(quota.daily_remaining, "Sin cabecera")}</strong></div>
                  <div className="v17-detail-metric"><small>Límite diario</small><strong>{safe(quota.daily_limit, "—")}</strong></div>
                  <div className="v17-detail-metric"><small>Uso observado</small><strong>{safe(quota.daily_used_percent, "—")}{quota.daily_used_percent !== null && quota.daily_used_percent !== undefined ? "%" : ""}</strong></div>
                  <div className="v17-detail-metric"><small>Llamadas observadas</small><strong>{safe(quota.observed_requests, 0)}</strong></div>
                  <div className="v17-detail-metric"><small>Intervalo</small><strong>{safe(data.stats?.scan_interval_seconds, "—")} s</strong></div>
                  <div className="v17-detail-metric"><small>Último endpoint</small><strong>{safe(quota.last_endpoint, "—")}</strong></div>
                </div>
              </section>

              <section className="v17-economy-panel">
                <div className="v17-section-header"><div><h2>Rendimiento oficial</h2><p>Solo picks realmente publicados por MasterDecisionAI.</p></div><span>{safe(data.stats?.precision, 0)}%</span></div>
                <div className="v17-detail-grid">
                  <div className="v17-detail-metric accent"><small>ROI</small><strong>{safe(data.stats?.roi, 0)}%</strong></div>
                  <div className="v17-detail-metric"><small>Cuota media</small><strong>{safe(data.stats?.average_odds, 0)}</strong></div>
                  <div className="v17-detail-metric"><small>Edge medio</small><strong>{safe(data.stats?.average_edge, 0)} pp</strong></div>
                  <div className="v17-detail-metric"><small>Confianza media</small><strong>{safe(data.stats?.average_confidence, 0)}%</strong></div>
                  <div className="v17-detail-metric"><small>Brier</small><strong>{safe(data.stats?.calibration?.brier_score, 0)}</strong></div>
                  <div className="v17-detail-metric"><small>Log Loss</small><strong>{safe(data.stats?.calibration?.log_loss, 0)}</strong></div>
                </div>
              </section>

              <section className="v17-economy-panel">
                <div className="v17-section-header"><div><h2>Filtro de competiciones</h2><p>Primera/segunda división senior y copas internacionales/nacionales prioritarias.</p></div><span>{safe(leagueFilter.allowed, stats.liveMatches)}</span></div>
                <div className="v17-detail-grid">
                  <div className="v17-detail-metric"><small>Permitidos</small><strong>{safe(leagueFilter.allowed, stats.analyzedMatches)}</strong></div>
                  <div className="v17-detail-metric"><small>Ignorados</small><strong>{safe(leagueFilter.blocked, data.stats?.blocked_by_league ?? 0)}</strong></div>
                  <div className="v17-detail-metric"><small>Modo</small><strong>STRICT TOP-2</strong></div>
                </div>
              </section>

              <SectionPanelV17 title="No Bet" subtitle="Sin ventaja suficiente para entrar." items={data.no_bet} compact limit={8} onDetail={setSelected} emptyText="Sin NO_BET visibles." />
              <SectionPanelV17 title="Bloqueados" subtitle="Bloqueos críticos de datos, reloj o competición." items={data.blocked} compact limit={8} onDetail={setSelected} emptyText="No hay bloqueos críticos." />
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

      <MatchDetailModal selection={selected} onClose={() => setSelected(null)}/>
    </main>
  );
}
