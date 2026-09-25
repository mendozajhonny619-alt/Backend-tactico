import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function JhonnyEliteLiveDashboard() {
  const [statsData, setStatsData] = useState(null);
  const [signalsData, setSignalsData] = useState(null);
  const [opportunitiesData, setOpportunitiesData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [leagueFilter, setLeagueFilter] = useState("Todas las ligas");
  const [signalFilter, setSignalFilter] = useState("Todas las señales");
  const [sortBy, setSortBy] = useState("score");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const [statsRes, signalsRes, opportunitiesRes] = await Promise.all([
          fetch(`${API_BASE}/stats`),
          fetch(`${API_BASE}/signals`),
          fetch(`${API_BASE}/opportunities`),
        ]);

        const statsJson = await statsRes.json();
        const signalsJson = await signalsRes.json();
        const opportunitiesJson = await opportunitiesRes.json();

        if (!active) return;

        setStatsData(statsJson);
        setSignalsData(signalsJson);
        setOpportunitiesData(opportunitiesJson);
      } catch (err) {
        if (!active) return;
        setError("No se pudo conectar con la API del panel.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadDashboard();
    const interval = setInterval(loadDashboard, 30000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const rawSignals = useMemo(() => {
    if (Array.isArray(signalsData)) return signalsData;
    if (Array.isArray(signalsData?.items)) return signalsData.items;
    if (Array.isArray(signalsData?.signals)) return signalsData.signals;
    if (Array.isArray(signalsData?.published_signals)) return signalsData.published_signals;
    return [];
  }, [signalsData]);

  const rawOpportunities = useMemo(() => {
    if (Array.isArray(opportunitiesData)) return opportunitiesData;
    if (Array.isArray(opportunitiesData?.items)) return opportunitiesData.items;
    if (Array.isArray(opportunitiesData?.observe)) return opportunitiesData.observe;
    if (Array.isArray(opportunitiesData?.opportunities)) return opportunitiesData.opportunities;
    return [];
  }, [opportunitiesData]);

  const allCards = useMemo(() => {
    const mappedSignals = rawSignals.map((item, index) => mapSignalItem(item, index));
    const mappedOpportunities = rawOpportunities.map((item, index) =>
      mapOpportunityItem(item, index, mappedSignals.length)
    );

    return [...mappedSignals, ...mappedOpportunities];
  }, [rawSignals, rawOpportunities]);

  const leagueOptions = useMemo(() => {
    const unique = [...new Set(allCards.map((m) => m.country).filter(Boolean))];
    return ["Todas las ligas", ...unique];
  }, [allCards]);

  const filteredMatches = useMemo(() => {
    let data = [...allCards];

    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter((m) =>
        [m.home, m.away, m.league, m.country, m.market, m.signal, m.reason]
          .join(" ")
          .toLowerCase()
          .includes(q)
      );
    }

    if (leagueFilter !== "Todas las ligas") {
      data = data.filter((m) => m.country === leagueFilter);
    }

    if (signalFilter !== "Todas las señales") {
      data = data.filter((m) => m.signal === signalFilter);
    }

    data.sort((a, b) => {
      if (sortBy === "minute") return b.minute - a.minute;
      if (sortBy === "odd") return Number(b.odd || 0) - Number(a.odd || 0);
      return Number(b.signalScore || 0) - Number(a.signalScore || 0);
    });

    return data;
  }, [allCards, search, leagueFilter, signalFilter, sortBy]);

  const signalBadge = {
    PREMIUM: "bg-emerald-500/15 text-emerald-400 border-emerald-400/30",
    FUERTE: "bg-sky-500/15 text-sky-400 border-sky-400/30",
    BUENA: "bg-violet-500/15 text-violet-400 border-violet-400/30",
    OBSERVACION: "bg-amber-500/15 text-amber-400 border-amber-400/30",
    ACEPTABLE: "bg-amber-500/15 text-amber-400 border-amber-400/30",
  };

  const momentumColor = {
    Explosivo: "text-rose-400",
    Caliente: "text-orange-400",
    Tibio: "text-yellow-300",
    Controlado: "text-slate-300",
    Muerto: "text-slate-500",
  };

  const totalMatches =
    statsData?.stats?.scanned_matches ??
    statsData?.stats?.live_matches_count ??
    statsData?.scanned_matches ??
    allCards.length;

  const totalSignals =
    statsData?.stats?.published_signals_total ??
    statsData?.stats?.published_count ??
    rawSignals.length;

  const totalOpportunities =
    statsData?.stats?.opportunities_count ??
    rawOpportunities.length;

  const totalBlocked =
    statsData?.stats?.blocked_matches ??
    0;

  const systemStatus =
    error ? "ERROR" : "OPERATIVO";

  return (
    <div className="min-h-screen bg-[#0b1220] text-white">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <header className="sticky top-0 z-20 mb-4 rounded-3xl border border-white/10 bg-[#111827]/90 p-4 shadow-2xl backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-2xl bg-emerald-500/20 p-2 text-emerald-400">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="h-full w-full"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  >
                    <path d="M4 14l4-4 3 3 7-7" />
                    <path d="M20 10v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
                    JHONNY ELITE V16
                  </h1>
                  <p className="text-sm text-slate-400">
                    Panel visual conectado a señales, oportunidades y estadísticas reales
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-[700px]">
              {[
                ["Sistema", systemStatus],
                ["Partidos", String(totalMatches)],
                ["Señales", String(totalSignals)],
                ["Oportunidades", String(totalOpportunities)],
                ["Bloqueados", String(totalBlocked)],
                ["Visibles", String(filteredMatches.length)],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-2xl border border-white/10 bg-white/5 p-3"
                >
                  <div className="text-xs uppercase tracking-wide text-slate-400">
                    {label}
                  </div>
                  <div className="mt-1 text-sm font-semibold sm:text-base">
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-[290px_minmax(0,1fr)]">
          <aside className="rounded-3xl border border-white/10 bg-[#111827] p-4 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold">Filtros</h2>
              <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-400">
                En vivo
              </span>
            </div>

            <div className="space-y-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none placeholder:text-slate-500"
                placeholder="Buscar partido o liga"
              />

              <select
                value={leagueFilter}
                onChange={(e) => setLeagueFilter(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none"
              >
                {leagueOptions.map((option) => (
                  <option key={option}>{option}</option>
                ))}
              </select>

              <select
                value={signalFilter}
                onChange={(e) => setSignalFilter(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none"
              >
                <option>Todas las señales</option>
                <option>PREMIUM</option>
                <option>FUERTE</option>
                <option>BUENA</option>
                <option>OBSERVACION</option>
                <option>ACEPTABLE</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none"
              >
                <option value="score">Ordenar por score</option>
                <option value="minute">Ordenar por minuto</option>
                <option value="odd">Ordenar por cuota</option>
              </select>
            </div>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-sm font-medium">Resumen operativo</div>
              <div className="mt-3 space-y-2 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>API</span>
                  <span className="truncate pl-3 text-right">{API_BASE}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Señales cargadas</span>
                  <span>{rawSignals.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Oportunidades cargadas</span>
                  <span>{rawOpportunities.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Visibles</span>
                  <span>{filteredMatches.length}</span>
                </div>
              </div>
            </div>
          </aside>

          <main className="space-y-4">
            {loading && (
              <StateBox
                title="Cargando panel"
                text="Conectando con la API y trayendo estadísticas, señales y oportunidades..."
              />
            )}

            {!loading && error && (
              <StateBox title="Error de conexión" text={error} />
            )}

            {!loading && !error && filteredMatches.length === 0 && (
              <StateBox
                title="Sin datos disponibles"
                text="La API respondió, pero en este momento no hay señales ni oportunidades visibles."
              />
            )}

            {!loading &&
              !error &&
              filteredMatches.map((match, index) => (
                <section
                  key={match.id}
                  className="overflow-hidden rounded-3xl border border-white/10 bg-[#111827] shadow-xl"
                >
                  <div className="border-b border-white/5 px-4 py-3 sm:px-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="text-xs uppercase tracking-wide text-slate-400">
                          {match.country}
                        </div>
                        <div className="text-sm font-semibold text-slate-200 sm:text-base">
                          {match.league}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full border px-3 py-1 text-xs font-medium ${
                            signalBadge[match.signal] || signalBadge.ACEPTABLE
                          }`}
                        >
                          {match.signal}
                        </span>

                        <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">
                          Score {match.signalScore}
                        </span>

                        <span className="rounded-full bg-rose-500/10 px-3 py-1 text-xs text-rose-300">
                          {match.status} {match.minute}'
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="px-4 py-4 sm:px-5">
                    <div className="grid gap-4 lg:grid-cols-[1.3fr_.9fr]">
                      <div>
                        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-3xl bg-[#0b1220] p-4">
                          <div>
                            <div className="text-sm text-slate-400">Local</div>
                            <div className="mt-1 text-base font-semibold sm:text-lg">
                              {match.home}
                            </div>
                          </div>

                          <div className="text-center">
                            <div className="text-2xl font-bold tracking-tight sm:text-3xl">
                              {match.score}
                            </div>
                            <div className="mt-1 text-xs text-slate-400">
                              Rank #{index + 1}
                            </div>
                          </div>

                          <div className="text-right">
                            <div className="text-sm text-slate-400">Visitante</div>
                            <div className="mt-1 text-base font-semibold sm:text-lg">
                              {match.away}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
                        <InfoCard label="Mercado" value={match.market} />
                        <InfoCard label="Cuota" value={String(match.odd)} />
                        <InfoCard
                          label="Momentum"
                          value={match.momentum}
                          valueClass={momentumColor[match.momentum] || "text-slate-300"}
                        />
                        <InfoCard
                          label="Estado"
                          value={match.cardStatus}
                          valueClass={
                            match.cardStatus === "Señal activa"
                              ? "text-emerald-400"
                              : "text-amber-400"
                          }
                        />
                      </div>
                    </div>

                    <details
                      className="group mt-4 rounded-2xl border border-white/10 bg-white/5"
                      open={match.expanded}
                    >
                      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-slate-200">
                        <span>Ver análisis desplegable</span>
                        <span className="text-slate-400 transition group-open:rotate-180">
                          ⌄
                        </span>
                      </summary>

                      <div className="grid gap-3 border-t border-white/10 px-4 py-4 sm:grid-cols-2 xl:grid-cols-4">
                        <PanelStat
                          title="Lectura IA"
                          value={match.momentum}
                          subtitle="Contexto táctico actual"
                        />
                        <PanelStat
                          title="Riesgo"
                          value={`${match.risk}/10`}
                          subtitle="Riesgo operativo"
                        />
                        <PanelStat
                          title="Value"
                          value={`${Number(match.value).toFixed(2)}`}
                          subtitle="Ventaja estimada"
                        />
                        <PanelStat
                          title="Motivo"
                          value={match.reason}
                          subtitle="Razón del sistema"
                        />
                      </div>
                    </details>
                  </div>
                </section>
              ))}
          </main>
        </div>
      </div>
    </div>
  );
}

function mapSignalItem(item, index) {
  const matchName =
    item.match_name ||
    item.partido ||
    item.nombre_partido ||
    "Partido sin nombre";

  const [home, away] = splitTeams(
    matchName,
    item.home_name || item.nombre_local || item.home_team || item.home,
    item.away_name || item.nombre_visitante || item.away_team || item.away
  );

  const minute = toNumber(item.minute ?? item.minuto);
  const score = buildScore(item);
  const signalLabel = item.rank || item.signal_rank || item.recomendacion_final || "ACEPTABLE";
  const momentum = item.momentum_label || item.context_state || item.match_state || "Controlado";

  return {
    id: item.signal_id || item.signal_key || `${matchName}-${index}`,
    league: item.league || item.liga || "Liga sin dato",
    country: item.country || item.pais || "País sin dato",
    minute,
    status: minute >= 46 ? "2T" : "1T",
    home,
    away,
    score,
    signal: normalizeSignal(signalLabel),
    signalScore: toNumber(item.signal_score ?? item.ai_score ?? item.score ?? 50),
    momentum: normalizeMomentum(momentum),
    market: item.market || item.mercado || "OVER",
    odd: item.odds ?? item.cuota ?? 0,
    expanded: index === 0,
    risk: item.risk_score ?? 0,
    value: item.value_edge ?? item.edge ?? 0,
    reason: item.opportunity_reason || item.reason || "SEÑAL_PUBLICADA",
    cardStatus: "Señal activa",
  };
}

function mapOpportunityItem(item, index, offset = 0) {
  const matchName =
    item.match_name ||
    item.nombre_partido ||
    item.partido ||
    "Partido sin nombre";

  const [home, away] = splitTeams(
    matchName,
    item.home_name || item.nombre_local || item.home_team || item.home,
    item.away_name || item.nombre_visitante || item.away_team || item.away
  );

  const minute = toNumber(item.minute ?? item.minuto);
  const score = buildScore(item);
  const momentum = item.context_state || item.match_state || "Controlado";

  return {
    id: item.opportunity_id || `${matchName}-opp-${index + offset}`,
    league: item.league || item.liga || "Liga sin dato",
    country: item.country || item.pais || "País sin dato",
    minute,
    status: minute >= 46 ? "2T" : "1T",
    home,
    away,
    score,
    signal: normalizeSignal(item.rank || "OBSERVACION"),
    signalScore: toNumber(item.ai_score ?? item.score ?? 50),
    momentum: normalizeMomentum(momentum),
    market: item.market || item.mercado || "N/A",
    odd: item.odds ?? item.cuota ?? 0,
    expanded: false,
    risk: item.risk_score ?? 0,
    value: item.value_edge ?? 0,
    reason: item.reason || "OBSERVE",
    cardStatus: "Oportunidad",
  };
}

function splitTeams(matchName, homeFallback, awayFallback) {
  if (homeFallback && awayFallback) return [homeFallback, awayFallback];

  if (String(matchName).includes(" vs ")) {
    const [home, away] = String(matchName).split(" vs ");
    return [home || "Local", away || "Visitante"];
  }

  return [homeFallback || matchName || "Local", awayFallback || "Visitante"];
}

function buildScore(item) {
  const direct = item.score || item.marcador || item.marcador_entrada;
  if (direct && String(direct).includes("-")) return String(direct);

  const homeScore =
    item.home_score ??
    item.local_score ??
    item.marcador_local ??
    item.score_home ??
    0;

  const awayScore =
    item.away_score ??
    item.visitor_score ??
    item.marcador_visitante ??
    item.score_away ??
    0;

  return `${homeScore}-${awayScore}`;
}

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function normalizeSignal(value) {
  const raw = String(value || "ACEPTABLE").toUpperCase();

  if (raw.includes("PREMIUM")) return "PREMIUM";
  if (raw.includes("FUERTE")) return "FUERTE";
  if (raw.includes("BUENA")) return "BUENA";
  if (raw.includes("OBSERV")) return "OBSERVACION";

  return "ACEPTABLE";
}

function normalizeMomentum(value) {
  const raw = String(value || "Controlado").toLowerCase();

  if (raw.includes("explos")) return "Explosivo";
  if (raw.includes("muy_caliente")) return "Caliente";
  if (raw.includes("calient")) return "Caliente";
  if (raw.includes("tibio")) return "Tibio";
  if (raw.includes("muert")) return "Muerto";

  return "Controlado";
}

function StateBox({ title, text }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-[#111827] p-6 shadow-xl">
      <div className="text-lg font-semibold">{title}</div>
      <div className="mt-2 text-sm text-slate-400">{text}</div>
    </div>
  );
}

function InfoCard({ label, value, valueClass = "text-white" }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`mt-1 text-sm font-semibold break-words ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}

function PanelStat({ title, value, subtitle }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1220] p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{title}</div>
      <div className="mt-2 text-lg font-semibold break-words">{value}</div>
      <div className="mt-1 text-sm text-slate-400">{subtitle}</div>
    </div>
  );
}
