from __future__ import annotations

from typing import Any, Dict


class SportsAIAgent:
    """
    Agente IA deportivo contextual.

    Función:
    - unir lecturas tácticas
    - interpretar contexto
    - detectar riesgo
    - explicar la lectura
    - sugerir acción operativa

    No crea señales.
    No reemplaza ScanService.
    No decide apuestas directamente.
    Solo entrega una capa de pensamiento contextual.
    """

    def think(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any] | None = None,
        ai: Dict[str, Any] | None = None,
        league_stability: Dict[str, Any] | None = None,
        next_goal_ai: Dict[str, Any] | None = None,
        deep_analysis: Dict[str, Any] | None = None,
        team_memory_home: Dict[str, Any] | None = None,
        team_memory_away: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        match = match or {}
        context = context or {}
        ai = ai or {}
        league_stability = league_stability or {}
        next_goal_ai = next_goal_ai or {}
        deep_analysis = deep_analysis or {}
        team_memory_home = team_memory_home or {}
        team_memory_away = team_memory_away or {}

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))

        context_state = str(context.get("context_state") or "").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()

        league_level = str(
            league_stability.get("league_stability_level")
            or ""
        ).upper()

        danger_level = str(
            league_stability.get("danger_level")
            or ""
        ).upper()

        next_goal_bias = str(
            next_goal_ai.get("next_goal_bias_ai")
            or ""
        ).upper()

        next_goal_confidence = self._safe_float(
            next_goal_ai.get("next_goal_confidence_ai")
        )

        fake_pressure = bool(
            next_goal_ai.get("next_goal_fake_pressure")
        )

        deep_bias = str(
            deep_analysis.get("deep_projection_bias")
            or ""
        ).upper()

        deep_confidence = self._safe_float(
            deep_analysis.get("deep_projection_confidence")
        )

        home_profile = str(
            team_memory_home.get("rhythm_profile")
            or "UNKNOWN"
        ).upper()

        away_profile = str(
            team_memory_away.get("rhythm_profile")
            or "UNKNOWN"
        ).upper()

        risk_flags = self._risk_flags(
            data_quality=data_quality,
            league_level=league_level,
            danger_level=danger_level,
            fake_pressure=fake_pressure,
            pressure=pressure,
            rhythm=rhythm,
        )

        tactical_bias = self._tactical_bias(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            deep_bias=deep_bias,
            deep_confidence=deep_confidence,
        )

        action = self._action(
            tactical_bias=tactical_bias,
            risk_flags=risk_flags,
            ai_score=ai_score,
            data_quality=data_quality,
            league_level=league_level,
            fake_pressure=fake_pressure,
        )

        confidence = self._confidence(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            deep_confidence=deep_confidence,
            next_goal_confidence=next_goal_confidence,
            risk_flags=risk_flags,
        )

        return {
            "sports_ai_agent_enabled": True,
            "sports_ai_action": action,
            "sports_ai_tactical_bias": tactical_bias,
            "sports_ai_confidence": round(confidence, 2),
            "sports_ai_risk_flags": risk_flags,
            "sports_ai_next_goal_bias": next_goal_bias,
            "sports_ai_next_goal_confidence": round(next_goal_confidence, 2),
            "sports_ai_league_level": league_level,
            "sports_ai_danger_level": danger_level,
            "sports_ai_home_profile": home_profile,
            "sports_ai_away_profile": away_profile,
            "sports_ai_summary": self._summary(
                action=action,
                tactical_bias=tactical_bias,
                confidence=confidence,
                league_level=league_level,
                next_goal_bias=next_goal_bias,
                fake_pressure=fake_pressure,
                risk_flags=risk_flags,
            ),
        }

    def _risk_flags(
        self,
        data_quality: str,
        league_level: str,
        danger_level: str,
        fake_pressure: bool,
        pressure: float,
        rhythm: float,
    ) -> list[str]:

        flags: list[str] = []

        if data_quality == "LOW":
            flags.append("LOW_DATA_QUALITY")

        if league_level in {"PELIGROSA", "INESTABLE"}:
            flags.append("LEAGUE_UNSTABLE")

        if danger_level in {"ALTO", "EXTREMO"}:
            flags.append("LEAGUE_DANGER_HIGH")

        if fake_pressure:
            flags.append("FAKE_PRESSURE_WARNING")

        if pressure <= 8 and rhythm <= 5:
            flags.append("LOW_ACTIVITY_CONTEXT")

        return flags

    def _tactical_bias(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        pressure: float,
        rhythm: float,
        context_state: str,
        deep_bias: str,
        deep_confidence: float,
    ) -> str:

        if deep_bias == "UNDER" and deep_confidence >= 70:
            return "UNDER"

        if deep_bias in {"OVER", "OVER_WATCH"} and deep_confidence >= 70:
            return "OVER"

        if (
            ai_score >= 62
            and goal_probability >= 64
            and over_probability >= 64
            and pressure >= 10
            and rhythm >= 6
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        ):
            return "OVER"

        if (
            ai_score >= 58
            and under_probability >= 62
            and goal_probability <= 55
            and pressure <= 14
            and rhythm <= 10
            and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
        ):
            return "UNDER"

        return "NEUTRAL"

    def _action(
        self,
        tactical_bias: str,
        risk_flags: list[str],
        ai_score: float,
        data_quality: str,
        league_level: str,
        fake_pressure: bool,
    ) -> str:

        if fake_pressure:
            return "WAIT_CONFIRMATION"

        if "LOW_DATA_QUALITY" in risk_flags and ai_score < 78:
            return "OBSERVE"

        if league_level in {"PELIGROSA", "INESTABLE"} and ai_score < 82:
            return "OBSERVE_STRICT"

        if tactical_bias in {"OVER", "UNDER"} and not risk_flags:
            return "ALLOW_ANALYSIS"

        if tactical_bias in {"OVER", "UNDER"}:
            return "ALLOW_ONLY_WITH_CONFIRMATION"

        return "WAIT"

    def _confidence(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        deep_confidence: float,
        next_goal_confidence: float,
        risk_flags: list[str],
    ) -> float:

        base = (
            ai_score * 0.30
            + max(goal_probability, over_probability, under_probability) * 0.30
            + deep_confidence * 0.25
            + next_goal_confidence * 0.15
        )

        penalty = len(risk_flags) * 7.5

        return max(0.0, min(100.0, base - penalty))

    def _summary(
        self,
        action: str,
        tactical_bias: str,
        confidence: float,
        league_level: str,
        next_goal_bias: str,
        fake_pressure: bool,
        risk_flags: list[str],
    ) -> str:

        if fake_pressure:
            return (
                "Sports AI detecta posible presión falsa. "
                "No operar sin confirmación ofensiva real."
            )

        if tactical_bias in {"OVER", "UNDER"}:
            return (
                f"Sports AI detecta sesgo {tactical_bias} "
                f"con confianza {round(confidence, 1)}%. "
                f"Acción sugerida: {action}. "
                f"Liga: {league_level or 'NO_CLASIFICADA'}. "
                f"Next Goal: {next_goal_bias or 'NEUTRAL'}."
            )

        if risk_flags:
            return (
                "Sports AI mantiene observación por riesgos contextuales: "
                + ", ".join(risk_flags)
            )

        return "Sports AI sin ventaja táctica fuerte. Mantener observación."

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
