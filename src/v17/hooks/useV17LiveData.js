import { useEffect, useMemo, useRef, useState } from "react";
import { fetchV17Dashboard } from "../services/apiV17";

const POLLING_MS = 30000;

const EMPTY_DASHBOARD = {
  ok: false,
  version: "V17",
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
  message: "Esperando datos V17...",
};

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeDashboard(payload) {
  if (!payload || typeof payload !== "object") {
    return EMPTY_DASHBOARD;
  }

  return {
    ...EMPTY_DASHBOARD,
    ...payload,
    top_signals: normalizeArray(payload.top_signals),
    observe: normalizeArray(payload.observe),
    no_bet: normalizeArray(payload.no_bet),
    blocked: normalizeArray(payload.blocked),
    pending_signals: normalizeArray(payload.pending_signals),
    closed_history: normalizeArray(payload.closed_history),
    history: normalizeArray(payload.history),
    stats: payload.stats || {},
    summary: payload.summary || {},
    learning: payload.learning || {},
    performance_analysis: payload.performance_analysis || {},
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
      const normalized = normalizeDashboard(payload);

      if (!mountedRef.current) return;

      setData(normalized);
      setError("");
      setLastFetchAt(new Date());
    } catch (err) {
      if (!mountedRef.current) return;

      setError(err?.message || "Error al cargar dashboard V17");
    } finally {
      if (!mountedRef.current) return;
      setLoading(false);
    }
  }

  useEffect(() => {
    mountedRef.current = true;

    load();

    const interval = setInterval(() => {
      load();
    }, POLLING_MS);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, []);

  const derived = useMemo(() => {
    const stats = data.stats || {};

    return {
      liveMatches: stats.live_matches ?? 0,
      analyzedMatches: stats.analyzed_matches ?? 0,
      publishedSignals: stats.published_signals ?? data.top_signals.length,
      observe: stats.observe ?? data.observe.length,
      noBet: stats.no_bet ?? data.no_bet.length,
      blocked: stats.blocked ?? data.blocked.length,
      pending: stats.pending ?? data.pending_signals.length,
      wins: stats.wins ?? 0,
      losses: stats.losses ?? 0,
      precision: stats.precision ?? 0,
    };
  }, [data]);

  return {
    data,
    stats: derived,
    loading,
    error,
    lastFetchAt,
    reload: load,
  };
    }
