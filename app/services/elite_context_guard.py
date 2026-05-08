from __future__ import annotations

from typing import Any, Dict, List


class EliteContextGuard:
    """
    Ayudante del filtro élite.

    No bloquea señales directamente.
    No publica señales.
    Solo detecta contextos peligrosos y devuelve:
    - context_guard_status
    - context_guard_score
    - context_guard_warnings
    - context_guard_advice
    """

    def evaluate(
        self,
        signal: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        penalty = 0.0

        minute = self._safe_int(signal.get("minute"))
        home_score = self._safe_int(signal.get("home_score"))
        away_score = self._safe_int(signal.get("away_score"))
        total_goals = home_score + away_score
        goal_diff = abs(home_score - away_score)

        ai_score = self._safe_float(ai.get("ai_score") or signal.get("ai_score"))
        goal_prob = self._safe_float(ai.get("goal_probability") or signal.get("goal_probability"))
        over_prob = self._safe_float(ai.get("over_probability") or signal.get("over_probability"))
        under_prob = self._safe_float(ai.get("under_probability") or signal.get("under_probability"))

        risk_score = self._safe_float(risk.get("risk_score") or signal.get("risk_score"))
        risk_level = str(risk.get("risk_level") or signal.get("risk_level") or "").upper()

        pressure = self._safe_float(context.get("pressure_index") or signal.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index") or signal.get("rhythm_index"))
        data_quality = str(context.get("data_quality") or signal.get("data_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or signal.get("context_state") or "").upper()
        market = str(signal.get("market") or "").upper()
        rank = str(signal.get("rank") or "").upper()

        final_decision = str(signal.get("final_decision") or "").upper()
        signal_decay_status = str(signal.get("signal_decay_status") or "").upper()
        revalidation_status = str(signal.get("revalidation_status") or "").upper()
        risk_reducer_status = str(signal.get("risk_reducer_status") or "").upper()

        retention_risk = self._safe_float(signal.get("retention_risk"))
        score_hold_probability = self._safe_float(signal.get("score_hold_probability"))
        under_transition_score = self._safe_float(
            context.get("under_transition_score") or signal.get("under_transition_score")
        )

        fake_pressure_detected = bool(
            context.get("fake_pressure_detected")
            or signal.get("fake_pressure_detected")
            or signal.get("deep_fake_pressure_detected")
        )
        pressure_without_depth = bool(
            context.get("pressure_without_depth")
            or signal.get("pressure_without_depth")
            or signal.get("deep_pressure_without_depth")
        )

        # 1) Datos débiles
        if data_quality == "LOW":
            penalty += 10
            warnings.append("LOW_DATA_CONTEXT")

        # 2) Partido resuelto / marcador peligroso
        if goal_diff >= 3 and minute >= 60:
            penalty += 22
            warnings.append("MATCH_ALREADY_RESOLVED")

        if total_goals >= 4 and minute >= 65:
            penalty += 16
            warnings.append("OVEREXTENDED_SCORELINE")

        # 3) Minuto peligroso
        if minute >= 78 and "OVER" in market:
            penalty += 12
            warnings.append("LATE_OVER_ENTRY_RISK")

        if minute <= 12:
            penalty += 8
            warnings.append("TOO_EARLY_SIGNAL")

        # 4) OVER sin presión suficiente
        if "OVER" in market:
            if goal_prob >= 65 and pressure < 9:
                penalty += 10
                warnings.append("OVER_PROB_HIGH_BUT_PRESSURE_LOW")

            if over_prob >= 65 and rhythm < 6:
                penalty += 8
                warnings.append("OVER_PROB_HIGH_BUT_RHYTHM_LOW")

            if context_state in {"FRIO", "MUERTO", "CONTROLADO"}:
                penalty += 12
                warnings.append("OVER_AGAINST_COLD_CONTEXT")

            if retention_risk >= 70 or score_hold_probability >= 70:
                penalty += 18
                warnings.append("OVER_AGAINST_RETENTION_RISK")

            if fake_pressure_detected or pressure_without_depth:
                penalty += 18
                warnings.append("OVER_FAKE_PRESSURE_OR_NO_DEPTH")

            if under_transition_score >= 70:
                penalty += 14
                warnings.append("OVER_AGAINST_UNDER_TRANSITION")

        # 5) UNDER con señales ofensivas fuertes en contra
        if "UNDER" in market:
            if goal_prob >= 60:
                penalty += 12
                warnings.append("UNDER_AGAINST_GOAL_PROBABILITY")

            if pressure >= 18 or rhythm >= 14:
                penalty += 10
                warnings.append("UNDER_AGAINST_HIGH_TEMPO")

            if context_state in {"CALIENTE", "MUY_CALIENTE"}:
                penalty += 14
                warnings.append("UNDER_AGAINST_HOT_CONTEXT")

        # 6) Riesgo alto
        if risk_level == "ALTO" or risk_score >= 7.0:
            penalty += 14
            warnings.append("HIGH_RISK_CONTEXT")

        # 7) Rank alto pero contexto no acompaña
        if rank in {"PREMIUM", "FUERTE"}:
            if ai_score < 65:
                penalty += 8
                warnings.append("HIGH_RANK_WITH_MODEST_AI_SCORE")

            if context_state not in {"TIBIO", "CALIENTE", "MUY_CALIENTE", "CONTROLADO"}:
                penalty += 6
                warnings.append("HIGH_RANK_WITH_UNCLEAR_CONTEXT")

        # 8) Coordinación con decisión/vida/revalidación
        if final_decision == "WAIT":
            penalty += 8
            warnings.append("FINAL_DECISION_WAIT")

        if final_decision == "NO_REENTRY":
            penalty += 18
            warnings.append("FINAL_DECISION_NO_REENTRY")

        if final_decision == "AVOID":
            penalty += 28
            warnings.append("FINAL_DECISION_AVOID")

        if signal_decay_status in {"COOLING", "NO_REENTRY", "AVOID"}:
            penalty += 14
            warnings.append("SIGNAL_DECAY_DEGRADED")

        if revalidation_status in {"COOLING", "HIGH_RISK", "NO_REENTRY", "AVOID"}:
            penalty += 14
            warnings.append("REVALIDATION_DEGRADED")

        if risk_reducer_status in {"HIGH_CAUTION", "NO_REENTRY", "AVOID"}:
            penalty += 14
            warnings.append("RISK_REDUCER_WARNING")

        guard_score = max(0.0, min(100.0, 100.0 - penalty))

        if guard_score >= 80:
            status = "CLEAR"
            advice = "Contexto limpio. No se detectan riesgos importantes."
        elif guard_score >= 60:
            status = "CAUTION"
            advice = "Contexto aceptable, pero conviene mantener prudencia."
        elif guard_score >= 40:
            status = "WARNING"
            advice = "Contexto delicado. Conviene bajar rango o esperar confirmación."
        else:
            status = "DANGER"
            advice = "Contexto peligroso. Señal con alto riesgo de falso positivo."

        return {
            "context_guard_status": status,
            "context_guard_score": round(guard_score, 2),
            "context_guard_penalty": round(penalty, 2),
            "context_guard_warnings": warnings,
            "context_guard_advice": advice,
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
