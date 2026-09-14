import { useEffect, useMemo, useRef, useState } from "react";
import { fetchV17Dashboard } from "../services/apiV17";

const POLLING_MS = Math.max(5000, Number(import.meta.env.VITE_DASHBOARD_POLL_MS || 15000));
const EMPTY_DASHBOARD = {
  ok: false,
  version: "JHONNY_ELITE_20.0",
  live_matches: [],
  top_signals: [],
  observe: [],
  no_bet: [],
  blocked: [],
  pending_signals: [],
  closed_history: [],
  history: [],
  stats: {},
  summary: {},
  learning: {},
  performance_analysis: {},
  health: {},
  message: "Esperando datos de JHONNY ELITE...",
};

const arr = (value) => (Array.isArray(value) ? value : []);

function normalizeDashboard(payload) {
  if (!payload || typeof payload !== "object") return EMPTY_DASHBOARD;
  return {
    ...EMPTY_DASHBOARD,
    ...payload,
    live_matches: arr(payload.live_matches),
    top_signals: arr(payload.top_signals),
    observe: arr(payload.observe),
    no_bet: arr(payload.no_bet),
    blocked: arr(payload.blocked),
    pending_signals: arr(payload.pending_signals),
    closed_history: arr(payload.closed_history),
    history: arr(payload.history),
    stats: payload.stats || {},
    summary: payload.summary || {},
    learning: payload.learning || {},
    performance_analysis: payload.performance_analysis || {},
    health: payload.health || {},
  };
}

export function useV17LiveData() {
  const [data, setData] = useState(EMPTY_DASHBOARD);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastFetchAt, setLastFetchAt] = useState(null);
  const mountedRef = useRef(true);

  async function load() {
    try {
      const payload = await fetchV17Dashboard();
      if (!mountedRef.current) return;
      setData(normalizeDashboard(payload));
      setError("");
      setLastFetchAt(new Date());
    } catch (err) {
      if (mountedRef.current) setError(err?.message || "Error al cargar JHONNY ELITE");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    load();
    const interval = setInterval(load, POLLING_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, []);

  const stats = useMemo(() => {
    const raw = data.stats || {};
    return {
      liveMatches: raw.live_matches ?? data.live_matches.length,
      analyzedMatches: raw.analyzed_matches ?? data.live_matches.length,
      publishedSignals: raw.published_signals ?? data.top_signals.length,
      observe: raw.observe ?? data.observe.length,
      noBet: raw.no_bet ?? data.no_bet.length,
      blocked: raw.blocked ?? data.blocked.length,
      pending: raw.pending ?? data.pending_signals.length,
      wins: raw.wins ?? 0,
      losses: raw.losses ?? 0,
      precision: raw.precision ?? 0,
    };
  }, [data]);

  return { data, stats, loading, error, lastFetchAt, reload: load };
}
