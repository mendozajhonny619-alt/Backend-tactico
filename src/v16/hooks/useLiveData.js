// src/v16/hooks/useLiveData.js

import { useEffect, useState } from "react";

import { fetchLiveMatches } from "../services/api";

import { mapMatchData } from "../services/dataMapper";

const REFRESH_INTERVAL = 30000;

export default function useLiveData() {
  const [matches, setMatches] = useState([]);

  const [loading, setLoading] = useState(true);

  const [lastUpdate, setLastUpdate] = useState(null);

  const [error, setError] = useState(null);

  // =====================================
  // LOAD DATA
  // =====================================

  const loadData = async () => {
    try {
      setError(null);

      const rawMatches = await fetchLiveMatches();

      const mappedMatches = rawMatches.map(mapMatchData);

      // =============================
      // ORDENAMIENTO IA
      // =============================

      mappedMatches.sort((a, b) => {
        const scoreA =
          a.aiScore +
          a.signalScore +
          a.goalProbability;

        const scoreB =
          b.aiScore +
          b.signalScore +
          b.goalProbability;

        return scoreB - scoreA;
      });

      setMatches(mappedMatches);

      setLastUpdate(new Date());
    } catch (err) {
      console.error("ERROR LIVE DATA:", err);

      setError(err);
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // AUTO REFRESH
  // =====================================

  useEffect(() => {
    loadData();

    const interval = setInterval(() => {
      loadData();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  // =====================================
  // RETURN
  // =====================================

  return {
    matches,
    loading,
    error,
    lastUpdate,
    reload: loadData,
  };
            }
