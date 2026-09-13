from __future__ import annotations

from typing import Any, Dict, List


class LiveVisualEngine:
    """
    Capa visual IA para el panel premium.

    No crea señales.
    No decide mercados.
    No reemplaza al analizador táctico.
    Solo transforma datos tácticos ya existentes en datos visuales
    para Momentum, Radar, Riesgo, Estadísticas y Lectura Live.
    """

    def build(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any] | None = None,
        ai: Dict[str, Any] | None = None,
        deep: Dict[str, Any] | None = None,
        timeline: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}
        deep = deep or {}
        timeline = timeline or {}

        pressure = self._clamp(
            self._first(
                context.get("pressure_index"),
                match.get("pressure_index"),
                ai.get("pressure_index"),
            )
        )

        rhythm = self._clamp(
            self._first(
                context.get("rhythm_index"),
                match.get("rhythm_index"),
                ai.get("rhythm_index"),
            )
        )

        risk = self._clamp(
            self._first(
                match.get("risk_score"),
                ai.get("risk_score"),
                context.get("risk_score"),
                deep.get("retention_risk"),
            )
        )

        xg = self._safe_float(
            self._first(
                match.get("xg"),
                match.get("xG"),
                context.get("xg"),
                context.get("xg_pressure"),
                ai.get("xg"),
            )
        )

        goal_probability = self._clamp(
            self._first(
                ai.get("goal_probability"),
                match.get("goal_probability"),
                context.get("goal_probability"),
            )
        )

        over_probability = self._clamp(
            self._first(
                ai.get("over_probability"),
                match.get("over_probability"),
                context.get("over_probability"),
            )
        )

        under_probability = self._clamp(
            self._first(
                ai.get("under_probability"),
                match.get("under_probability"),
                context.get("under_probability"),
            )
        )

        projection_confidence = self._clamp(
            self._first(
                deep.get("deep_projection_confidence"),
                ai.get("ai_score"),
                match.get("ai_score"),
                match.get("signal_score"),
            )
        )

        pressure_trend = str(
            self._first(
                deep.get("deep_pressure_trend"),
                timeline.get("pressure_trend"),
                context.get("pressure_trend"),
                "UNKNOWN",
            )
        ).upper()

        rhythm_trend = str(
            self._first(
                deep.get("deep_rhythm_trend"),
                timeline.get("rhythm_trend"),
                context.get("rhythm_trend"),
                "UNKNOWN",
            )
        ).upper()

        goal_threat_trend = str(
            self._first(
                deep.get("deep_goal_threat_trend"),
                timeline.get("goal_threat_trend"),
                context.get("goal_threat_trend"),
                "UNKNOWN",
            )
        ).upper()

        projection_bias = str(
            self._first(
                deep.get("deep_projection_bias"),
                ai.get("recommendation"),
                match.get("market"),
                "NEUTRAL",
            )
        ).upper()

        chaos_mode = bool(deep.get("deep_chaos_mode") or context.get("chaos_mode"))
        late_reactivation = bool(
            deep.get("deep_late_reactivation") or context.get("late_reactivation")
        )
        cooling_detected = bool(
            context.get("cooling_detected") or match.get("cooling_detected")
        )
        fake_pressure = bool(
            deep.get("deep_fake_pressure_detected")
            or context.get("fake_pressure_detected")
        )

        live_intensity = self._live_intensity(
            pressure=pressure,
            rhythm=rhythm,
            goal_probability=goal_probability,
            over_probability=over_probability,
            projection_confidence=projection_confidence,
            risk=risk,
            chaos_mode=chaos_mode,
            late_reactivation=late_reactivation,
            cooling_detected=cooling_detected,
            fake_pressure=fake_pressure,
        )

        momentum_curve = self._curve(
            base=live_intensity,
            trend=self._dominant_trend(
                pressure_trend,
                rhythm_trend,
                goal_threat_trend,
            ),
            cooling=cooling_detected,
            chaos=chaos_mode,
            late_reactivation=late_reactivation,
        )

        pressure_curve = self._curve(
            base=pressure,
            trend=pressure_trend,
            cooling=cooling_detected,
            chaos=chaos_mode,
            late_reactivation=late_reactivation,
        )

        rhythm_curve = self._curve(
            base=rhythm,
            trend=rhythm_trend,
            cooling=cooling_detected,
            chaos=chaos_mode,
            late_reactivation=late_reactivation,
        )

        attack_flow = self._attack_flow(
            pressure=pressure,
            rhythm=rhythm,
            goal_probability=goal_probability,
            goal_threat_trend=goal_threat_trend,
            chaos=chaos_mode,
            cooling=cooling_detected,
        )

        radar = {
            "pressure": round(pressure, 1),
            "rhythm": round(rhythm, 1),
            "risk": round(risk, 1),
            "xg": round(xg, 2),
            "momentum": round(live_intensity, 1),
            "goal_threat": round(goal_probability, 1),
        }

        return {
            "visual_engine": "LIVE_VISUAL_ENGINE_V1",
            "live_intensity": round(live_intensity, 1),
            "intensity_label": self._intensity_label(live_intensity),
            "momentum_state": self._momentum_state(live_intensity, cooling_detected),
            "visual_state": self._visual_state(
                projection_bias=projection_bias,
                live_intensity=live_intensity,
                risk=risk,
                chaos_mode=chaos_mode,
                late_reactivation=late_reactivation,
                cooling_detected=cooling_detected,
                fake_pressure=fake_pressure,
            ),
            "momentum_curve": momentum_curve,
            "pressure_curve": pressure_curve,
            "rhythm_curve": rhythm_curve,
            "attack_flow": attack_flow,
            "radar": radar,
            "tactical_flags": {
                "chaos_mode": chaos_mode,
                "late_reactivation": late_reactivation,
                "cooling_detected": cooling_detected,
                "fake_pressure_detected": fake_pressure,
            },
            "labels": {
                "pressure": self._level_label(pressure),
                "rhythm": self._level_label(rhythm),
                "risk": self._risk_label(risk),
                "xg": self._xg_label(xg),
                "confidence": self._confidence_label(projection_confidence),
            },
            "probabilities": {
                "goal": round(goal_probability, 1),
                "over": round(over_probability, 1),
                "under": round(under_probability, 1),
                "confidence": round(projection_confidence, 1),
            },
        }

    def _live_intensity(
        self,
        pressure: float,
        rhythm: float,
        goal_probability: float,
        over_probability: float,
        projection_confidence: float,
        risk: float,
        chaos_mode: bool,
        late_reactivation: bool,
        cooling_detected: bool,
        fake_pressure: bool,
    ) -> float:
        value = (
            pressure * 0.30
            + rhythm * 0.25
            + goal_probability * 0.18
            + over_probability * 0.12
            + projection_confidence * 0.15
            - risk * 0.10
        )

        if chaos_mode:
            value += 12
        if late_reactivation:
            value += 10
        if cooling_detected:
            value -= 14
        if fake_pressure:
            value -= 10

        return self._clamp(value)

    def _curve(
        self,
        base: float,
        trend: str,
        cooling: bool,
        chaos: bool,
        late_reactivation: bool,
    ) -> List[float]:
        base = self._clamp(base)

        if chaos:
            offsets = [-18, 14, -10, 22, -6, 18, -12, 25, -8]
        elif late_reactivation:
            offsets = [-20, -14, -7, 2, 12, 22, 18, 28, 24]
        elif cooling or trend == "FALLING":
            offsets = [18, 12, 7, 3, -4, -9, -13, -17, -21]
        elif trend == "RISING":
            offsets = [-20, -13, -8, -1, 8, 15, 21, 16, 26]
        elif trend == "STABLE":
            offsets = [-6, 4, -2, 5, 0, 6, -3, 4, 1]
        else:
            offsets = [-8, 3, 7, -4, 5, 0, 6, -2, 4]

        return [round(self._clamp(base + x), 1) for x in offsets]

    def _attack_flow(
        self,
        pressure: float,
        rhythm: float,
        goal_probability: float,
        goal_threat_trend: str,
        chaos: bool,
        cooling: bool,
    ) -> List[float]:
        base = self._clamp(
            pressure * 0.35 + rhythm * 0.25 + goal_probability * 0.40
        )

        if chaos:
            offsets = [-10, 18, -6, 22, 4, 26]
        elif cooling or goal_threat_trend == "FALLING":
            offsets = [12, 5, 0, -8, -14, -20]
        elif goal_threat_trend == "RISING":
            offsets = [-18, -9, 2, 12, 22, 30]
        else:
            offsets = [-6, 4, 0, 8, -2, 5]

        return [round(self._clamp(base + x), 1) for x in offsets]

    def _dominant_trend(self, *trends: str) -> str:
        normalized = [str(t or "UNKNOWN").upper() for t in trends]

        if "RISING" in normalized:
            return "RISING"
        if "FALLING" in normalized:
            return "FALLING"
        if "STABLE" in normalized:
            return "STABLE"
        return "UNKNOWN"

    def _visual_state(
        self,
        projection_bias: str,
        live_intensity: float,
        risk: float,
        chaos_mode: bool,
        late_reactivation: bool,
        cooling_detected: bool,
        fake_pressure: bool,
    ) -> str:
        if chaos_mode:
            return "CHAOS_MODE"
        if late_reactivation:
            return "LATE_REACTIVATION"
        if fake_pressure:
            return "FAKE_PRESSURE"
        if cooling_detected:
            return "COOLING"
        if projection_bias in {"OVER", "OVER_WATCH"} and live_intensity >= 65:
            return "ATTACK_WINDOW"
        if projection_bias == "UNDER":
            return "RETENTION_WINDOW"
        if risk >= 70:
            return "HIGH_RISK"
        if live_intensity >= 70:
            return "HIGH_INTENSITY"
        if live_intensity >= 45:
            return "MEDIUM_INTENSITY"
        return "LOW_ACTIVITY"

    def _momentum_state(self, live_intensity: float, cooling: bool) -> str:
        if cooling:
            return "ENFRIANDO"
        if live_intensity >= 75:
            return "EXPLOSIVO"
        if live_intensity >= 60:
            return "ASCENDENTE"
        if live_intensity >= 40:
            return "ESTABLE"
        return "BAJO"

    def _intensity_label(self, value: float) -> str:
        if value >= 75:
            return "ALTA"
        if value >= 55:
            return "MEDIA"
        if value >= 35:
            return "BAJA"
        return "MUY BAJA"

    def _level_label(self, value: float) -> str:
        if value >= 75:
            return "ALTO"
        if value >= 50:
            return "MEDIO"
        if value >= 25:
            return "BAJO"
        return "MUY BAJO"

    def _risk_label(self, value: float) -> str:
        if value >= 70:
            return "ALTO"
        if value >= 45:
            return "MEDIO"
        return "BAJO"

    def _xg_label(self, value: float) -> str:
        if value >= 2.0:
            return "MUY ALTO"
        if value >= 1.2:
            return "ALTO"
        if value >= 0.7:
            return "MEDIO"
        if value > 0:
            return "BAJO"
        return "SIN DATO"

    def _confidence_label(self, value: float) -> str:
        if value >= 85:
            return "PREMIUM"
        if value >= 70:
            return "FUERTE"
        if value >= 55:
            return "MEDIA"
        if value >= 40:
            return "BAJA"
        return "OBSERVACIÓN"

    def _first(self, *values: Any) -> Any:
        for value in values:
            if value is not None and value != "":
                return value
        return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    def _clamp(self, value: Any) -> float:
        return max(0.0, min(100.0, self._safe_float(value)))
