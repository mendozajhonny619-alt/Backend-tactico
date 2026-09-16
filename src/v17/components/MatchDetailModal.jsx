import React, { useEffect, useMemo, useState } from "react";
import { BrainCircuit, Calculator, Gauge, ShieldCheck, X } from "lucide-react";
import { fetchV17MatchDetail } from "../services/apiV17";

const safe = (value, fallback = "—") => value === null || value === undefined || value === "" ? fallback : value;
const num = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const pct = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(0)}%` : "—";

function scoreOf(item) {
  return item.current_score || item.scoreline || item.score || item.marcador || `${safe(item.home_score, 0)}-${safe(item.away_score, 0)}`;
}

function DetailMetric({ label, value, accent = false }) {
  return <div className={`v17-detail-metric ${accent ? "accent" : ""}`}><small>{label}</small><strong>{safe(value)}</strong></div>;
}

function TeamStat({ label, home, away }) {
  return (
    <div className="v17-team-stat">
      <strong>{safe(home, 0)}</strong><span>{label}</span><strong>{safe(away, 0)}</strong>
    </div>
  );
}

function Tags({ title, items, kind = "support" }) {
  if (!Array.isArray(items) || !items.length) return null;
  return (
    <div className="v17-detail-tags-block">
      <h4>{title}</h4>
      <div className={`v17-tags ${kind}`}>{items.slice(0, 10).map((x, i) => <span key={`${x}-${i}`}>{String(x)}</span>)}</div>
    </div>
  );
}

function MatchList({ title, items }) {
  if (!Array.isArray(items) || !items.length) return null;
  return (
    <div className="v17-prematch-list">
      <h4>{title}</h4>
      {items.slice(0, 5).map((m, index) => {
        const teams = m?.teams || {};
        const goals = m?.goals || {};
        const home = m.home_team || teams?.home?.name || m.home || "Local";
        const away = m.away_team || teams?.away?.name || m.away || "Visitante";
        const homeGoals = m.home_score ?? goals.home ?? m.goals_home;
        const awayGoals = m.away_score ?? goals.away ?? m.goals_away;
        return <div className="v17-prematch-row" key={m.fixture_id || m.id || index}><span>{home} vs {away}</span><strong>{safe(homeGoals, "?")}-{safe(awayGoals, "?")}</strong></div>;
      })}
    </div>
  );
}

function JsonFallback({ value }) {
  if (!value || typeof value !== "object" || !Object.keys(value).length) return null;
  return <pre className="v17-detail-json">{JSON.stringify(value, null, 2)}</pre>;
}

export default function MatchDetailModal({ selection, onClose }) {
  const [detail, setDetail] = useState(selection || {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("summary");

  const fixtureId = selection?.fixture_id || selection?.match_id;
  const signalKey = selection?.signal_key || "";

  useEffect(() => {
    if (!selection) return undefined;
    setDetail(selection);
    setTab("summary");
    setError("");
    if (!fixtureId) return undefined;
    let active = true;
    setLoading(true);
    fetchV17MatchDetail(fixtureId, signalKey)
      .then((payload) => {
        if (!active) return;
        if (payload?.item && Object.keys(payload.item).length) setDetail({ ...selection, ...payload.item });
        else setError("El detalle completo todavía no está en memoria; se muestra el resumen disponible.");
      })
      .catch(() => active && setError("No se pudo ampliar el detalle; se muestra la información ya cargada."))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [selection, fixtureId, signalKey]);

  useEffect(() => {
    if (!selection) return undefined;
    const close = (event) => event.key === "Escape" && onClose?.();
    window.addEventListener("keydown", close);
    document.body.classList.add("v17-modal-open");
    return () => {
      window.removeEventListener("keydown", close);
      document.body.classList.remove("v17-modal-open");
    };
  }, [selection, onClose]);

  const homeStats = detail.home_stats || {};
  const awayStats = detail.away_stats || {};
  const market = String(detail.official_market || detail.market || detail.suggested_market || "OBSERVE").toUpperCase();
  const confidence = detail.official_confidence ?? detail.master_confidence ?? detail.elite_score ?? detail.candidate_score;
  const alternatives = useMemo(() => detail.alternative_scores || detail.prediction_score_scenarios || [], [detail]);

  if (!selection) return null;

  return (
    <div className="v17-modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <section className="v17-detail-modal" role="dialog" aria-modal="true" aria-label="Detalle del partido">
        <header className="v17-detail-header">
          <div>
            <small>{safe(detail.country)} · {safe(detail.league)}</small>
            <h2>{safe(detail.home_team)} <span>{scoreOf(detail)}</span> {safe(detail.away_team)}</h2>
            <p>Min {safe(detail.display_minute || detail.current_minute || detail.api_minute)} · {safe(detail.status_long || detail.clock_status, "EN VIVO")}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar"><X size={22}/></button>
        </header>

        <div className="v17-detail-hero">
          <DetailMetric label="Lectura" value={market} accent />
          <DetailMetric label="Confianza" value={pct(confidence)} accent />
          <DetailMetric label="Fuerza" value={detail.signal_strength || detail.elite_rank || detail.master_rank || "OBSERVE"} />
          <DetailMetric label="Riesgo" value={detail.risk_status || detail.risk_level || "—"} />
          <DetailMetric label="Línea oficial" value={detail.official_line ? num(detail.official_line).toFixed(1) : detail.line ? num(detail.line).toFixed(1) : "N/D"} />
          <DetailMetric label="Cuota oficial" value={detail.official_odds ? num(detail.official_odds).toFixed(2) : detail.odds_available ? num(detail.odds).toFixed(2) : "N/D"} />
          <DetailMetric label="Fuente cuota" value={detail.odds_source || detail.odds_provider || detail.bookmaker || "N/D"} />
        </div>

        {loading ? <div className="v17-detail-notice">Cargando ficha completa desde la memoria del motor…</div> : null}
        {error ? <div className="v17-detail-notice warning">{error}</div> : null}

        <nav className="v17-detail-tabs">
          <button className={tab === "summary" ? "active" : ""} onClick={() => setTab("summary")}>Resumen</button>
          <button className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}>Live</button>
          <button className={tab === "ai" ? "active" : ""} onClick={() => setTab("ai")}>IA + Matemática</button>
          <button className={tab === "prematch" ? "active" : ""} onClick={() => setTab("prematch")}>Prepartido</button>
          <button className={tab === "evidence" ? "active" : ""} onClick={() => setTab("evidence")}>Evidencia</button>
        </nav>

        <div className="v17-detail-body">
          {tab === "summary" ? (
            <>
              <div className="v17-detail-section-title"><BrainCircuit size={17}/><h3>Lectura de JHONNY ELITE</h3></div>
              <div className="v17-detail-reading">
                <p>{safe(detail.main_reading || detail.official_main_scenario || detail.prediction_panel_message, "El motor continúa leyendo el encuentro.")}</p>
              </div>
              <div className="v17-detail-grid">
                <DetailMetric label="Resultado principal" value={detail.primary_final_score || detail.official_probable_score || detail.prediction_final_score || detail.prediction_main_score} accent />
                <DetailMetric label="Próximo gol" value={detail.official_next_goal_team || detail.prediction_attacking_team || "Sin ventaja clara"} />
                <DetailMetric label="Partido" value={detail.dynamic_match_state || detail.tactical_status || "Leyendo"} />
                <DetailMetric label="Amenaza reciente" value={pct(detail.recent_threat_score)} />
                <DetailMetric label="Equipo que empuja" value={detail.recent_dominant_team || detail.prediction_attacking_side || "Equilibrado"} />
                <DetailMetric label="DataTruth" value={`${safe(detail.data_truth_status, detail.data_quality)} · ${pct(detail.data_truth_score)}`} />
              </div>
              {alternatives.length ? <div className="v17-alt-box"><h4>Resultados alternativos</h4><div>{alternatives.slice(0, 4).map((x, i) => <span key={i}>{typeof x === "object" ? `${safe(x.score)} · ${pct(x.probability)}` : String(x)}</span>)}</div></div> : null}
              {(detail.entry_score || detail.current_score) ? (
                <div className="v17-detail-grid v17-tracking-grid">
                  <DetailMetric label="Entrada" value={`Min ${safe(detail.entry_minute)} · ${safe(detail.entry_score)}`} />
                  <DetailMetric label="Final / actual" value={safe(detail.current_score || scoreOf(detail))} accent />
                  <DetailMetric label="Resultado" value={detail.result_label || detail.result_status || "PENDIENTE"} />
                  <DetailMetric label="Resolución" value={detail.result_reason || "En seguimiento"} />
                </div>
              ) : null}
            </>
          ) : null}

          {tab === "live" ? (
            <>
              <div className="v17-detail-section-title"><Gauge size={17}/><h3>Estadísticas en vivo</h3></div>
              <div className="v17-team-stat-head"><strong>{safe(detail.home_team)}</strong><span>LIVE</span><strong>{safe(detail.away_team)}</strong></div>
              <div className="v17-team-stats">
                <TeamStat label="Tiros" home={homeStats.shots ?? homeStats.total_shots} away={awayStats.shots ?? awayStats.total_shots}/>
                <TeamStat label="Al arco" home={homeStats.shots_on_target} away={awayStats.shots_on_target}/>
                <TeamStat label="xG" home={homeStats.xg ?? homeStats.xG} away={awayStats.xg ?? awayStats.xG}/>
                <TeamStat label="Córners" home={homeStats.corners} away={awayStats.corners}/>
                <TeamStat label="Posesión" home={homeStats.possession ?? detail.possession_home} away={awayStats.possession ?? detail.possession_away}/>
                <TeamStat label="Ataques peligrosos" home={homeStats.dangerous_attacks} away={awayStats.dangerous_attacks}/>
                <TeamStat label="Tiros bloqueados" home={homeStats.blocked_shots} away={awayStats.blocked_shots}/>
                <TeamStat label="Dentro del área" home={homeStats.shots_inside_box} away={awayStats.shots_inside_box}/>
                <TeamStat label="Faltas" home={homeStats.fouls} away={awayStats.fouls}/>
                <TeamStat label="Tarjetas amarillas" home={homeStats.yellow_cards} away={awayStats.yellow_cards}/>
                <TeamStat label="Tarjetas rojas" home={homeStats.red_cards} away={awayStats.red_cards}/>
                <TeamStat label="Atajadas" home={homeStats.goalkeeper_saves} away={awayStats.goalkeeper_saves}/>
              </div>
              <div className="v17-detail-grid">
                <DetailMetric label="Ritmo" value={pct(detail.rhythm_score)} />
                <DetailMetric label="Presión" value={pct(detail.pressure_score)} />
                <DetailMetric label="Profundidad ofensiva" value={pct(detail.offensive_depth_score)} />
                <DetailMetric label="Proxy ataque reciente" value={pct(detail.recent_attack_proxy)} />
                <DetailMetric label="Inestabilidad" value={pct(detail.dynamic_instability_score)} />
                <DetailMetric label="Falsa presión" value={pct(detail.false_pressure_risk)} />
              </div>
              <div className="v17-detail-grid">
                <DetailMetric label="Amenaza últimos 5'" value={pct(detail.window_5?.threat_score)} />
                <DetailMetric label="Amenaza últimos 10'" value={pct(detail.window_10?.threat_score)} />
                <DetailMetric label="Amenaza últimos 15'" value={pct(detail.window_15?.threat_score)} />
                <DetailMetric label="Memoria temporal" value={detail.temporal_memory_ready ? `${safe(detail.temporal_memory_points, 0)} snapshots` : "Calentando"} />
              </div>
              {Array.isArray(detail.events) && detail.events.length ? <JsonFallback value={{ eventos: detail.events.slice(-12) }}/>: null}
            </>
          ) : null}

          {tab === "ai" ? (
            <>
              <div className="v17-detail-section-title"><Calculator size={17}/><h3>Cálculo matemático y predicción</h3></div>
              <div className="v17-detail-grid">
                <DetailMetric label="xG restante" value={num(detail.expected_goals_remaining).toFixed(2)} accent />
                <DetailMetric label="Prob. próximo gol" value={pct(detail.probability_next_goal)} />
                <DetailMetric label="Prob. sin más goles" value={pct(detail.probability_no_more_goals)} />
                <DetailMetric label="Prob. 2+ goles" value={pct(detail.probability_two_plus_goals)} />
                <DetailMetric label="OVER live" value={pct(detail.prediction_live_over_probability ?? detail.visual_over_probability ?? detail.over_score)} />
                <DetailMetric label="UNDER live" value={pct(detail.prediction_live_under_probability ?? detail.visual_under_probability ?? detail.under_score)} />
                <DetailMetric label="Sostener marcador" value={pct(detail.score_hold_probability)} />
                <DetailMetric label="Transición UNDER" value={pct(detail.under_transition_score)} />
                <DetailMetric label="Score live" value={pct(detail.candidate_score)} />
                <DetailMetric label="Score IA" value={pct(detail.prediction_confidence)} />
                <DetailMetric label="Valor cuota" value={detail.official_value_edge !== undefined ? `${num(detail.official_value_edge).toFixed(1)} pp` : detail.odds_available ? `${num(detail.value_edge).toFixed(1)} pp` : "N/D"} />
                <DetailMetric label="EV" value={detail.official_expected_value !== undefined ? num(detail.official_expected_value).toFixed(3) : "N/D"} />
                <DetailMetric label="Consenso" value={detail.official_consensus !== undefined ? `${detail.official_consensus}/5` : "—"} />
                <DetailMetric label="Próx. gol 5'" value={pct(detail.goal_next_5_probability)} />
                <DetailMetric label="Próx. gol 10'" value={pct(detail.goal_next_10_probability)} />
                <DetailMetric label="Próx. gol 15'" value={pct(detail.goal_next_15_probability)} />
                <DetailMetric label="Estabilidad marcador" value={pct(detail.score_stability_probability)} />
                <DetailMetric label="Estado Master" value={detail.official_status || "OBSERVATION"} />
              </div>
              <div className="v17-detail-reading"><h4>Interpretación</h4><p>{safe(detail.prediction_reason || detail.result_probability_reading || detail.main_reading)}</p></div>
            </>
          ) : null}

          {tab === "prematch" ? (
            <>
              <div className="v17-detail-section-title"><ShieldCheck size={17}/><h3>Memoria prepartido</h3></div>
              <div className="v17-detail-grid">
                <DetailMetric label="Estado" value={detail.pre_match_available ? "DISPONIBLE" : detail.pre_match_queued ? "EN COLA ECONOMÍA" : "NO REQUERIDO"} accent={detail.pre_match_available}/>
                <DetailMetric label="Fuente" value={detail.pre_match_source} />
                <DetailMetric label="Refuerzo OVER" value={pct(detail.over_pre_match_score)} />
                <DetailMetric label="Refuerzo UNDER" value={pct(detail.under_pre_match_score)} />
                <DetailMetric label="Promedio goles" value={detail.pre_match_avg_total_goals} />
                <DetailMetric label="Goles esperados temporada" value={detail.season_expected_total_goals} />
              </div>
              <MatchList title={`Últimos 5 · ${safe(detail.home_team)}`} items={detail.home_last_5}/>
              <MatchList title={`Últimos 5 · ${safe(detail.away_team)}`} items={detail.away_last_5}/>
              <MatchList title="Enfrentamientos directos" items={detail.head_to_head_last_5}/>
              <div className="v17-prematch-json-grid">
                {detail.standings_context && Object.keys(detail.standings_context).length ? <div><h4>Clasificación</h4><JsonFallback value={detail.standings_context}/></div> : null}
                {detail.home_team_statistics && Object.keys(detail.home_team_statistics).length ? <div><h4>Temporada local</h4><JsonFallback value={detail.home_team_statistics}/></div> : null}
                {detail.away_team_statistics && Object.keys(detail.away_team_statistics).length ? <div><h4>Temporada visitante</h4><JsonFallback value={detail.away_team_statistics}/></div> : null}
              </div>
              {!detail.pre_match_available ? <div className="v17-detail-notice">El prepartido solo se consulta cuando el live supera el filtro de candidato; así se ahorran créditos.</div> : null}
            </>
          ) : null}

          {tab === "evidence" ? (
            <>
              <div className="v17-detail-section-title"><ShieldCheck size={17}/><h3>Evidencia y filtros</h3></div>
              <Tags title="Evidencia a favor" items={detail.support_points || detail.pre_match_support_points} kind="support"/>
              <Tags title="Advertencias" items={detail.caution_points || detail.soft_warnings || detail.pre_match_caution_points} kind="warning"/>
              <Tags title="Filtros superados" items={detail.passed_filters} kind="support"/>
              <Tags title="Filtros secundarios pendientes" items={detail.failed_secondary_filters} kind="warning"/>
              <Tags title="Bloqueos críticos" items={detail.official_blockers || detail.hard_blockers || detail.over_blockers} kind="blocked"/>
              <Tags title="Advertencias Master" items={detail.official_warnings} kind="warning"/>
              <div className="v17-detail-grid">
                <DetailMetric label="Fase de escaneo" value={detail.scan_phase} />
                <DetailMetric label="Motivo" value={detail.scan_reason} />
                <DetailMetric label="Fuente stats" value={detail.stats_source} />
                <DetailMetric label="Competición" value={detail.competition_tier} />
                <DetailMetric label="Peso liga" value={detail.competition_weight} />
                <DetailMetric label="Estado liga" value={detail.league_filter_status} />
              </div>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
