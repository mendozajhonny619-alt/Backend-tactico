from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.v17.core.constants import (
    MIN_CONFIDENCE_TO_ENTER,
    MIN_CONFIDENCE_TO_OBSERVE,
    MIN_CONFIDENCE_TO_OPERABLE,
)


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


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def upper(value: Any, default: str = "") -> str:
    try:
        text = str(value or default).strip().upper()
        return text or default
    except Exception:
        return default


class MasterDecisionAI:
    """
    Autoridad final de decisión V17.

    Filosofía:
    - No decide por estadística bruta.
    - Decide por lectura del partido, amenaza real, escenario probable y riesgo.
    - Puede interpretar alternativas como un analista profesional.
    - Mantiene autonomía controlada: interpreta escenarios, pero no rompe guardias críticos.

    Reglas de autoridad:
    - ClockGuard, DataQualityGuard, RiskAI crítico y ContradictionJudge crítico pueden bloquear.
    - PressureQualityAI y MatchPredictionAI alimentan la lectura profesional.
    - MasterDecisionAI decide ENTER, OPERABLE, WAIT_CONFIRMATION, NO_BET o BLOCKED.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        evidence = evidence or {}

        suggested_market = upper(
            market.get("suggested_market")
            or market.get("market")
            or "NO_BET"
        )

        prediction_evidence = evidence.get("prediction") or {}
        normalized_prediction = {
            **prediction_evidence,
            "predicted_score": (
                prediction_evidence.get("prediction_final_score")
                or prediction_evidence.get("prediction_score")
                or prediction_evidence.get("predicted_score")
            ),
            "alternative_score": (
                prediction_evidence.get("prediction_alternative_score")
                or prediction_evidence.get("alternative_score")
            ),
            "conservative_score": (
                prediction_evidence.get("prediction_conservative_score")
                or prediction_evidence.get("conservative_score")
            ),
            "next_goal_probability": (
                prediction_evidence.get("prediction_next_goal_probability")
                or prediction_evidence.get("next_goal_probability")
            ),
            "next_goal_team": (
                prediction_evidence.get("prediction_attacking_team")
                or prediction_evidence.get("next_goal_team")
            ),
            "main_scenario": (
                prediction_evidence.get("prediction_scenario")
                or prediction_evidence.get("main_scenario")
            ),
            "scenario_probabilities": prediction_evidence.get(
                "prediction_score_scenarios",
                prediction_evidence.get("scenario_probabilities", []),
            ),
            "opponent_break_risk": (
                prediction_evidence.get("break_risk")
                or prediction_evidence.get("opponent_break_risk")
            ),
        }
        match_with_prediction = {
            **match,
            "match_prediction": normalized_prediction,
        }

        pressure_quality = self._extract_pressure_quality(
            match=match,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
        )
        scenario_intelligence = self._analyze_scenario_intelligence(
            match=match_with_prediction,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            suggested_market=suggested_market,
            pressure_quality=pressure_quality,
        )

        hard_blockers: List[str] = []
        soft_warnings: List[str] = []

        if not data_quality.get("data_valid", False):
            hard_blockers.extend(data_quality.get("data_issues", []))

        if upper(clock.get("clock_status")) == "BLOCKED_CLOCK":
            hard_blockers.extend(clock.get("clock_blockers", []))

        if upper(risk.get("risk_status")) == "EXTREME_RISK":
            hard_blockers.extend(risk.get("hard_blockers", []))
            hard_blockers.append("EXTREME_RISK")

        if upper(contradiction.get("contradiction_status")) == "CRITICAL_CONTRADICTION":
            hard_blockers.extend(contradiction.get("critical_contradictions", []))
            hard_blockers.append("CRITICAL_CONTRADICTION")

        # Autonomía controlada: la IA puede interpretar, pero no saltarse guardias críticos.
        if scenario_intelligence["scenario_status"] == "CRITICAL_SCENARIO_BLOCK":
            hard_blockers.extend(scenario_intelligence.get("scenario_blockers", []))

        evidence_hard_blockers, evidence_soft_warnings = (
            self._extract_pre_master_evidence(evidence)
        )
        hard_blockers.extend(evidence_hard_blockers)

        if hard_blockers:
            return self._decision(
                status="BLOCKED",
                rank="BLOCKED",
                confidence=0.0,
                market=suggested_market,
                passed_filters=[],
                failed_secondary_filters=[],
                hard_blockers=sorted(set(hard_blockers)),
                soft_warnings=[],
                reason="Existe bloqueo crítico. La señal no puede entrar.",
                action="NO_OPERAR",
                pressure_quality=pressure_quality,
                scenario_intelligence=scenario_intelligence,
                match=match,
            )

        recovered_market = self._recover_market_if_possible(
            suggested_market=suggested_market,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            pressure_quality=pressure_quality,
            scenario_intelligence=scenario_intelligence,
        )
        suggested_market = recovered_market

        # Recalcula escenario si el mercado se recuperó o cambió.
        scenario_intelligence = self._analyze_scenario_intelligence(
            match=match_with_prediction,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            suggested_market=suggested_market,
            pressure_quality=pressure_quality,
        )

        if suggested_market not in {"OVER", "UNDER"}:
            market_confidence = safe_float(market.get("market_confidence"), 0.0)

            if market_confidence >= MIN_CONFIDENCE_TO_OBSERVE:
                return self._decision(
                    status="OBSERVE",
                    rank="OBSERVE",
                    confidence=market_confidence,
                    market="OBSERVE",
                    passed_filters=[],
                    failed_secondary_filters=[],
                    hard_blockers=[],
                    soft_warnings=["MARKET_OBSERVE"],
                    reason="El partido tiene lectura parcial, pero todavía no existe ventaja operable.",
                    action="OBSERVAR",
                    pressure_quality=pressure_quality,
                    scenario_intelligence=scenario_intelligence,
                    match=match,
                )

            return self._decision(
                status="NO_BET",
                rank="NO_BET",
                confidence=market_confidence,
                market="NO_BET",
                passed_filters=[],
                failed_secondary_filters=[],
                hard_blockers=[],
                soft_warnings=["NO_MARKET_EDGE"],
                reason="No existe ventaja clara para OVER ni UNDER.",
                action="NO_OPERAR",
                pressure_quality=pressure_quality,
                scenario_intelligence=scenario_intelligence,
                match=match,
            )

        filter_result = self._majority_filters(
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            suggested_market=suggested_market,
            pressure_quality=pressure_quality,
            scenario_intelligence=scenario_intelligence,
        )

        passed_filters = filter_result["passed_filters"]
        failed_secondary_filters = filter_result["failed_secondary_filters"]
        failed_primary_filters = filter_result["failed_primary_filters"]
        soft_warnings = list(filter_result["soft_warnings"])
        soft_warnings.extend(evidence_soft_warnings)
        soft_warnings = list(dict.fromkeys(soft_warnings))
        majority_score = filter_result["majority_score"]

        confidence = self._calculate_confidence(
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            majority_score=majority_score,
            suggested_market=suggested_market,
            pressure_quality=pressure_quality,
            scenario_intelligence=scenario_intelligence,
        )

        risk_status = upper(risk.get("risk_status"))
        contradiction_status = upper(contradiction.get("contradiction_status"))
        clock_status = upper(clock.get("clock_status"))
        scenario_status = scenario_intelligence["scenario_status"]

        if contradiction_status == "STRONG_CONTRADICTION":
            confidence -= 14
            soft_warnings.append("STRONG_CONTRADICTION_FORCES_WAIT_CONFIRMATION")

        if risk_status == "HIGH_RISK":
            confidence -= 10
            soft_warnings.append("HIGH_RISK_DEGRADES_ENTER")

        if clock_status == "CLOCK_WARNING":
            confidence -= 8
            soft_warnings.append("CLOCK_WARNING_DEGRADES_ENTER")

        if scenario_status == "SCENARIO_CONFLICT":
            confidence -= 12
            soft_warnings.append("RESULT_PROBABLE_CONTRADICTS_MARKET")
        elif scenario_status == "SCENARIO_PARTIAL":
            confidence -= 4
            soft_warnings.append("RESULT_PROBABLE_PARTIAL_ALIGNMENT")
        elif scenario_status == "SCENARIO_ALIGNED":
            confidence += 5
            soft_warnings.append("RESULT_PROBABLE_ALIGNED_WITH_MARKET")

        if pressure_quality["pressure_type"] in {"FALSE_PRESSURE", "DOMINANCE_WITHOUT_DEPTH", "LATERAL_PRESSURE"}:
            if suggested_market == "OVER":
                confidence -= 8
                soft_warnings.append("OVER_DEGRADED_BY_PRESSURE_QUALITY")
            elif suggested_market == "UNDER":
                confidence += 3
                soft_warnings.append("UNDER_SUPPORTED_BY_LOW_THREAT_PRESSURE")

        if pressure_quality["real_goal_threat"] >= 70:
            if suggested_market == "OVER":
                confidence += 6
                soft_warnings.append("OVER_SUPPORTED_BY_REAL_GOAL_THREAT")
            elif suggested_market == "UNDER":
                confidence -= 7
                soft_warnings.append("UNDER_DEGRADED_BY_REAL_GOAL_THREAT")

        if scenario_intelligence.get("opponent_break_risk", 0) >= 70:
            if suggested_market == "UNDER":
                confidence -= 6
                soft_warnings.append("UNDER_DEGRADED_BY_OPPONENT_BREAK_RISK")
            elif suggested_market == "OVER":
                confidence += 3
                soft_warnings.append("OVER_SUPPORTED_BY_TRANSITION_RISK")

        secondary_fail_count = len(failed_secondary_filters)
        primary_fail_count = len(failed_primary_filters)

        if secondary_fail_count <= 2 and primary_fail_count == 0:
            confidence += 4
            soft_warnings.append("MAJORITY_RECOVERY_ACTIVE")

        if secondary_fail_count >= 4:
            confidence -= 8
            soft_warnings.append("TOO_MANY_SECONDARY_FILTERS_FAILED")

        if suggested_market == "UNDER":
            confidence = self._apply_under_safety_adjustment(
                confidence=confidence,
                tactical=tactical,
                market=market,
                context=context,
                pressure_quality=pressure_quality,
                scenario_intelligence=scenario_intelligence,
                soft_warnings=soft_warnings,
            )

        if suggested_market == "OVER":
            confidence = self._apply_over_recovery_adjustment(
                confidence=confidence,
                tactical=tactical,
                market=market,
                context=context,
                pressure_quality=pressure_quality,
                scenario_intelligence=scenario_intelligence,
                soft_warnings=soft_warnings,
            )

        confidence = clamp(confidence)

        status, rank, action, reason = self._final_status(
            suggested_market=suggested_market,
            confidence=confidence,
            majority_score=majority_score,
            secondary_fail_count=secondary_fail_count,
            primary_fail_count=primary_fail_count,
            market=market,
            tactical=tactical,
            risk=risk,
            contradiction=contradiction,
            pressure_quality=pressure_quality,
            scenario_intelligence=scenario_intelligence,
        )

        status, rank, action, reason = self._apply_pre_master_evidence(
            status=status,
            rank=rank,
            action=action,
            reason=reason,
            evidence=evidence,
        )

        return self._decision(
            status=status,
            rank=rank,
            confidence=confidence,
            market=suggested_market,
            passed_filters=passed_filters,
            failed_secondary_filters=failed_secondary_filters,
            hard_blockers=[],
            soft_warnings=soft_warnings,
            reason=reason,
            action=action,
            pressure_quality=pressure_quality,
            scenario_intelligence=scenario_intelligence,
            match=match,
        )

    def _extract_pressure_quality(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
    ) -> Dict[str, Any]:
        sources = [tactical, context, market, risk, contradiction, match]
        pressure_payload = {}
        for source in sources:
            if isinstance(source.get("pressure_quality"), dict):
                pressure_payload.update(source.get("pressure_quality") or {})
            if isinstance(source.get("pressure_quality_ai"), dict):
                pressure_payload.update(source.get("pressure_quality_ai") or {})

        pressure_type = upper(
            pressure_payload.get("pressure_type")
            or pressure_payload.get("pressure_label")
            or tactical.get("pressure_type")
            or context.get("pressure_type")
            or "UNKNOWN"
        )

        real_goal_threat = safe_float(
            pressure_payload.get("real_goal_threat")
            or tactical.get("real_goal_threat")
            or context.get("real_goal_threat")
            or market.get("real_goal_threat"),
            0.0,
        )
        false_pressure_risk = safe_float(
            pressure_payload.get("false_pressure_risk")
            or tactical.get("false_pressure_risk")
            or context.get("false_pressure_risk"),
            0.0,
        )
        dominance_without_depth = safe_float(
            pressure_payload.get("dominance_without_depth")
            or tactical.get("dominance_without_depth")
            or context.get("dominance_without_depth"),
            0.0,
        )
        game_state = upper(
            pressure_payload.get("game_state")
            or tactical.get("game_state")
            or context.get("game_state")
            or "UNKNOWN"
        )
        dominant_team = str(
            pressure_payload.get("dominant_team")
            or tactical.get("dominant_team")
            or context.get("dominant_team")
            or "UNKNOWN"
        )

        if pressure_type == "UNKNOWN":
            if real_goal_threat >= 72:
                pressure_type = "HIGH_THREAT_PRESSURE"
            elif false_pressure_risk >= 72:
                pressure_type = "FALSE_PRESSURE"
            elif dominance_without_depth >= 68:
                pressure_type = "DOMINANCE_WITHOUT_DEPTH"
            elif real_goal_threat >= 55:
                pressure_type = "REAL_PRESSURE"
            else:
                pressure_type = "LOW_PRESSURE"

        return {
            "pressure_type": pressure_type,
            "real_goal_threat": round(clamp(real_goal_threat), 2),
            "false_pressure_risk": round(clamp(false_pressure_risk), 2),
            "dominance_without_depth": round(clamp(dominance_without_depth), 2),
            "game_state": game_state,
            "dominant_team": dominant_team,
        }

    def _analyze_scenario_intelligence(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        suggested_market: str,
        pressure_quality: Dict[str, Any],
    ) -> Dict[str, Any]:
        prediction = self._extract_prediction_payload(match, context, tactical, market, risk, contradiction)
        current_score = self._current_score(match)
        predicted_score = self._score_from_payload(prediction, preferred_keys=(
            "predicted_score", "prediction_final_score", "prediction_score",
            "result_probability_score", "probable_score", "most_likely_score", "ft_score",
        ))
        alternative_score = self._score_from_payload(prediction, preferred_keys=(
            "alternative_score", "prediction_alternative_score",
            "offensive_alternative", "main_alternative", "second_scenario",
        ))
        conservative_score = self._score_from_payload(prediction, preferred_keys=(
            "conservative_score", "score_hold_score", "hold_score", "defensive_scenario",
        ))

        scenario_probs = prediction.get("scenario_probabilities") or prediction.get("scenarios") or []
        total_goals_now = sum(current_score) if current_score else 0
        total_goals_predicted = sum(predicted_score) if predicted_score else total_goals_now
        total_goals_alternative = sum(alternative_score) if alternative_score else total_goals_predicted
        total_goals_conservative = sum(conservative_score) if conservative_score else total_goals_predicted

        next_goal_probability = safe_float(
            prediction.get("next_goal_probability")
            or prediction.get("goal_probability")
            or market.get("goal_probability")
            or market.get("over_score"),
            0.0,
        )
        score_hold_probability = safe_float(
            prediction.get("score_hold_probability")
            or context.get("score_hold_probability"),
            0.0,
        )
        opponent_break_risk = safe_float(
            prediction.get("opponent_break_risk")
            or prediction.get("transition_risk")
            or tactical.get("opponent_break_risk")
            or context.get("opponent_break_risk")
            or risk.get("opponent_break_risk"),
            0.0,
        )

        real_goal_threat = pressure_quality["real_goal_threat"]
        false_pressure_risk = pressure_quality["false_pressure_risk"]
        game_state = pressure_quality["game_state"]

        scenario_status = "SCENARIO_UNKNOWN"
        blockers: List[str] = []
        warnings: List[str] = []
        aligned_reasons: List[str] = []

        if suggested_market == "OVER":
            over_by_score = total_goals_predicted > total_goals_now or total_goals_alternative > total_goals_now
            over_by_threat = real_goal_threat >= 62 or next_goal_probability >= 64 or opponent_break_risk >= 68
            under_conservative = score_hold_probability >= 76 and total_goals_predicted <= total_goals_now

            if over_by_score and over_by_threat and not under_conservative:
                scenario_status = "SCENARIO_ALIGNED"
                aligned_reasons.append("FORECAST_EXPECTS_ADDITIONAL_GOAL")
            elif over_by_threat and total_goals_alternative > total_goals_now:
                scenario_status = "SCENARIO_PARTIAL"
                warnings.append("OVER_EXISTS_AS_ALTERNATIVE_SCENARIO")
            elif under_conservative or (false_pressure_risk >= 78 and real_goal_threat < 55):
                scenario_status = "SCENARIO_CONFLICT"
                warnings.append("OVER_CONFLICTS_WITH_SCORE_HOLD_OR_FALSE_PRESSURE")
            else:
                scenario_status = "SCENARIO_PARTIAL"
                warnings.append("OVER_REQUIRES_MORE_CONFIRMATION")

        elif suggested_market == "UNDER":
            under_by_score = total_goals_predicted <= total_goals_now or total_goals_conservative <= total_goals_now
            under_by_hold = score_hold_probability >= 66 or real_goal_threat <= 42
            break_risk = opponent_break_risk >= 70 or real_goal_threat >= 72 or next_goal_probability >= 70

            if under_by_score and under_by_hold and not break_risk:
                scenario_status = "SCENARIO_ALIGNED"
                aligned_reasons.append("FORECAST_SUPPORTS_SCORE_HOLD")
            elif break_risk:
                scenario_status = "SCENARIO_CONFLICT"
                warnings.append("UNDER_CONFLICTS_WITH_BREAK_OR_TRANSITION_RISK")
            else:
                scenario_status = "SCENARIO_PARTIAL"
                warnings.append("UNDER_REQUIRES_MORE_CONFIRMATION")
        else:
            scenario_status = "SCENARIO_UNKNOWN"

        if (
            upper(risk.get("risk_status")) == "EXTREME_RISK"
            or upper(contradiction.get("contradiction_status")) == "CRITICAL_CONTRADICTION"
        ):
            scenario_status = "CRITICAL_SCENARIO_BLOCK"
            blockers.append("SCENARIO_CRITICAL_RISK_OR_CONTRADICTION")

        # Lectura más allá de los próximos 10 minutos: el rival puede romper dominio o presión.
        if opponent_break_risk >= 68:
            warnings.append("OPPONENT_CAN_BREAK_DOMINANCE")

        main_scenario = (
            prediction.get("main_scenario")
            or prediction.get("prediction_scenario")
            or scenario_status
        )
        next_goal_team = (
            prediction.get("next_goal_team")
            or prediction.get("prediction_attacking_team")
        )

        return {
            "scenario_status": scenario_status,
            "main_scenario": main_scenario,
            "next_goal_team": next_goal_team,
            "current_score": self._format_score(current_score),
            "predicted_score": self._format_score(predicted_score),
            "alternative_score": self._format_score(alternative_score),
            "conservative_score": self._format_score(conservative_score),
            "next_goal_probability": round(clamp(next_goal_probability), 2),
            "score_hold_probability": round(clamp(score_hold_probability), 2),
            "opponent_break_risk": round(clamp(opponent_break_risk), 2),
            "scenario_probabilities": scenario_probs,
            "scenario_blockers": blockers,
            "scenario_warnings": warnings,
            "scenario_support": aligned_reasons,
            "game_state": game_state,
        }

    def _extract_prediction_payload(self, *sources: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        prediction_keys = (
            "prediction", "match_prediction", "forecast", "match_forecast",
            "prediction_ai", "match_prediction_ai", "result_prediction",
        )
        for source in sources:
            for key in prediction_keys:
                value = source.get(key) if isinstance(source, dict) else None
                if isinstance(value, dict):
                    payload.update(value)
            if isinstance(source, dict):
                for key in (
                    "predicted_score", "prediction_final_score", "prediction_score",
                    "probable_score", "alternative_score", "prediction_alternative_score",
                    "conservative_score", "score_hold_probability", "next_goal_probability",
                    "prediction_next_goal_probability", "goal_probability", "opponent_break_risk",
                    "prediction_attacking_team", "prediction_scenario", "main_scenario",
                ):
                    if key in source and key not in payload:
                        payload[key] = source[key]
        return payload

    def _current_score(self, match: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        for home_key, away_key in (("home_score", "away_score"), ("goals_home", "goals_away"), ("score_home", "score_away")):
            if home_key in match or away_key in match:
                return safe_int(match.get(home_key), 0), safe_int(match.get(away_key), 0)
        score = match.get("score") or match.get("current_score")
        return self._parse_score(score)

    def _score_from_payload(self, payload: Dict[str, Any], preferred_keys: Tuple[str, ...]) -> Optional[Tuple[int, int]]:
        for key in preferred_keys:
            if key in payload:
                parsed = self._parse_score(payload.get(key))
                if parsed is not None:
                    return parsed
        return None

    def _parse_score(self, value: Any) -> Optional[Tuple[int, int]]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return safe_int(value[0]), safe_int(value[1])
        if isinstance(value, dict):
            return safe_int(value.get("home") or value.get("home_score")), safe_int(value.get("away") or value.get("away_score"))
        text = str(value).strip()
        for sep in ("-", ":", "–"):
            if sep in text:
                parts = text.replace(" ", "").split(sep)
                if len(parts) >= 2:
                    return safe_int(parts[0]), safe_int(parts[1])
        return None

    def _format_score(self, score: Optional[Tuple[int, int]]) -> Optional[str]:
        if score is None:
            return None
        return f"{score[0]}-{score[1]}"

    def _recover_market_if_possible(
        self,
        suggested_market: str,
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
    ) -> str:
        if suggested_market in {"OVER", "UNDER"}:
            return suggested_market

        risk_status = upper(risk.get("risk_status"))
        contradiction_status = upper(contradiction.get("contradiction_status"))

        if risk_status in {"EXTREME_RISK", "HIGH_RISK"}:
            return suggested_market

        if contradiction_status in {"CRITICAL_CONTRADICTION", "STRONG_CONTRADICTION"}:
            return suggested_market

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        market_gap = safe_float(market.get("market_gap"), abs(over_score - under_score))

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = max(
            safe_float(tactical.get("false_pressure_risk"), 0.0),
            pressure_quality["false_pressure_risk"],
        )
        real_goal_threat = pressure_quality["real_goal_threat"]
        scenario_status = scenario_intelligence["scenario_status"]

        if (
            over_score >= 64
            and over_score >= under_score + 6
            and tactical_score >= 56
            and offensive_depth_score >= 48
            and offensive_volume_score >= 45
            and recent_attack_proxy >= 35
            and real_goal_threat >= 55
            and false_pressure_risk < 72
            and scenario_status != "SCENARIO_CONFLICT"
        ):
            return "OVER"

        if (
            under_score >= 74
            and under_score >= over_score + 10
            and market_gap >= 10
            and score_hold_probability >= 68
            and under_transition_score >= 62
            and tactical_score < 72
            and offensive_volume_score <= 55
            and false_pressure_risk < 70
            and real_goal_threat < 62
            and scenario_status != "SCENARIO_CONFLICT"
        ):
            return "UNDER"

        return suggested_market

    def _majority_filters(
        self,
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        suggested_market: str,
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        checks.append({"name": "CLOCK_CONFIRMED", "passed": bool(clock.get("clock_can_enter")), "weight": 15, "secondary": False})
        checks.append({"name": "DATA_VALID", "passed": bool(data_quality.get("data_valid")), "weight": 12, "secondary": False})
        checks.append({"name": "MARKET_EDGE", "passed": safe_float(market.get("market_confidence"), 0.0) >= 55, "weight": 12, "secondary": False})
        checks.append({"name": "TACTICAL_SCORE", "passed": safe_float(tactical.get("tactical_score"), 0.0) >= 45, "weight": 10, "secondary": False})
        checks.append({"name": "RISK_ACCEPTABLE", "passed": upper(risk.get("risk_status")) in {"LOW_RISK", "CONTROLLED_RISK", "MEDIUM_RISK"}, "weight": 13, "secondary": False})
        checks.append({"name": "NO_CRITICAL_CONTRADICTION", "passed": upper(contradiction.get("contradiction_status")) not in {"CRITICAL_CONTRADICTION", "STRONG_CONTRADICTION"}, "weight": 12, "secondary": False})
        checks.append({"name": "SCENARIO_NOT_CONTRARY", "passed": scenario_intelligence["scenario_status"] != "SCENARIO_CONFLICT", "weight": 10, "secondary": False})

        if suggested_market == "OVER":
            checks.extend([
                {"name": "REAL_GOAL_THREAT", "passed": pressure_quality["real_goal_threat"] >= 55, "weight": 9, "secondary": False},
                {"name": "OFFENSIVE_DEPTH", "passed": safe_float(tactical.get("offensive_depth_score"), 0.0) >= 45, "weight": 8, "secondary": True},
                {"name": "OFFENSIVE_VOLUME", "passed": safe_float(tactical.get("offensive_volume_score"), 0.0) >= 42, "weight": 8, "secondary": True},
                {"name": "FALSE_PRESSURE_CONTROLLED", "passed": pressure_quality["false_pressure_risk"] < 75, "weight": 7, "secondary": True},
                {"name": "SCORE_HOLD_NOT_CRITICAL", "passed": safe_float(context.get("score_hold_probability"), 0.0) < 84, "weight": 5, "secondary": True},
                {"name": "RECENT_ATTACK_ACTIVITY", "passed": safe_float(tactical.get("recent_attack_proxy"), 0.0) >= 35, "weight": 5, "secondary": True},
            ])

            if context.get("conmebol_late"):
                checks.append({
                    "name": "CONMEBOL_EXTRA_CONFIRMATION",
                    "passed": (
                        safe_float(tactical.get("tactical_score"), 0.0) >= 68
                        and safe_float(tactical.get("offensive_depth_score"), 0.0) >= 58
                        and safe_float(tactical.get("recent_attack_proxy"), 0.0) >= 45
                        and pressure_quality["real_goal_threat"] >= 62
                    ),
                    "weight": 10,
                    "secondary": False,
                })

        if suggested_market == "UNDER":
            checks.extend([
                {"name": "SCORE_HOLD_SUPPORT", "passed": safe_float(context.get("score_hold_probability"), 0.0) >= 62, "weight": 9, "secondary": True},
                {"name": "UNDER_TRANSITION_SUPPORT", "passed": safe_float(context.get("under_transition_score"), 0.0) >= 58, "weight": 8, "secondary": True},
                {"name": "LOW_REAL_GOAL_THREAT", "passed": pressure_quality["real_goal_threat"] < 60, "weight": 8, "secondary": False},
                {"name": "LOW_BREAK_RISK", "passed": scenario_intelligence.get("opponent_break_risk", 0) < 68, "weight": 7, "secondary": False},
                {"name": "LOW_OFFENSIVE_VOLUME", "passed": safe_float(tactical.get("offensive_volume_score"), 0.0) <= 58, "weight": 8, "secondary": True},
                {"name": "LOW_FALSE_UNDER_RISK", "passed": safe_float(tactical.get("tactical_score"), 0.0) < 82, "weight": 6, "secondary": True},
                {"name": "PRESSURE_NOT_TOO_HIGH", "passed": safe_float(context.get("pressure_score"), 0.0) < 78, "weight": 5, "secondary": True},
            ])

        total_weight = sum(x["weight"] for x in checks)
        passed_weight = sum(x["weight"] for x in checks if x["passed"])

        passed_filters = [x["name"] for x in checks if x["passed"]]
        failed_secondary_filters = [x["name"] for x in checks if not x["passed"] and x.get("secondary")]
        failed_primary_filters = [x["name"] for x in checks if not x["passed"] and not x.get("secondary")]

        majority_score = (passed_weight / max(1, total_weight)) * 100

        soft_warnings: List[str] = []
        for item in failed_secondary_filters:
            soft_warnings.append(f"FALTA_FILTRO_SECUNDARIO:{item}")
        for item in failed_primary_filters:
            soft_warnings.append(f"FALTA_FILTRO_PRINCIPAL:{item}")
        for item in scenario_intelligence.get("scenario_warnings", []):
            soft_warnings.append(f"SCENARIO_WARNING:{item}")

        return {
            "majority_score": round(majority_score, 2),
            "passed_filters": passed_filters,
            "failed_secondary_filters": failed_secondary_filters,
            "failed_primary_filters": failed_primary_filters,
            "soft_warnings": soft_warnings,
        }

    def _calculate_confidence(
        self,
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        majority_score: float,
        suggested_market: str,
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
    ) -> float:
        market_confidence = safe_float(market.get("market_confidence"), 0.0)
        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        risk_score = safe_float(risk.get("risk_score"), 0.0)
        contradiction_score = safe_float(contradiction.get("contradiction_score"), 0.0)
        real_goal_threat = pressure_quality["real_goal_threat"]
        false_pressure_risk = pressure_quality["false_pressure_risk"]
        scenario_alignment_score = {
            "SCENARIO_ALIGNED": 78,
            "SCENARIO_PARTIAL": 55,
            "SCENARIO_UNKNOWN": 50,
            "SCENARIO_CONFLICT": 25,
        }.get(scenario_intelligence["scenario_status"], 50)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        confidence = (
            market_confidence * 0.20
            + tactical_score * 0.15
            + offensive_volume_score * 0.06
            + pressure_score * 0.05
            + real_goal_threat * 0.12
            + max(0, 100 - false_pressure_risk) * 0.07
            + scenario_alignment_score * 0.11
            + majority_score * 0.20
            + max(0, 100 - risk_score) * 0.09
            + max(0, 100 - contradiction_score) * 0.05
        )

        if suggested_market == "UNDER":
            confidence += under_score * 0.04
            confidence += score_hold_probability * 0.04
            confidence += under_transition_score * 0.03
            confidence -= real_goal_threat * 0.04

        if suggested_market == "OVER":
            confidence += over_score * 0.06
            confidence += real_goal_threat * 0.05
            confidence += scenario_intelligence.get("opponent_break_risk", 0) * 0.02

        return clamp(confidence)

    def _apply_under_safety_adjustment(
        self,
        confidence: float,
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        context: Dict[str, Any],
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
        soft_warnings: List[str],
    ) -> float:
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        real_goal_threat = pressure_quality["real_goal_threat"]
        opponent_break_risk = scenario_intelligence.get("opponent_break_risk", 0)

        if offensive_volume_score >= 60:
            confidence -= 10
            soft_warnings.append("UNDER_DEGRADED_BY_OFFENSIVE_VOLUME")
        if tactical_score >= 75:
            confidence -= 8
            soft_warnings.append("UNDER_DEGRADED_BY_TACTICAL_ACTIVITY")
        if pressure_score >= 78:
            confidence -= 6
            soft_warnings.append("UNDER_DEGRADED_BY_HIGH_PRESSURE")
        if real_goal_threat >= 62:
            confidence -= 10
            soft_warnings.append("UNDER_DEGRADED_BY_REAL_GOAL_THREAT")
        if opponent_break_risk >= 68:
            confidence -= 7
            soft_warnings.append("UNDER_DEGRADED_BY_OPPONENT_BREAK_RISK")
        if scenario_intelligence["scenario_status"] == "SCENARIO_CONFLICT":
            confidence -= 10
            soft_warnings.append("UNDER_DEGRADED_BY_SCENARIO_CONFLICT")
        if over_score >= under_score - 6:
            confidence -= 5
            soft_warnings.append("UNDER_EDGE_NOT_WIDE_ENOUGH")

        return confidence

    def _apply_over_recovery_adjustment(
        self,
        confidence: float,
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        context: Dict[str, Any],
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
        soft_warnings: List[str],
    ) -> float:
        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = pressure_quality["false_pressure_risk"]
        real_goal_threat = pressure_quality["real_goal_threat"]
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)
        opponent_break_risk = scenario_intelligence.get("opponent_break_risk", 0)

        if (
            over_score >= 75
            and over_score >= under_score + 12
            and offensive_volume_score >= 55
            and offensive_depth_score >= 55
            and real_goal_threat >= 65
            and false_pressure_risk < 65
            and scenario_intelligence["scenario_status"] != "SCENARIO_CONFLICT"
        ):
            confidence += 8
            soft_warnings.append("OVER_STRONG_RECOVERY_BONUS")
        elif (
            over_score >= 68
            and over_score >= under_score + 8
            and offensive_volume_score >= 48
            and recent_attack_proxy >= 35
            and real_goal_threat >= 55
            and false_pressure_risk < 72
        ):
            confidence += 5
            soft_warnings.append("OVER_MODERATE_RECOVERY_BONUS")

        if goal_need_score >= 70 and offensive_volume_score >= 45:
            confidence += 3
            soft_warnings.append("OVER_GOAL_NEED_BONUS")
        if opponent_break_risk >= 68:
            confidence += 3
            soft_warnings.append("OVER_ALTERNATIVE_BREAK_SCENARIO_BONUS")
        if scenario_intelligence["scenario_status"] == "SCENARIO_CONFLICT":
            confidence -= 9
            soft_warnings.append("OVER_DEGRADED_BY_SCENARIO_CONFLICT")

        return confidence

    def _final_status(
        self,
        suggested_market: str,
        confidence: float,
        majority_score: float,
        secondary_fail_count: int,
        primary_fail_count: int,
        market: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        pressure_quality: Dict[str, Any],
        scenario_intelligence: Dict[str, Any],
    ) -> tuple[str, str, str, str]:
        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        false_pressure_risk = pressure_quality["false_pressure_risk"]
        real_goal_threat = pressure_quality["real_goal_threat"]
        scenario_status = scenario_intelligence["scenario_status"]

        risk_status = upper(risk.get("risk_status"))
        contradiction_status = upper(contradiction.get("contradiction_status"))

        if primary_fail_count >= 2:
            return "WAIT_CONFIRMATION", "OBSERVE", "ESPERAR_CONFIRMACION", "Faltan filtros principales. La señal queda en observación."

        if contradiction_status == "STRONG_CONTRADICTION":
            return "WAIT_CONFIRMATION", "OBSERVE", "ESPERAR_CONFIRMACION", "Existe contradicción fuerte entre módulos V17. La señal requiere confirmación antes de operar."

        if scenario_status == "SCENARIO_CONFLICT":
            return "WAIT_CONFIRMATION", "OBSERVE", "ESPERAR_CONFIRMACION", "El resultado probable o la alternativa principal contradicen el mercado sugerido. Se requiere confirmación."

        if risk_status == "HIGH_RISK":
            if (
                confidence >= MIN_CONFIDENCE_TO_OPERABLE + 5
                and majority_score >= 72
                and primary_fail_count == 0
                and secondary_fail_count <= 2
                and scenario_status in {"SCENARIO_ALIGNED", "SCENARIO_PARTIAL"}
            ):
                return "OPERABLE", "OPERABLE", "OPERAR_CON_CAUTELA", "La señal es operable con cautela: riesgo alto, pero mayoría de filtros y escenario alineados."
            return "WAIT_CONFIRMATION", "OBSERVE", "ESPERAR_CONFIRMACION", "Riesgo alto. Se requiere confirmación adicional antes de operar."

        if suggested_market == "OVER":
            if (
                confidence >= MIN_CONFIDENCE_TO_ENTER
                and majority_score >= 76
                and over_score >= under_score + 10
                and offensive_volume_score >= 52
                and real_goal_threat >= 62
                and false_pressure_risk < 65
                and scenario_status == "SCENARIO_ALIGNED"
            ):
                return "ENTER", "PREMIUM" if confidence >= 86 else "FUERTE", "OPERAR", "OVER fuerte: amenaza real, escenario probable alineado y mayoría de filtros confirmada."

            if (
                confidence >= MIN_CONFIDENCE_TO_OPERABLE
                and majority_score >= 60
                and secondary_fail_count <= 3
                and offensive_volume_score >= 42
                and real_goal_threat >= 52
                and false_pressure_risk < 75
                and scenario_status in {"SCENARIO_ALIGNED", "SCENARIO_PARTIAL"}
            ):
                return "OPERABLE", "BUENA" if confidence >= 72 else "OPERABLE", "OPERAR_CON_CAUTELA", "OVER operable por mayoría flexible V17. Hay amenaza suficiente y escenario no contrario."

        if suggested_market == "UNDER":
            if (
                confidence >= MIN_CONFIDENCE_TO_ENTER
                and majority_score >= 82
                and under_score >= over_score + 14
                and offensive_volume_score <= 48
                and real_goal_threat < 52
                and scenario_status == "SCENARIO_ALIGNED"
            ):
                return "ENTER", "PREMIUM" if confidence >= 88 else "FUERTE", "OPERAR", "UNDER fuerte: baja amenaza real, escenario de marcador sostenido y mayoría de filtros alineada."

            if (
                confidence >= MIN_CONFIDENCE_TO_OPERABLE
                and majority_score >= 68
                and secondary_fail_count <= 2
                and under_score >= over_score + 9
                and offensive_volume_score <= 58
                and real_goal_threat < 60
                and scenario_status in {"SCENARIO_ALIGNED", "SCENARIO_PARTIAL"}
            ):
                return "OPERABLE", "BUENA" if confidence >= 74 else "OPERABLE", "OPERAR_CON_CAUTELA", "UNDER operable con lectura conservadora, amenaza controlada y riesgo aceptable."

        if confidence >= 60 and majority_score >= 58 and secondary_fail_count <= 2 and primary_fail_count == 0:
            return "OPERABLE", "OPERABLE", "OPERAR_CON_CAUTELA", "La señal pasa por mayoría flexible V17. No hay bloqueo crítico y el escenario no la contradice."

        if confidence >= MIN_CONFIDENCE_TO_OBSERVE:
            return "WAIT_CONFIRMATION", "OBSERVE", "ESPERAR_CONFIRMACION", "Existe lectura parcial, pero faltan confirmaciones para operar."

        return "NO_BET", "NO_BET", "NO_OPERAR", "La lectura no alcanza mayoría suficiente para señal operable."


    def _extract_pre_master_evidence(
        self,
        evidence: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        promotion = evidence.get("promotion") or {}
        activation = evidence.get("activation") or {}
        maturity = evidence.get("maturity") or {}
        lifecycle = evidence.get("lifecycle") or {}

        hard_blockers: List[str] = []
        soft_warnings: List[str] = []

        hard_blockers.extend(promotion.get("promotion_blockers") or [])
        hard_blockers.extend(activation.get("activation_blockers") or [])

        if activation.get("activation_should_block"):
            hard_blockers.append("ACTIVATION_CRITICAL_BLOCK")

        if maturity.get("match_maturity_entry_permission") == "BLOCK_ENTRY":
            hard_blockers.append("MATCH_MATURITY_BLOCK")

        if lifecycle.get("no_reentry") or lifecycle.get("signal_expired"):
            hard_blockers.append("SIGNAL_LIFECYCLE_NO_REENTRY")

        soft_warnings.extend(promotion.get("promotion_warnings") or [])
        soft_warnings.extend(activation.get("activation_warnings") or [])
        soft_warnings.extend(maturity.get("match_maturity_warnings") or [])

        if lifecycle.get("lifecycle_requires_wait"):
            soft_warnings.append("SIGNAL_LIFECYCLE_REQUIRES_WAIT")

        return (
            list(dict.fromkeys(str(x) for x in hard_blockers if x)),
            list(dict.fromkeys(str(x) for x in soft_warnings if x)),
        )

    def _apply_pre_master_evidence(
        self,
        status: str,
        rank: str,
        action: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Tuple[str, str, str, str]:
        promotion = evidence.get("promotion") or {}
        activation = evidence.get("activation") or {}
        maturity = evidence.get("maturity") or {}
        lifecycle = evidence.get("lifecycle") or {}

        maturity_permission = upper(
            maturity.get("match_maturity_entry_permission")
        )
        promotion_level = upper(promotion.get("promotion_level"))
        activation_level = upper(activation.get("activation_level"))

        requires_wait = (
            bool(lifecycle.get("lifecycle_requires_wait"))
            or maturity_permission in {
                "WAIT_REVALIDATION",
                "PANORAMA_ONLY",
            }
            or promotion_level in {
                "WAIT_REVALIDATION",
                "STRONG_CANDIDATE",
                "EARLY_OVER_CANDIDATE",
                "OBSERVE_ONLY",
            }
            or activation_level in {
                "RISKY_CANDIDATE",
                "HIGH_OBSERVATION",
                "STRONG_CANDIDATE",
                "EARLY_OVER_CANDIDATE",
                "OBSERVATION",
            }
        )

        if status in {"ENTER", "OPERABLE"} and requires_wait:
            return (
                "WAIT_CONFIRMATION",
                "OBSERVE",
                "ESPERAR_CONFIRMACION",
                "La decisión maestra mantiene la lectura, pero la evidencia "
                "previa exige revalidación antes de publicar.",
            )

        return status, rank, action, reason

    def _decision(
        self,
        status: str,
        rank: str,
        confidence: float,
        market: str,
        passed_filters: List[str],
        failed_secondary_filters: List[str],
        hard_blockers: List[str],
        soft_warnings: List[str],
        reason: str,
        action: str,
        pressure_quality: Optional[Dict[str, Any]] = None,
        scenario_intelligence: Optional[Dict[str, Any]] = None,
        match: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scenario = scenario_intelligence or {}
        match_context = match or {}
        rounded_confidence = round(confidence, 2)
        can_publish = status in {"ENTER", "OPERABLE"}
        official_risks = list(
            dict.fromkeys(
                str(item)
                for item in [*hard_blockers, *soft_warnings]
                if item is not None and str(item).strip()
            )
        )
        official_main_scenario = scenario.get("main_scenario") or scenario.get("scenario_status")
        official_probable_score = scenario.get("predicted_score")
        official_next_goal_team = scenario.get("next_goal_team")
        decision_timestamp = datetime.now(timezone.utc).isoformat()

        match_id = str(
            match_context.get("match_id")
            or match_context.get("fixture_id")
            or match_context.get("id")
            or "UNKNOWN"
        )
        minute = safe_int(
            match_context.get("api_minute")
            or match_context.get("display_minute")
            or match_context.get("minute"),
            0,
        )
        decision_fingerprint = {
            "match_id": match_id,
            "minute": minute,
            "scoreline": match_context.get("scoreline") or match_context.get("current_score"),
            "market": market,
            "status": status,
            "confidence": rounded_confidence,
            "scenario": official_main_scenario,
            "probable_score": official_probable_score,
            "next_goal_team": official_next_goal_team,
            "can_publish": can_publish,
            "reason": reason,
            "risks": official_risks,
        }
        digest = hashlib.sha256(
            json.dumps(decision_fingerprint, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        decision_id = f"V17:{match_id}:{minute}:{digest}"

        return {
            # Contrato oficial V17. Estos campos son la frontera de autoridad
            # y no deben ser modificados por módulos posteriores.
            "official_market": market,
            "official_status": status,
            "official_confidence": rounded_confidence,
            "official_main_scenario": official_main_scenario,
            "official_probable_score": official_probable_score,
            "official_next_goal_team": official_next_goal_team,
            "official_can_publish": can_publish,
            "official_reason": reason,
            "official_risks": official_risks,
            "decision_id": decision_id,
            "decision_timestamp": decision_timestamp,

            # Alias existentes para compatibilidad durante la migración.
            "master_status": status,
            "master_rank": rank,
            "master_confidence": rounded_confidence,
            "master_market": market,
            "market": market,
            "market_direction": market if market in {"OVER", "UNDER"} else "OTHER",
            "master_action": action,
            "master_reason": reason,
            "passed_filters": passed_filters,
            "failed_secondary_filters": failed_secondary_filters,
            "hard_blockers": hard_blockers,
            "soft_warnings": soft_warnings,
            "pressure_quality_used": pressure_quality or {},
            "scenario_intelligence": scenario,
            "scenario_status": scenario.get("scenario_status"),
            "predicted_score": scenario.get("predicted_score"),
            "alternative_score": scenario.get("alternative_score"),
            "opponent_break_risk": scenario.get("opponent_break_risk"),
            "can_publish": can_publish,
            "should_observe": status in {"OBSERVE", "WAIT_CONFIRMATION"},
            "should_block": status in {"BLOCKED", "NO_BET"},
        }
