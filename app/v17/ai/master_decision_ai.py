from __future__ import annotations

from typing import Any, Dict, List

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


class MasterDecisionAI:
    """
    Autoridad final de la capa IA.

    Regla flexible:
    - Si cumple mayoría de filtros importantes, puede pasar como BUENA u OPERABLE.
    - Si falla uno o dos filtros secundarios, no se bloquea automáticamente.
    - Si falla bloqueo crítico, no entra.
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
    ) -> Dict[str, Any]:
        suggested_market = str(market.get("suggested_market") or "NO_BET").upper()

        hard_blockers: List[str] = []
        soft_warnings: List[str] = []
        passed_filters: List[str] = []
        failed_secondary_filters: List[str] = []

        if not data_quality.get("data_valid", False):
            hard_blockers.extend(data_quality.get("data_issues", []))

        if clock.get("clock_status") == "BLOCKED_CLOCK":
            hard_blockers.extend(clock.get("clock_blockers", []))

        if risk.get("risk_status") == "EXTREME_RISK":
            hard_blockers.extend(risk.get("hard_blockers", []))
            hard_blockers.append("EXTREME_RISK")

        if contradiction.get("contradiction_status") == "CRITICAL_CONTRADICTION":
            hard_blockers.extend(contradiction.get("critical_contradictions", []))
            hard_blockers.append("CRITICAL_CONTRADICTION")

        if suggested_market not in {"OVER", "UNDER"}:
            if suggested_market == "OBSERVE":
                return self._decision(
                    status="OBSERVE",
                    rank="OBSERVE",
                    confidence=safe_float(market.get("market_confidence"), 0.0),
                    market=suggested_market,
                    passed_filters=[],
                    failed_secondary_filters=[],
                    hard_blockers=[],
                    soft_warnings=["MARKET_OBSERVE"],
                    reason="El partido tiene lectura parcial, pero todavía no existe ventaja operable.",
                    action="OBSERVAR",
                )

            return self._decision(
                status="NO_BET",
                rank="NO_BET",
                confidence=safe_float(market.get("market_confidence"), 0.0),
                market=suggested_market,
                passed_filters=[],
                failed_secondary_filters=[],
                hard_blockers=[],
                soft_warnings=["NO_MARKET_EDGE"],
                reason="No existe ventaja clara para OVER ni UNDER.",
                action="NO_OPERAR",
            )

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
                reason="Existe al menos un bloqueo crítico. La señal no puede entrar.",
                action="NO_OPERAR",
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
        )

        passed_filters = filter_result["passed_filters"]
        failed_secondary_filters = filter_result["failed_secondary_filters"]
        soft_warnings = filter_result["soft_warnings"]

        majority_score = filter_result["majority_score"]
        confidence = self._calculate_confidence(
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            majority_score=majority_score,
        )

        if contradiction.get("contradiction_status") == "STRONG_CONTRADICTION":
            confidence -= 8
            soft_warnings.append("STRONG_CONTRADICTION_DEGRADES_ENTER")

        if risk.get("risk_status") == "HIGH_RISK":
            confidence -= 10
            soft_warnings.append("HIGH_RISK_DEGRADES_ENTER")

        if clock.get("clock_status") == "CLOCK_WARNING":
            confidence -= 8
            soft_warnings.append("CLOCK_WARNING_DEGRADES_ENTER")

        confidence = max(0, min(100, confidence))

        if confidence >= MIN_CONFIDENCE_TO_ENTER and majority_score >= 78:
            status = "ENTER"
            rank = "PREMIUM" if confidence >= 86 and majority_score >= 86 else "FUERTE"
            action = "OPERAR"
            reason = "La mayoría de filtros críticos y contextuales están alineados."
        elif confidence >= MIN_CONFIDENCE_TO_OPERABLE and majority_score >= 68:
            status = "OPERABLE"
            rank = "BUENA" if confidence >= 72 else "OPERABLE"
            action = "OPERAR_CON_CAUTELA"
            reason = "La señal cumple la mayoría de filtros. Puede pasar aunque falten uno o dos filtros secundarios."
        elif confidence >= MIN_CONFIDENCE_TO_OBSERVE:
            status = "WAIT_CONFIRMATION"
            rank = "OBSERVE"
            action = "ESPERAR_CONFIRMACION"
            reason = "Existe lectura parcial, pero faltan confirmaciones para operar."
        else:
            status = "NO_BET"
            rank = "NO_BET"
            action = "NO_OPERAR"
            reason = "La lectura no alcanza mayoría suficiente para señal operable."

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
        )

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
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        checks.append({
            "name": "CLOCK_CONFIRMED",
            "passed": bool(clock.get("clock_can_enter")),
            "weight": 15,
            "secondary": False,
        })

        checks.append({
            "name": "DATA_VALID",
            "passed": bool(data_quality.get("data_valid")),
            "weight": 12,
            "secondary": False,
        })

        checks.append({
            "name": "MARKET_EDGE",
            "passed": safe_float(market.get("market_confidence"), 0.0) >= 65,
            "weight": 13,
            "secondary": False,
        })

        checks.append({
            "name": "TACTICAL_SCORE",
            "passed": safe_float(tactical.get("tactical_score"), 0.0) >= 60,
            "weight": 12,
            "secondary": False,
        })

        checks.append({
            "name": "RISK_ACCEPTABLE",
            "passed": str(risk.get("risk_status")) in {"LOW_RISK", "CONTROLLED_RISK", "MEDIUM_RISK"},
            "weight": 13,
            "secondary": False,
        })

        checks.append({
            "name": "NO_STRONG_CONTRADICTION",
            "passed": str(contradiction.get("contradiction_status")) not in {
                "CRITICAL_CONTRADICTION",
                "STRONG_CONTRADICTION",
            },
            "weight": 12,
            "secondary": False,
        })

        if suggested_market == "OVER":
            checks.extend([
                {
                    "name": "OFFENSIVE_DEPTH",
                    "passed": safe_float(tactical.get("offensive_depth_score"), 0.0) >= 55,
                    "weight": 8,
                    "secondary": True,
                },
                {
                    "name": "FALSE_PRESSURE_CONTROLLED",
                    "passed": safe_float(tactical.get("false_pressure_risk"), 0.0) < 70,
                    "weight": 6,
                    "secondary": True,
                },
                {
                    "name": "SCORE_HOLD_NOT_CRITICAL",
                    "passed": safe_float(context.get("score_hold_probability"), 0.0) < 80,
                    "weight": 5,
                    "secondary": True,
                },
                {
                    "name": "RECENT_ATTACK_ACTIVITY",
                    "passed": safe_float(tactical.get("recent_attack_proxy"), 0.0) >= 45,
                    "weight": 4,
                    "secondary": True,
                },
            ])

            if context.get("conmebol_late"):
                checks.append({
                    "name": "CONMEBOL_EXTRA_CONFIRMATION",
                    "passed": (
                        safe_float(tactical.get("tactical_score"), 0.0) >= 72
                        and safe_float(tactical.get("offensive_depth_score"), 0.0) >= 65
                        and safe_float(tactical.get("recent_attack_proxy"), 0.0) >= 55
                    ),
                    "weight": 10,
                    "secondary": False,
                })

        if suggested_market == "UNDER":
            checks.extend([
                {
                    "name": "SCORE_HOLD_SUPPORT",
                    "passed": safe_float(context.get("score_hold_probability"), 0.0) >= 60,
                    "weight": 8,
                    "secondary": True,
                },
                {
                    "name": "UNDER_TRANSITION_SUPPORT",
                    "passed": safe_float(context.get("under_transition_score"), 0.0) >= 58,
                    "weight": 7,
                    "secondary": True,
                },
                {
                    "name": "LOW_FALSE_UNDER_RISK",
                    "passed": safe_float(tactical.get("tactical_score"), 0.0) < 82,
                    "weight": 6,
                    "secondary": True,
                },
            ])

        total_weight = sum(x["weight"] for x in checks)
        passed_weight = sum(x["weight"] for x in checks if x["passed"])

        passed_filters = [x["name"] for x in checks if x["passed"]]
        failed_secondary_filters = [
            x["name"] for x in checks if not x["passed"] and x.get("secondary")
        ]
        failed_primary_filters = [
            x["name"] for x in checks if not x["passed"] and not x.get("secondary")
        ]

        majority_score = (passed_weight / max(1, total_weight)) * 100

        soft_warnings: List[str] = []

        for item in failed_secondary_filters:
            soft_warnings.append(f"FALTA_FILTRO_SECUNDARIO:{item}")

        for item in failed_primary_filters:
            soft_warnings.append(f"FALTA_FILTRO_PRINCIPAL:{item}")

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
    ) -> float:
        market_confidence = safe_float(market.get("market_confidence"), 0.0)
        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        risk_score = safe_float(risk.get("risk_score"), 0.0)
        contradiction_score = safe_float(contradiction.get("contradiction_score"), 0.0)

        confidence = (
            market_confidence * 0.28
            + tactical_score * 0.25
            + pressure_score * 0.15
            + majority_score * 0.22
            + max(0, 100 - risk_score) * 0.07
            + max(0, 100 - contradiction_score) * 0.03
        )

        return max(0, min(100, confidence))

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
    ) -> Dict[str, Any]:
        return {
            "master_status": status,
            "master_rank": rank,
            "master_confidence": round(confidence, 2),
            "master_market": market,
            "master_action": action,
            "master_reason": reason,
            "passed_filters": passed_filters,
            "failed_secondary_filters": failed_secondary_filters,
            "hard_blockers": hard_blockers,
            "soft_warnings": soft_warnings,
            "can_publish": status in {"ENTER", "OPERABLE"},
            "should_observe": status in {"OBSERVE", "WAIT_CONFIRMATION"},
            "should_block": status in {"BLOCKED", "NO_BET"},
      }
