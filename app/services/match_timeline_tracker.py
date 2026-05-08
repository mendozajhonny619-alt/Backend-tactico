from __future__ import annotations

import time
from typing import Any, Dict, List


class MatchTimelineTracker:
    """
    Guarda snapshots live del partido y calcula deltas temporales.

    No bloquea.
    No crea señales.
    No modifica probabilidades.

    Ahora también detecta:
    - reactivación tardía
    - caos ofensivo
    - presión desesperada
    - falso enfriamiento
    - transición partido muerto -> vivo
    """

    MAX_SNAPSHOTS_PER_MATCH = 80

    def __init__(self) -> None:
        self._timeline: Dict[str, List[Dict[str, Any]]] = {}

    def update(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}

        match_id = str(match.get("match_id") or match.get("id") or "")
        if not match_id:
            return self._empty_result()

        snapshot = self._build_snapshot(match, context, ai)

        history = self._timeline.setdefault(match_id, [])
        history.append(snapshot)

        if len(history) > self.MAX_SNAPSHOTS_PER_MATCH:
            self._timeline[match_id] = history[-self.MAX_SNAPSHOTS_PER_MATCH:]

        return self._analyze(self._timeline[match_id])

    def _build_snapshot(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "ts": time.time(),
            "minute": self._safe_int(match.get("minute") or context.get("minute")),
            "score": match.get("score") or f"{match.get('home_score', 0)}-{match.get('away_score', 0)}",

            "shots": self._safe_float(match.get("shots") or context.get("shots")),
            "shots_on_target": self._safe_float(match.get("shots_on_target") or context.get("shots_on_target")),
            "corners": self._safe_float(match.get("corners") or context.get("corners")),
            "dangerous_attacks": self._safe_float(match.get("dangerous_attacks") or context.get("dangerous_attacks")),
            "xg": self._safe_float(match.get("xg") or match.get("xG") or context.get("xg")),

            "pressure_index": self._safe_float(context.get("pressure_index")),
            "rhythm_index": self._safe_float(context.get("rhythm_index")),
            "goal_window_score": self._safe_float(context.get("goal_window_score")),
            "over_window_score": self._safe_float(context.get("over_window_score")),
            "under_transition_score": self._safe_float(context.get("under_transition_score")),
            "live_decay_factor": self._safe_float(context.get("live_decay_factor") or 1.0),
            "cooling_detected": bool(context.get("cooling_detected", False)),
            "context_state": str(context.get("context_state") or "N/A").upper(),

            "ai_score": self._safe_float(ai.get("ai_score")),
            "goal_probability": self._safe_float(ai.get("goal_probability")),
            "over_probability": self._safe_float(ai.get("over_probability")),
            "under_probability": self._safe_float(ai.get("under_probability")),
            "red_alert": bool(context.get("red_alert", False)),
        }

    def _analyze(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not history:
            return self._empty_result()

        current = history[-1]

        delta_3 = self._delta_since_minutes(history, 3)
        delta_5 = self._delta_since_minutes(history, 5)
        delta_10 = self._delta_since_minutes(history, 10)

        pressure_trend = self._trend(delta_5.get("pressure_index", 0.0))
        rhythm_trend = self._trend(delta_5.get("rhythm_index", 0.0))
        goal_threat_trend = self._trend(delta_5.get("goal_window_score", 0.0))

        late_reactivation = self._detect_late_reactivation(
            current=current,
            delta_3=delta_3,
            delta_5=delta_5,
        )

        chaos_mode = self._detect_chaos_mode(
            current=current,
            delta_3=delta_3,
        )

        signal_life_status = self._signal_life_status(
            current=current,
            delta_5=delta_5,
            pressure_trend=pressure_trend,
            rhythm_trend=rhythm_trend,
            goal_threat_trend=goal_threat_trend,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
        )

        return {
            "timeline_ready": len(history) >= 2,
            "timeline_snapshots": len(history),

            "delta_3m": delta_3,
            "delta_5m": delta_5,
            "delta_10m": delta_10,

            "pressure_trend": pressure_trend,
            "rhythm_trend": rhythm_trend,
            "goal_threat_trend": goal_threat_trend,

            "late_reactivation": late_reactivation,
            "chaos_mode": chaos_mode,

            "signal_life_status": signal_life_status,

            "timeline_summary": self._summary(
                pressure_trend=pressure_trend,
                rhythm_trend=rhythm_trend,
                goal_threat_trend=goal_threat_trend,
                signal_life_status=signal_life_status,
                current=current,
                late_reactivation=late_reactivation,
                chaos_mode=chaos_mode,
            ),
        }

    def _detect_late_reactivation(
        self,
        current: Dict[str, Any],
        delta_3: Dict[str, float],
        delta_5: Dict[str, float],
    ) -> bool:
        minute = self._safe_int(current.get("minute"))

        if minute < 70:
            return False

        pressure = self._safe_float(current.get("pressure_index"))
        rhythm = self._safe_float(current.get("rhythm_index"))

        recent_sot = self._safe_float(delta_3.get("shots_on_target"))
        recent_corners = self._safe_float(delta_3.get("corners"))
        recent_danger = self._safe_float(delta_3.get("dangerous_attacks"))

        return (
            pressure >= 18
            and rhythm >= 11
            and (
                recent_sot > 0
                or recent_corners >= 1
                or recent_danger >= 4
            )
        )

    def _detect_chaos_mode(
        self,
        current: Dict[str, Any],
        delta_3: Dict[str, float],
    ) -> bool:
        minute = self._safe_int(current.get("minute"))

        if minute < 75:
            return False

        pressure = self._safe_float(current.get("pressure_index"))
        rhythm = self._safe_float(current.get("rhythm_index"))

        recent_danger = self._safe_float(delta_3.get("dangerous_attacks"))
        recent_sot = self._safe_float(delta_3.get("shots_on_target"))

        return (
            pressure >= 24
            and rhythm >= 14
            and (
                recent_danger >= 6
                or recent_sot >= 1
            )
        )

    def _delta_since_minutes(
        self,
        history: List[Dict[str, Any]],
        minutes_back: int,
    ) -> Dict[str, float]:
        current = history[-1]
        current_minute = self._safe_int(current.get("minute"))
        target_minute = max(0, current_minute - minutes_back)

        base = history[0]
        for item in reversed(history):
            if self._safe_int(item.get("minute")) <= target_minute:
                base = item
                break

        keys = [
            "shots",
            "shots_on_target",
            "corners",
            "dangerous_attacks",
            "xg",
            "pressure_index",
            "rhythm_index",
            "goal_window_score",
            "over_window_score",
            "under_transition_score",
            "goal_probability",
            "over_probability",
            "under_probability",
        ]

        return {
            key: round(self._safe_float(current.get(key)) - self._safe_float(base.get(key)), 2)
            for key in keys
        }

    def _trend(self, value: float) -> str:
        if value >= 4:
            return "RISING"
        if value <= -4:
            return "FALLING"
        return "STABLE"

    def _signal_life_status(
        self,
        current: Dict[str, Any],
        delta_5: Dict[str, float],
        pressure_trend: str,
        rhythm_trend: str,
        goal_threat_trend: str,
        late_reactivation: bool,
        chaos_mode: bool,
    ) -> str:
        minute = self._safe_int(current.get("minute"))
        pressure = self._safe_float(current.get("pressure_index"))
        rhythm = self._safe_float(current.get("rhythm_index"))
        goal_window = self._safe_float(current.get("goal_window_score"))
        under_transition = self._safe_float(current.get("under_transition_score"))
        cooling = bool(current.get("cooling_detected", False))
        red_alert = bool(current.get("red_alert", False))

        recent_sot = self._safe_float(delta_5.get("shots_on_target"))
        recent_corners = self._safe_float(delta_5.get("corners"))
        recent_danger = self._safe_float(delta_5.get("dangerous_attacks"))

        if chaos_mode:
            return "CHAOS_ACTIVE"

        if late_reactivation:
            return "LATE_REACTIVATION"

        if red_alert and pressure >= 24 and rhythm >= 14:
            return "ACTIVE_DANGER"

        if (
            minute >= 80
            and cooling
            and under_transition >= 70
            and not late_reactivation
        ):
            return "NO_REENTRY"

        if (
            cooling
            and pressure_trend == "FALLING"
            and rhythm_trend == "FALLING"
            and not late_reactivation
        ):
            return "WEAKENING"

        if (
            pressure >= 18
            and rhythm >= 12
            and goal_window >= 18
            and (
                recent_sot > 0
                or recent_corners > 0
                or recent_danger >= 4
            )
        ):
            return "VALID"

        if goal_threat_trend == "RISING" or pressure_trend == "RISING":
            return "NEEDS_CONFIRMATION"

        if minute >= 75:
            return "AGING"

        return "OBSERVE"

    def _summary(
        self,
        pressure_trend: str,
        rhythm_trend: str,
        goal_threat_trend: str,
        signal_life_status: str,
        current: Dict[str, Any],
        late_reactivation: bool,
        chaos_mode: bool,
    ) -> str:
        if chaos_mode:
            return "Caos ofensivo detectado: partido abierto y altamente volátil."

        if late_reactivation:
            return "Reactivación tardía detectada: el partido volvió a acelerarse."

        if signal_life_status == "ACTIVE_DANGER":
            return "Peligro activo: presión y ritmo siguen altos."

        if signal_life_status == "VALID":
            return "Señal todavía vigente: hay actividad reciente que sostiene la lectura."

        if signal_life_status == "NEEDS_CONFIRMATION":
            return "La lectura muestra posible reactivación, pero necesita confirmación."

        if signal_life_status == "WEAKENING":
            return "La señal se está debilitando: presión y ritmo vienen cayendo."

        if signal_life_status == "NO_REENTRY":
            return "No reentrar: partido avanzado con enfriamiento y transición UNDER alta."

        if signal_life_status == "AGING":
            return "Señal envejecida por minuto avanzado; operar solo con nueva presión clara."

        if pressure_trend == "RISING" or rhythm_trend == "RISING" or goal_threat_trend == "RISING":
            return "El partido muestra señales de activación reciente."

        return "Lectura estable sin confirmación fuerte de nueva aceleración."

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "timeline_ready": False,
            "timeline_snapshots": 0,
            "delta_3m": {},
            "delta_5m": {},
            "delta_10m": {},
            "pressure_trend": "UNKNOWN",
            "rhythm_trend": "UNKNOWN",
            "goal_threat_trend": "UNKNOWN",
            "late_reactivation": False,
            "chaos_mode": False,
            "signal_life_status": "UNKNOWN",
            "timeline_summary": "Sin historial suficiente del partido.",
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
