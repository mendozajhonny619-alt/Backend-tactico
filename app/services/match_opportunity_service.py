from __future__ import annotations

import logging
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class MatchOpportunityService:
    """
    Motor operativo de oportunidades.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = self._extract_minute(match)
        match_name = (
            match.get("match_name")
            or match.get("partido")
            or f"{match.get('home', 'HOME')} vs {match.get('away', 'AWAY')}"
        )

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "ALTO").upper()

        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))
        over_window_score = self._safe_float(context.get("over_window_score"))
        goal_window_score = self._safe_float(context.get("goal_window_score"))

        logger.info(
            "OPPORTUNITY_EVAL | %s | min=%s ai=%.2f goal=%.2f over=%.2f under=%.2f "
            "risk=%s(%.2f) dq=%s gq=%s ctx=%s pressure=%.2f rhythm=%.2f",
            match_name,
            minute,
            ai_score,
            goal_probability,
            over_probability,
            under_probability,
            risk_level,
            risk_score,
            data_quality,
            game_quality,
            context_state,
            pressure_index,
            rhythm_index,
        )

        if not window.get("allowed", False):
            return self._response("REJECTED", "NO_BET", None, "REJECTED_INVALID_WINDOW")

        if risk_level == "ALTO" and risk_score >= 8.5:
            return self._response("NO_BET", "NO_BET", None, "NO_BET_RISK_TOO_HIGH")

        if window.get("allow_over", False):
            over_check = self._evaluate_over_candidate(
                minute=minute,
                ai_score=ai_score,
                goal_probability=goal_probability,
                over_probability=over_probability,
                pressure_index=pressure_index,
                rhythm_index=rhythm_index,
                over_window_score=over_window_score,
                goal_window_score=goal_window_score,
                context_state=context_state,
                game_quality=game_quality,
                data_quality=data_quality,
                risk_level=risk_level,
                risk_score=risk_score,
                window=window,
            )

            if over_check["approved"]:
                return self._response(
                    type_="OVER_CANDIDATE",
                    rank=over_check["rank"],
                    market="OVER",
                    reason=over_check["reason"],
                )

        if window.get("allow_under", False):
            under_check = self._evaluate_under_candidate(
                minute=minute,
                ai_score=ai_score,
                under_probability=under_probability,
                goal_probability=goal_probability,
                pressure_index=pressure_index,
                rhythm_index=rhythm_index,
                over_window_score=over_window_score,
                goal_window_score=goal_window_score,
                context_state=context_state,
                game_quality=game_quality,
                data_quality=data_quality,
                risk_level=risk_level,
                risk_score=risk_score,
                window=window,
            )

            if under_check["approved"]:
                return self._response(
                    type_="UNDER_CANDIDATE",
                    rank=under_check["rank"],
                    market="UNDER",
                    reason=under_check["reason"],
                )

        observe_check = self._evaluate_observation(
            minute=minute,
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            pressure_index=pressure_index,
            rhythm_index=rhythm_index,
            context_state=context_state,
            game_quality=game_quality,
        )

        if observe_check:
            return self._response("OBSERVE", "OBSERVACION", None, "OBSERVE_PARTIAL_ALIGNMENT")

        return self._response("NO_BET", "NO_BET", None, "NO_BET_NO_CLEAR_EDGE")

    def _evaluate_over_candidate(
        self,
        minute: int,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        pressure_index: float,
        rhythm_index: float,
        over_window_score: float,
        goal_window_score: float,
        context_state: str,
        game_quality: str,
        data_quality: str,
        risk_level: str,
        risk_score: float,
        window: Dict[str, Any],
    ) -> Dict[str, Any]:
        gate_min_score = self._safe_float(window.get("gate_min_score") or 60)

        critical_failed: List[str] = []

        if minute < 15:
            critical_failed.append("OVER_MINUTE_TOO_EARLY")
        if minute >= 80:
            critical_failed.append("OVER_TOO_LATE")
        if ai_score < 45:
            critical_failed.append("OVER_AI_CRITICAL_LOW")
        if goal_probability < 52:
            critical_failed.append("OVER_GOAL_PROB_CRITICAL_LOW")
        if over_probability < 52:
            critical_failed.append("OVER_PROB_CRITICAL_LOW")
        if context_state in {"MUERTO", "FRIO"}:
            critical_failed.append("OVER_CONTEXT_DEAD")
        if risk_level == "ALTO" and risk_score >= 7.8:
            critical_failed.append("OVER_RISK_TOO_HIGH")

        if critical_failed:
            return self._fail("OVER_CRITICAL_FILTER_FAILED", [], critical_failed, 0.0)

        checks = {
            "AI_OK": ai_score >= 58,
            "AI_STRONG": ai_score >= 68,
            "GOAL_PROB_OK": goal_probability >= 60,
            "GOAL_PROB_STRONG": goal_probability >= 70,
            "OVER_PROB_OK": over_probability >= 60,
            "OVER_PROB_STRONG": over_probability >= 70,
            "GATE_OK": ai_score >= max(gate_min_score - 12, 50),
            "CONTEXT_OK": context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"},
            "CONTEXT_STRONG": context_state in {"CALIENTE", "MUY_CALIENTE"},
            "PRESSURE_OK": pressure_index >= 10,
            "PRESSURE_STRONG": pressure_index >= 18,
            "RHYTHM_OK": rhythm_index >= 7,
            "RHYTHM_STRONG": rhythm_index >= 12,
            "OVER_WINDOW_OK": over_window_score >= 12,
            "GOAL_WINDOW_OK": goal_window_score >= 12,
            "GAME_QUALITY_OK": game_quality in {"MEDIUM", "HIGH"},
            "DATA_USABLE": data_quality in {"LOW", "MEDIUM", "HIGH"},
            "DATA_GOOD": data_quality in {"MEDIUM", "HIGH"},
            "MINUTE_OK": 15 <= minute <= 75,
        }

        passed, failed, pass_ratio = self._score_checks(checks)

        if pass_ratio >= 0.82 and ai_score >= 70 and goal_probability >= 72 and over_probability >= 72:
            return self._ok("PREMIUM", "OVER_PREMIUM_CONSENSUS", passed, failed, pass_ratio)

        if pass_ratio >= 0.74 and ai_score >= 64 and goal_probability >= 66 and over_probability >= 66:
            return self._ok("FUERTE", "OVER_STRONG_CONSENSUS", passed, failed, pass_ratio)

        if pass_ratio >= 0.66 and ai_score >= 58 and goal_probability >= 62 and over_probability >= 62:
            return self._ok("BUENA", "OVER_GOOD_MAJORITY_PASS", passed, failed, pass_ratio)

        if pass_ratio >= 0.58 and ai_score >= 52 and goal_probability >= 58 and over_probability >= 58:
            return self._ok("OPERABLE", "OVER_OPERABLE_MAJORITY_PASS", passed, failed, pass_ratio)

        if (
            ai_score >= 82
            and goal_probability >= 82
            and over_probability >= 82
            and 15 <= minute <= 75
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        ):
            return self._ok("FUERTE", "OVER_HIGH_AI_RESCUE", passed, failed, pass_ratio)

        return self._fail("OVER_NOT_ENOUGH_CONSENSUS", passed, failed, pass_ratio)

    def _evaluate_under_candidate(
        self,
        minute: int,
        ai_score: float,
        under_probability: float,
        goal_probability: float,
        pressure_index: float,
        rhythm_index: float,
        over_window_score: float,
        goal_window_score: float,
        context_state: str,
        game_quality: str,
        data_quality: str,
        risk_level: str,
        risk_score: float,
        window: Dict[str, Any],
    ) -> Dict[str, Any]:
        gate_min_score = self._safe_float(window.get("gate_min_score") or 60)

        critical_failed: List[str] = []

        if minute < 58:
            critical_failed.append("UNDER_TOO_EARLY")
        if ai_score < 55:
            critical_failed.append("UNDER_AI_CRITICAL_LOW")
        if under_probability < 60:
            critical_failed.append("UNDER_PROB_CRITICAL_LOW")
        if goal_probability > 58:
            critical_failed.append("UNDER_GOAL_PROB_TOO_HIGH")
        if context_state in {"CALIENTE", "MUY_CALIENTE"}:
            critical_failed.append("UNDER_CONTEXT_TOO_HOT")
        if pressure_index > 28:
            critical_failed.append("UNDER_PRESSURE_TOO_HIGH")
        if risk_level == "ALTO" and risk_score >= 7.5:
            critical_failed.append("UNDER_RISK_TOO_HIGH")

        if critical_failed:
            return self._fail(
                reason="UNDER_CRITICAL_FILTER_FAILED",
                passed=[],
                failed=critical_failed,
                pass_ratio=0.0,
            )

        checks = {
            "MINUTE_OK": minute >= 60,
            "MINUTE_STRONG": minute >= 66,
            "AI_OK": ai_score >= 60,
            "AI_STRONG": ai_score >= 70,
            "UNDER_PROB_OK": under_probability >= 64,
            "UNDER_PROB_STRONG": under_probability >= 72,
            "GOAL_PROB_LOW": goal_probability <= 52,
            "GATE_OK": ai_score >= max(gate_min_score - 8, 55),
            "CONTEXT_OK": context_state in {"CONTROLADO", "TIBIO", "FRIO", "MUERTO"},
            "CONTEXT_STRONG": context_state in {"CONTROLADO", "FRIO", "MUERTO"},
            "PRESSURE_OK": pressure_index <= 24,
            "PRESSURE_STRONG": pressure_index <= 18,
            "RHYTHM_OK": rhythm_index <= 15,
            "RHYTHM_STRONG": rhythm_index <= 11,
            "GOAL_THREAT_OK": over_window_score <= 20 and goal_window_score <= 20,
            "GOAL_THREAT_STRONG": over_window_score <= 15 and goal_window_score <= 15,
            "DATA_GOOD": data_quality in {"MEDIUM", "HIGH"},
            "GAME_NOT_HIGH": game_quality in {"LOW", "MEDIUM"},
        }

        passed, failed, pass_ratio = self._score_checks(checks)

        if pass_ratio >= 0.86 and ai_score >= 78 and under_probability >= 76:
            return self._ok("PREMIUM", "UNDER_PREMIUM_CONSENSUS", passed, failed, pass_ratio)

        if pass_ratio >= 0.78 and ai_score >= 70 and under_probability >= 70:
            return self._ok("FUERTE", "UNDER_STRONG_CONSENSUS", passed, failed, pass_ratio)

        if pass_ratio >= 0.72 and ai_score >= 64 and under_probability >= 66:
            return self._ok("BUENA", "UNDER_GOOD_MAJORITY_PASS", passed, failed, pass_ratio)

        if pass_ratio >= 0.64 and ai_score >= 60 and under_probability >= 64:
            return self._ok("OPERABLE", "UNDER_OPERABLE_MAJORITY_PASS", passed, failed, pass_ratio)

        return self._fail("UNDER_NOT_ENOUGH_CONSENSUS", passed, failed, pass_ratio)

    def _evaluate_observation(
        self,
        minute: int,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        pressure_index: float,
        rhythm_index: float,
        context_state: str,
        game_quality: str,
    ) -> bool:
        if minute < 10:
            return False

        over_watch = (
            ai_score >= 45
            and goal_probability >= 52
            and over_probability >= 52
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        )

        under_watch = (
            minute >= 55
            and under_probability >= 56
            and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
            and pressure_index <= 24
        )

        activity_watch = (
            game_quality in {"MEDIUM", "HIGH"}
            and (pressure_index >= 8 or rhythm_index >= 6)
        )

        return over_watch or under_watch or activity_watch

    def _score_checks(self, checks: Dict[str, bool]) -> tuple[list[str], list[str], float]:
        passed = [key for key, value in checks.items() if value]
        failed = [key for key, value in checks.items() if not value]
        total = len(checks) or 1
        pass_ratio = len(passed) / total
        return passed, failed, pass_ratio

    def _ok(
        self,
        rank: str,
        reason: str,
        passed: list[str],
        failed: list[str],
        pass_ratio: float,
    ) -> Dict[str, Any]:
        return {
            "approved": True,
            "rank": rank,
            "reason": reason,
            "passed": passed,
            "failed": failed,
            "pass_ratio": round(pass_ratio, 4),
        }

    def _fail(
        self,
        reason: str,
        passed: list[str],
        failed: list[str],
        pass_ratio: float,
    ) -> Dict[str, Any]:
        return {
            "approved": False,
            "rank": "NO_BET",
            "reason": reason,
            "passed": passed,
            "failed": failed,
            "pass_ratio": round(pass_ratio, 4),
        }

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or 0
        )
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _response(
        self,
        type_: str,
        rank: str,
        market: str | None,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "type": type_,
            "rank": rank,
            "market": market,
            "reason": reason,
        }
