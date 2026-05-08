from __future__ import annotations

from typing import Any, Dict, List


class FinalDecisionEngine:
    """
    Capa maestra final.
    No reemplaza el scanner.
    Solo decide si una señal realmente debe publicarse,
    observarse o evitarse.
    """

    def evaluate(
        self,
        signal: Dict[str, Any],
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        market: Dict[str, Any] | None = None,
        value: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        reasons: List[str] = []

        minute = self._safe_float(signal.get("minute"))
        market_type = str(signal.get("market") or "").upper()

        goal_prob = self._safe_float(signal.get("goal_probability"))
        over_prob = self._safe_float(signal.get("over_probability"))
        under_prob = self._safe_float(signal.get("under_probability"))
        score_hold = self._safe_float(signal.get("score_hold_probability"))

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        shots_on_target = self._safe_float(signal.get("shots_on_target"))
        shots = self._safe_float(signal.get("shots"))
        corners = self._safe_float(signal.get("corners"))

        risk_level = str(signal.get("risk_level") or "").upper()
        risk_score = self._safe_float(signal.get("risk_score"))

        market_status = str(signal.get("market_status") or "").upper()
        signal_life = str(signal.get("signal_life_status") or signal.get("deep_signal_life_status") or "").upper()
        retention_risk = str(signal.get("retention_risk") or "").upper()
        context_state = str(signal.get("context_state") or "").upper()

        # 1. Bloqueo por minutos muertos
        if 43 <= minute <= 45:
            if not self._has_extreme_confirmation(pressure, rhythm, shots_on_target, shots):
                return self._decision(
                    "AVOID",
                    "BLOCK_DEAD_MINUTE_FIRST_HALF",
                    ["Minuto peligroso antes del descanso sin confirmación extrema."],
                )

        if minute >= 88:
            if not self._has_extreme_confirmation(pressure, rhythm, shots_on_target, shots):
                return self._decision(
                    "AVOID",
                    "BLOCK_DEAD_MINUTE_FINAL",
                    ["Minuto final sin confirmación extrema."],
                )

        # 2. Retención mayor que gol
        if market_type == "OVER":
            if score_hold >= 60 and score_hold > goal_prob:
                return self._decision(
                    "OBSERVE",
                    "RETENTION_OVER_GOAL_PROBABILITY",
                    [
                        f"Retención alta ({score_hold}%) supera probabilidad de gol ({goal_prob}%).",
                        "No conviene publicar OVER todavía.",
                    ],
                )

        # 3. Mercado UNDER fuerte contra OVER
        if market_type == "OVER":
            if under_prob >= 62 and under_prob > over_prob:
                return self._decision(
                    "WAIT",
                    "UNDER_DOMINATES_OVER",
                    [
                        f"UNDER ({under_prob}%) domina sobre OVER ({over_prob}%).",
                        "El mercado/contexto no acompaña entrada OVER.",
                    ],
                )

        # 4. Presión sin tiros reales
        if market_type == "OVER":
            if pressure >= 12 and rhythm >= 6 and shots_on_target <= 0:
                return self._decision(
                    "OBSERVE",
                    "PRESSURE_WITHOUT_REAL_SHOTS",
                    [
                        "Hay presión, pero no hay tiros al arco.",
                        "Actividad ofensiva no es confirmación real.",
                    ],
                )

        # 5. Señal viva débil
        if signal_life in {"WEAK", "DEAD", "EXPIRED", "LOW"}:
            return self._decision(
                "NO_REENTRY",
                "SIGNAL_LIFE_DEGRADED",
                ["La vida de señal está degradada o vencida."],
            )

        # 6. Riesgo alto
        if risk_level == "ALTO" and risk_score >= 7:
            return self._decision(
                "AVOID",
                "HIGH_RISK_CONTEXT",
                ["Riesgo alto detectado por el sistema."],
            )

        # 7. Partido muerto o frío para OVER
        if market_type == "OVER":
            if context_state in {"MUERTO", "FRIO"} and goal_prob < 60:
                return self._decision(
                    "WAIT",
                    "COLD_CONTEXT_FOR_OVER",
                    ["Contexto frío/muerto para buscar OVER."],
                )

        # 8. Mercado interno sin cuota real
        if market_status == "INTERNAL_ONLY":
            return self._decision(
                "OBSERVE",
                "INTERNAL_ONLY_MARKET",
                ["Señal interna sin validación completa de mercado real."],
            )

        # 9. Confirmación real
        if market_type == "OVER":
            if (
                goal_prob >= 64
                and over_prob >= 64
                and pressure >= 9
                and rhythm >= 6
                and risk_score < 7
            ):
                return self._decision(
                    "ENTER",
                    "FINAL_OVER_CONFIRMED",
                    ["Momentum, probabilidad y riesgo aceptables para OVER."],
                )

        if market_type == "UNDER":
            if (
                under_prob >= 65
                and goal_prob <= 55
                and pressure <= 14
                and rhythm <= 10
                and risk_score < 7
            ):
                return self._decision(
                    "ENTER",
                    "FINAL_UNDER_CONFIRMED",
                    ["Retención/control y baja amenaza favorecen UNDER."],
                )

        return self._decision(
            "WAIT",
            "WAIT_MORE_CONFIRMATION",
            ["No hay confirmación final suficiente para entrada."],
        )

    def _has_extreme_confirmation(
        self,
        pressure: float,
        rhythm: float,
        shots_on_target: float,
        shots: float,
    ) -> bool:
        return (
            pressure >= 18
            and rhythm >= 10
            and (shots_on_target >= 2 or shots >= 6)
        )

    def _decision(self, decision: str, reason: str, details: List[str]) -> Dict[str, Any]:
        return {
            "final_decision": decision,
            "final_decision_reason": reason,
            "final_decision_details": details,
            "allow_publish": decision == "ENTER",
        }

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
