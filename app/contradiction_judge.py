from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_upper(value: Any, default: str = "") -> str:
    try:
        if value is None:
            return default
        return str(value).upper()
    except Exception:
        return default


class ContradictionJudge:
    """
    Revisa contradicciones internas entre capas.

    Filosofia V17:
    - Este modulo NO debe matar oportunidades por pequeñas diferencias.
    - Este modulo NO decide la señal final.
    - Este modulo solo detecta incoherencias, riesgos de lectura y alertas internas.
    - MasterDecisionAI sigue siendo la autoridad final.

    Regla de seguridad:
    Solo CLOCK_CRITICAL y DATA_CRITICAL quedan como contradicciones criticas.
    Las nuevas incoherencias predictivas se agregan como warnings suaves para no romper
    el flujo oportunidad -> candidato -> señal.
    """

    def evaluate(
        self,
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
        pressure_quality: Optional[Dict[str, Any]] = None,
        break_scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        contradictions: List[str] = []
        warnings: List[str] = []
        critical: List[str] = []

        prediction = prediction or {}
        pressure_quality = pressure_quality or {}
        break_scenario = break_scenario or {}

        suggested_market = safe_upper(market.get("suggested_market") or "NO_BET", "NO_BET")

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        risk_score = safe_float(risk.get("risk_score"), 0.0)

        # ------------------------------------------------------------------
        # BLOQUEOS TECNICOS REALES
        # ------------------------------------------------------------------
        if not clock.get("clock_can_enter", False):
            contradictions.append("CLOCK_DOES_NOT_ALLOW_ENTER")

            if clock.get("clock_status") == "BLOCKED_CLOCK":
                critical.append("CLOCK_CRITICAL")

        if not data_quality.get("data_valid", False):
            contradictions.append("DATA_NOT_VALID")
            critical.append("DATA_CRITICAL")

        # ------------------------------------------------------------------
        # CONTRADICCIONES EXISTENTES V17
        # ------------------------------------------------------------------
        if suggested_market == "OVER":
            if score_hold_probability >= 75:
                contradictions.append("OVER_VS_SCORE_HOLD")

            if under_transition_score >= 75:
                contradictions.append("OVER_VS_UNDER_TRANSITION")

            if false_pressure_risk >= 75:
                contradictions.append("OVER_VS_FALSE_PRESSURE")

            if offensive_depth_score < 45:
                contradictions.append("OVER_WITHOUT_DEPTH")

        if suggested_market == "UNDER":
            if tactical_score >= 78 and over_score >= 68:
                contradictions.append("UNDER_VS_HIGH_ATTACK_ACTIVITY")

        if over_score >= 65 and under_score >= 65:
            contradictions.append("MARKET_SPLIT_OVER_UNDER")

        if risk_score >= 75:
            contradictions.append("HIGH_RISK_AGAINST_ENTER")
            warnings.append("RISK_DEMANDS_CONFIRMATION")

        if context.get("conmebol_late") and suggested_market == "OVER":
            if tactical_score < 72 or offensive_depth_score < 65:
                contradictions.append("CONMEBOL_OVER_WITHOUT_EXTRA_CONFIRMATION")

        # ------------------------------------------------------------------
        # NUEVAS ALERTAS SUAVES V17
        # No aumentan contradiction_score directamente.
        # Su objetivo es advertir incoherencias sin bloquear candidatos.
        # ------------------------------------------------------------------

        # 1) Incoherencia visual/operativa entre mercado sugerido y porcentajes.
        # Ejemplo detectado: Lectura OVER con OVER 23% y UNDER 81%.
        if suggested_market == "OVER":
            if under_score >= 70 and over_score <= 45 and (under_score - over_score) >= 25:
                warnings.append("OVER_UNDER_ALIGNMENT_WARNING")

        if suggested_market == "UNDER":
            if over_score >= 70 and under_score <= 45 and (over_score - under_score) >= 25:
                warnings.append("UNDER_OVER_ALIGNMENT_WARNING")

        # 2) Conflicto con prediccion de resultado/escenario.
        # Se mantiene como warning para que MasterDecision decida si degrada.
        prediction_market = safe_upper(
            prediction.get("recommended_market")
            or prediction.get("market_prediction")
            or prediction.get("predicted_market")
            or prediction.get("market"),
            "",
        )
        prediction_alignment = safe_upper(prediction.get("prediction_alignment"), "")
        likely_no_more_goals = safe_float(
            prediction.get("no_more_goals_probability")
            or prediction.get("score_hold_probability")
            or prediction.get("no_goal_probability"),
            0.0,
        )
        next_goal_probability = safe_float(
            prediction.get("next_goal_probability")
            or prediction.get("goal_probability")
            or prediction.get("one_more_goal_probability"),
            0.0,
        )

        if suggested_market == "OVER":
            if prediction_market == "UNDER" or prediction_alignment == "CONFLICT":
                warnings.append("PREDICTION_CONFLICT_WARNING")
            elif likely_no_more_goals >= 70 and next_goal_probability <= 45:
                warnings.append("PREDICTION_FAVORS_SCORE_HOLD")

        if suggested_market == "UNDER":
            if prediction_market == "OVER" or prediction_alignment == "CONFLICT":
                warnings.append("PREDICTION_CONFLICT_WARNING")
            elif next_goal_probability >= 70:
                warnings.append("PREDICTION_FAVORS_NEXT_GOAL")

        # 3) Lectura nueva de calidad de presion.
        pressure_state = safe_upper(
            pressure_quality.get("pressure_state")
            or pressure_quality.get("pressure_type")
            or pressure_quality.get("pressure_quality"),
            "",
        )
        real_goal_threat = safe_float(pressure_quality.get("real_goal_threat"), 0.0)
        pq_false_pressure_risk = safe_float(pressure_quality.get("false_pressure_risk"), false_pressure_risk)

        if suggested_market == "OVER":
            if pressure_state in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
                warnings.append("PRESSURE_QUALITY_WARNING")
            if pq_false_pressure_risk >= 75 and real_goal_threat < 55:
                warnings.append("FALSE_PRESSURE_OVER_WARNING")

        if suggested_market == "UNDER":
            if pressure_state in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"} or real_goal_threat >= 70:
                warnings.append("UNDER_AGAINST_REAL_THREAT_WARNING")

        # 4) Riesgo de ruptura/apertura del partido.
        # No bloquea. Sirve para bajar seguridad del UNDER o pedir confirmacion.
        break_risk = safe_float(break_scenario.get("break_risk"), 0.0)
        break_status = safe_upper(break_scenario.get("break_status") or break_scenario.get("status"), "")

        if break_risk >= 70 or break_status in {"HIGH", "HIGH_BREAK_RISK", "PARTIDO_CON_POSIBLE_RUPTURA"}:
            warnings.append("BREAK_RISK_WARNING")

        if suggested_market == "UNDER" and (break_risk >= 60 or break_status in {"MEDIUM", "HIGH", "HIGH_BREAK_RISK"}):
            warnings.append("UNDER_WITH_BREAK_RISK_WARNING")

        # Evita warnings duplicados manteniendo el orden original.
        warnings = list(dict.fromkeys(warnings))

        contradiction_score = len(contradictions) * 15 + len(critical) * 25
        contradiction_score = max(0, min(100, contradiction_score))

        if critical:
            status = "CRITICAL_CONTRADICTION"
            action = "BLOCK_OR_DEGRADE"
        elif contradiction_score >= 60:
            status = "STRONG_CONTRADICTION"
            action = "WAIT_CONFIRMATION"
        elif contradiction_score >= 30:
            status = "MODERATE_CONTRADICTION"
            action = "OBSERVE"
        else:
            status = "NO_CRITICAL_CONTRADICTION"
            action = "ALLOW_EVALUATION"

        return {
            "contradiction_status": status,
            "contradiction_score": round(contradiction_score, 2),
            "contradiction_action": action,
            "contradictions": contradictions,
            "contradiction_warnings": warnings,
            "critical_contradictions": critical,
        }
