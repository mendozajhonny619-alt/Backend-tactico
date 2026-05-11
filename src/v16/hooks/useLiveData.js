// src/v16/hooks/useLiveData.js

import { useEffect, useState } from "react";
import {
  fetchLiveMatches,
  fetchSignals,
  fetchStats,
  fetchHistory,
  fetchOpportunities,
} from "../services/api";
import { mapMatchData } from "../services/dataMapper";

const REFRESH_INTERVAL = 15000;

export default function useLiveData() {
  const [matches, setMatches] = useState([]);
  const [signals, setSignals] = useState([]);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [opportunities, setOpportunities] = useState(null);
  const [systemStatus, setSystemStatus] = useState({
    active: false,
    riskLevel: "MEDIO",
    lastUpdate: null,
  });

  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const safeArray = (value) => {
    if (Array.isArray(value)) return value;
    if (Array.isArray(value?.items)) return value.items;
    if (Array.isArray(value?.signals)) return value.signals;
    if (Array.isArray(value?.history)) return value.history;
    return [];
  };

  const loadData = async () => {
    try {
      setError(null);

      const [
        rawMatches,
        rawSignals,
        rawStats,
        rawHistory,
        rawOpportunities,
      ] = await Promise.allSettled([
        fetchLiveMatches(),
        fetchSignals(),
        fetchStats(),
        fetchHistory(),
        fetchOpportunities(),
      ]);

      const liveMatches =
        rawMatches.status === "fulfilled" ? safeArray(rawMatches.value) : [];

      const mappedMatches = liveMatches.map(mapMatchData);

      mappedMatches.sort((a, b) => {
        const scoreA =
          Number(a.aiScore || a.ai_score || 0) +
          Number(a.signalScore || a.signal_score || 0) +
          Number(a.goalProbability || a.goal_probability || 0);

        const scoreB =
          Number(b.aiScore || b.ai_score || 0) +
          Number(b.signalScore || b.signal_score || 0) +
          Number(b.goalProbability || b.goal_probability || 0);

        return scoreB - scoreA;
      });

      const signalList =
        rawSignals.status === "fulfilled" ? safeArray(rawSignals.value) : [];

      const statsData =
        rawStats.status === "fulfilled" ? rawStats.value?.stats || rawStats.value : null;

      const historyList =
        rawHistory.status === "fulfilled" ? safeArray(rawHistory.value) : [];

      const opportunitiesData =
        rawOpportunities.status === "fulfilled" ? rawOpportunities.value : null;

      const now = new Date();

      setMatches(mappedMatches);
      setSignals(signalList);
      setStats(statsData);
      setHistory(historyList);
      setOpportunities(opportunitiesData);
      setLastUpdate(now);

      setSystemStatus({
        active: true,
        riskLevel:
          statsData?.risk_level ||
          statsData?.riskLevel ||
          opportunitiesData?.summary?.risk_level ||
          "MEDIO",
        lastUpdate: now,
        signalsCount: signalList.length,
        liveMatchesCount:
          statsData?.live_matches_count ||
          statsData?.live_matches ||
          mappedMatches.length,
        precision:
          statsData?.precision ||
          statsData?.accuracy ||
          statsData?.win_rate ||
          0,
        roi:
          statsData?.roi ||
          statsData?.roi_today ||
          0,
      });
    } catch (err) {
      console.error("ERROR LIVE DATA:", err);
      setError(err);

      setSystemStatus((prev) => ({
        ...prev,
        active: false,
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    const interval = setInterval(() => {
      loadData();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  return {
    matches,
    signals,
    stats,
    history,
    opportunities,
    systemStatus,
    loading,
    error,
    lastUpdate,
    reload: loadData,
  };
                 }
