import { useMemo } from "react";

const useMomentum = (signals = []) => {
  return useMemo(() => {
    if (!Array.isArray(signals) || signals.length === 0) return 0;

    const validSignals = signals.filter((s) => Number.isFinite(Number(s.intensity)));

    if (validSignals.length === 0) return 0;

    const avgIntensity =
      validSignals.reduce((acc, s) => acc + Number(s.intensity), 0) / validSignals.length;

    return Math.round(avgIntensity);
  }, [signals]);
};

export default useMomentum;
