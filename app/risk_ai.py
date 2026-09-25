from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí"}
    return bool(value)


def first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def first_value(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not None:
            return value
    return default


class RiskAI:
    """
    Detecta riesgos operativos y tácticos sin convertirse en el juez final.

    Filosofía V17:
    - RiskAI NO decide ENTER.
    - RiskAI NO debe matar oportunidades por pequeñas dudas.
    - RiskAI identifica trampas, advertencias y riesgos de fallo.
    - MasterDecisionAI conserva la autoridad final.

    Riesgos principales:
    - reloj no confiable
    - datos inválidos o débiles
    - CONMEBOL tardío sin confirmación
    - presión falsa
    - dominio sin profundidad
    - score hold
    - señal envejecida o sin reactivación
    - conflicto entre mercado sugerido y resultado probable
    - riesgo de ruptura del partido
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = safe_int(match.get("api_minute"), 0)

        risk_reasons: List[str] = []
        risk_warnings: List[str] = []
        hard_blockers: List[str] = []
        risk_tags: List[str] = []

        risk_score = 0.0

        # ------------------------------------------------------------------
        # 1) Calidad base: se mantiene la protección existente.
        # ------------------------------------------------------------------
        if not data_quality.get("data_valid", False):
            risk_score += 35
            hard_blockers.extend(data_quality.get("data_issues", []))

        # Datos débiles NO significan oportunidad muerta.
        # En ligas con poca cobertura se tratan como LOW_DATA_RISK, no como bloqueo.
        low_data_league = safe_bool(
            first_value(
                context.get("low_data_league"),
                context.get("is_low_data_league"),
                context.get("limited_data_league"),
                match.get("low_data_league"),
                default=False,
            )
        )

        if data_quality.get("data_weak", False):
            if low_data_league:
                risk_score += 8
                risk_tags.append("LOW_DATA_CANDIDATE")
                risk_warnings.append("LOW_DATA_LEAGUE_MODE")
            else:
                risk_score += 12
            risk_warnings.extend(data_quality.get("data_warnings", []))

        if not clock.get("clock_can_enter", False):
            risk_score += 30
            if clock.get("clock_status") == "BLOCKED_CLOCK":
                hard_blockers.extend(clock.get("clock_blockers", []))
            else:
                risk_warnings.extend(clock.get("clock_warnings", []))

        # ------------------------------------------------------------------
        # 2) Contexto general.
        # ------------------------------------------------------------------
        is_conmebol = bool(context.get("is_conmebol", False))
        conmebol_late = bool(context.get("conmebol_late", False))
        suggested_market = str(market.get("suggested_market") or "NO_BET").upper()

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        total_shots_on = safe_int(match.get("total_shots_on"), 0)

        # ------------------------------------------------------------------
        # 3) Integración ligera con PressureQualityAI.
        # No cambia la arquitectura: consume campos si existen.
        # ------------------------------------------------------------------
        pressure_quality = first_dict(
            tactical.get("pressure_quality"),
            context.get("pressure_quality"),
            match.get("pressure_quality"),
        )

        pressure_state = str(
            first_value(
                pressure_quality.get("pressure_state"),
                pressure_quality.get("state"),
                tactical.get("pressure_state"),
                context.get("pressure_state"),
                default="",
            )
        ).upper()

        game_state = str(
            first_value(
                pressure_quality.get("game_state"),
                tactical.get("game_state"),
                context.get("game_state"),
                default="",
            )
        ).upper()

        real_goal_threat = safe_float(
            first_value(
                pressure_quality.get("real_goal_threat"),
                tactical.get("real_goal_threat"),
                context.get("real_goal_threat"),
                default=0.0,
            )
        )

        pressure_false_risk_ai = safe_float(
            first_value(
                pressure_quality.get("false_pressure_risk"),
                tactical.get("pressure_false_risk"),
                default=false_pressure_risk,
            )
        )

        if pressure_false_risk_ai >= 75 or false_pressure_risk >= 75:
            risk_score += 22
            risk_reasons.append("FALSE_PRESSURE_RISK")

        if pressure_state in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
            risk_score += 10
            risk_reasons.append(pressure_state)

        if pressure_state == "HIGH_THREAT_PRESSURE" or real_goal_threat >= 75:
            # No elimina riesgo ya detectado; solo reconoce que la presión sí tiene amenaza.
            risk_score -= 6
            risk_tags.append("REAL_GOAL_THREAT_CONFIRMED")

        # ------------------------------------------------------------------
        # 4) Riesgos clásicos OVER / UNDER.
        # ------------------------------------------------------------------
        if suggested_market == "OVER" and total_shots_on <= 1 and minute >= 55:
            risk_score += 18
            risk_reasons.append("OVER_WITH_LOW_SHOTS_ON_TARGET")

        if suggested_market == "OVER" and score_hold_probability >= 75:
            risk_score += 18
            risk_reasons.append("OVER_AGAINST_SCORE_HOLD")

        if suggested_market == "OVER" and under_transition_score >= 75:
            risk_score += 15
            risk_reasons.append("OVER_AGAINST_UNDER_TRANSITION")

        if suggested_market == "OVER" and minute >= 80 and recent_attack_proxy < 50:
            risk_score += 16
            risk_reasons.append("LATE_OVER_WITHOUT_REACTIVATION")

        if suggested_market == "OVER" and offensive_depth_score < 45:
            risk_score += 14
            risk_reasons.append("OVER_WITHOUT_DEPTH")

        if conmebol_late:
            risk_score += 14
            risk_warnings.append("CONMEBOL_EXTRA_CONFIRMATION_REQUIRED")

            if suggested_market == "OVER":
                if tactical_score < 72 or offensive_depth_score < 65 or recent_attack_proxy < 60:
                    risk_score += 20
                    risk_reasons.append("CONMEBOL_OVER_NOT_CONFIRMED")

        if suggested_market == "UNDER" and tactical_score >= 78:
            risk_score += 12
            risk_warnings.append("UNDER_AGAINST_STRONG_TACTICAL_ACTIVITY")

        if suggested_market == "NO_BET":
            risk_score += 15
            risk_warnings.append("NO_MARKET_EDGE")

        # ------------------------------------------------------------------
        # 5) Conflicto con predicción de resultado / escenarios.
        # Consume campos si MatchPredictionAI los entrega dentro de context/market.
        # Es advertencia, no bloqueo.
        # ------------------------------------------------------------------
        prediction = first_dict(
            context.get("prediction"),
            context.get("match_prediction"),
            market.get("prediction"),
            market.get("match_prediction"),
            tactical.get("prediction"),
        )

        prediction_alignment = str(
            first_value(
                prediction.get("prediction_alignment"),
                prediction.get("market_alignment"),
                context.get("prediction_alignment"),
                market.get("prediction_alignment"),
                default="",
            )
        ).upper()

        predicted_market = str(
            first_value(
                prediction.get("predicted_market"),
                prediction.get("recommended_market"),
                prediction.get("market"),
                context.get("predicted_market"),
                default="",
            )
        ).upper()

        over_probability = safe_float(
            first_value(
                prediction.get("over_probability"),
                prediction.get("over_score"),
                context.get("over_probability"),
                market.get("over_probability"),
                default=0.0,
            )
        )
        under_probability = safe_float(
            first_value(
                prediction.get("under_probability"),
                prediction.get("under_score"),
                context.get("under_probability"),
                market.get("under_probability"),
                default=0.0,
            )
        )

        if suggested_market and predicted_market and predicted_market != "NO_BET":
            if suggested_market != predicted_market:
                risk_score += 10
                risk_warnings.append("PREDICTION_MARKET_CONFLICT")

        if prediction_alignment in {"CONFLICT", "WEAK_CONFLICT", "PARTIAL_CONFLICT"}:
            risk_score += 10
            risk_warnings.append("PREDICTION_ALIGNMENT_CONFLICT")

        if suggested_market == "OVER" and under_probability >= 70 and over_probability <= 45:
            risk_score += 10
            risk_warnings.append("OVER_UNDER_PERCENT_MISMATCH")

        if suggested_market == "UNDER" and over_probability >= 70 and under_probability <= 45:
            risk_score += 10
            risk_warnings.append("UNDER_OVER_PERCENT_MISMATCH")

        # ------------------------------------------------------------------
        # 6) Riesgo de ruptura / apertura.
        # La señal no se bloquea: se marca que el partido puede romperse.
        # ------------------------------------------------------------------
        break_risk = safe_float(
            first_value(
                prediction.get("break_risk"),
                context.get("break_risk"),
                tactical.get("break_risk"),
                pressure_quality.get("break_risk"),
                default=0.0,
            )
        )
        break_state = str(
            first_value(
                prediction.get("break_state"),
                context.get("break_state"),
                tactical.get("break_state"),
                default="",
            )
        ).upper()

        if break_risk >= 70 or break_state in {"HIGH", "BREAK_RISK", "RUPTURE_RISK", "OPEN_GAME_RISK"}:
            risk_score += 8
            risk_warnings.append("BREAK_RISK_WARNING")
            risk_tags.append("MATCH_CAN_BREAK")

        # UNDER con ruptura alta pierde seguridad, pero no se bloquea.
        if suggested_market == "UNDER" and (break_risk >= 60 or break_state in {"MEDIUM", "HIGH"}):
            risk_score += 8
            risk_warnings.append("UNDER_WITH_BREAK_RISK")

        # ------------------------------------------------------------------
        # 7) Normalización y salida compatible.
        # ------------------------------------------------------------------
        risk_score = max(0, min(100, risk_score))

        if hard_blockers:
            risk_status = "EXTREME_RISK"
            risk_action = "BLOCK"
        elif risk_score >= 75:
            risk_status = "HIGH_RISK"
            risk_action = "WAIT_CONFIRMATION"
        elif risk_score >= 55:
            risk_status = "MEDIUM_RISK"
            risk_action = "OBSERVE"
        elif risk_score >= 35:
            risk_status = "CONTROLLED_RISK"
            risk_action = "OPERABLE_WITH_CAUTION"
        else:
            risk_status = "LOW_RISK"
            risk_action = "RISK_ACCEPTABLE"

        return {
            "risk_status": risk_status,
            "risk_score": round(risk_score, 2),
            "risk_action": risk_action,
            "risk_reasons": list(dict.fromkeys(risk_reasons)),
            "risk_warnings": list(dict.fromkeys(risk_warnings)),
            "hard_blockers": list(dict.fromkeys(hard_blockers)),
            # Campos nuevos no intrusivos: no rompen consumidores existentes.
            "risk_tags": list(dict.fromkeys(risk_tags)),
            "low_data_league": low_data_league,
            "pressure_state": pressure_state,
            "game_state": game_state,
            "real_goal_threat": round(real_goal_threat, 2),
        }
