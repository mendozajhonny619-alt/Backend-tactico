import { useMemo } from "react";

const useSignalFeed = (signals = []) => {
  return useMemo(() => {
    if (!Array.isArray(signals)) return [];

    return signals.slice(0, 12).map((s, index) => ({
      id: s.id || `signal-${index}`,
      type: s.type || s.market || "SIGNAL",
      confidence: s.confidence ?? s.signalScore ?? s.signal_score ?? "—",
      intensity: s.intensity ?? s.pressureIndex ?? s.pressure_index ?? "—",
      context: s.contextState || s.context_state || "Live tactical event",
      label: `${s.type || s.market || "SIGNAL"} • Confianza: ${
        s.confidence ?? s.signalScore ?? s.signal_score ?? "—"
      }% • Intensidad: ${s.intensity ?? s.pressureIndex ?? s.pressure_index ?? "—"}`,
    }));
  }, [signals]);
};

export default useSignalFeed;
