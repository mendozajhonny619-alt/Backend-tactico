from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.opportunity_context_validator import OpportunityContextValidator
from app.services.match_state_guard import MatchStateGuard


logger = logging.getLogger(__name__)


class MatchOpportunityService:
    """
    Motor operativo de oportunidades.

    Convierte lectura IA + contexto + ventana en:
    - OVER_CANDIDATE
    - UNDER_CANDIDATE
    - OBSERVE
    - NO_BET

    No calcula contexto.
    No calcula IA.
    No publica señales.
    Solo decide si la lectura actual merece oportunidad.
    """

    def __init__(self) -> None:
        self._context_validator = OpportunityContextValidator()
        self._match_state_guard = MatchStateGuard()

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}
        window = window or {}

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
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))

        live_read = self._opportunity_live_read(
            minute=minute,
            context=context,
            ai=ai,
        )

        logger.info(
            "OPPORTUNITY_EVAL | %s | min=%s ai=%.2f goal=%.2f over=%.2f under=%.2f "
            "risk=%s(%.2f) dq=%s gq=%s ctx=%s pressure=%.2f rhythm=%.2f live=%s",
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
            live_read.get("opportunity_live_status"),
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
                cooling_detected=cooling_detected,
                under_transition_score=under_transition_score,
                live_read=live_read,
            )

            if over_check["approved"]:
                state_guard = self._match_state_guard.evaluate(
                    match=match,
                    context=context,
                    ai=ai,
                    opportunity={
                        "type": "OVER_CANDIDATE",
                        "rank": over_check["rank"],
                        "market": "OVER",
                        "reason": over_check["reason"],
                    },
                )

                if state_guard.get("force_action") == "REJECT":
                    response = self._response(
                        "NO_BET",
                        "NO_BET",
                        None,
                        state_guard.get("match_state_reason", "MATCH_STATE_REJECT"),
                    )
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                if state_guard.get("force_action") == "OBSERVE":
                    response = self._response(
                        "OBSERVE",
                        "OBSERVACION",
                        state_guard.get("suggested_market"),
                        state_guard.get("match_state_reason", "MATCH_STATE_OBSERVE"),
                    )
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                validation = self._context_validator.validate(match, context, ai, "OVER")

                if validation.get("opportunity_context_status") == "DANGER":
                    response = self._response(
                        "OBSERVE",
                        "OBSERVACION",
                        None,
                        "OVER_BLOCKED_BY_CONTEXT_VALIDATOR",
                    )
                    response.update(validation)
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                rank = over_check["rank"]
                if validation.get("opportunity_context_status") == "WARNING":
                    rank = "OPERABLE"
                elif validation.get("opportunity_context_status") == "CAUTION" and rank in {"PREMIUM", "FUERTE"}:
                    rank = "BUENA"

                response = self._response(
                    type_="OVER_CANDIDATE",
                    rank=rank,
                    market="OVER",
                    reason=over_check["reason"],
                )
                response.update(validation)
                response.update(state_guard)
                response.update(live_read)
                return response

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
                cooling_detected=cooling_detected,
                under_transition_score=under_transition_score,
                live_read=live_read,
            )

            if under_check["approved"]:
                state_guard = self._match_state_guard.evaluate(
                    match=match,
                    context=context,
                    ai=ai,
                    opportunity={
                        "type": "UNDER_CANDIDATE",
                        "rank": under_check["rank"],
                        "market": "UNDER",
                        "reason": under_check["reason"],
                    },
                )

                if state_guard.get("force_action") == "REJECT":
                    response = self._response(
                        "NO_BET",
                        "NO_BET",
                        None,
                        state_guard.get("match_state_reason", "MATCH_STATE_REJECT"),
                    )
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                if state_guard.get("force_action") == "OBSERVE":
                    response = self._response(
                        "OBSERVE",
                        "OBSERVACION",
                        state_guard.get("suggested_market"),
                        state_guard.get("match_state_reason", "MATCH_STATE_OBSERVE"),
                    )
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                validation = self._context_validator.validate(match, context, ai, "UNDER")

                if validation.get("opportunity_context_status") == "DANGER":
                    response = self._response(
                        "OBSERVE",
                        "OBSERVACION",
                        None,
                        "UNDER_BLOCKED_BY_CONTEXT_VALIDATOR",
                    )
                    response.update(validation)
                    response.update(state_guard)
                    response.update(live_read)
                    return response

                rank = under_check["rank"]
                if validation.get("opportunity_context_status") == "WARNING":
                    rank = "OPERABLE"
                elif validation.get("opportunity_context_status") == "CAUTION" and rank in {"PREMIUM", "FUERTE"}:
                    rank = "BUENA"

                response = self._response(
                    type_="UNDER_CANDIDATE",
                    rank=rank,
                    market="UNDER",
                    reason=under_check["reason"],
                )
                response.update(validation)
                response.update(state_guard)
                response.update(live_read)
                return response

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
            live_read=live_read,
        )

        if observe_check:
            response = self._response("OBSERVE", "OBSERVACION", None, "OBSERVE_PARTIAL_ALIGNMENT")
            response.update(live_read)
            return response

        response = self._response("NO_BET", "NO_BET", None, "NO_BET_NO_CLEAR_EDGE")
        response.update(live_read)
        return response

    def _opportunity_live_read(
        self,
        minute: int,
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        under_transition = self._safe_float(context.get("under_transition_score"))

        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        context_state = str(context.get("context_state") or "MUERTO").upper()
        field_vision_status = str(context.get("field_vision_status") or "").upper()

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        cooling_detected = bool(context.get("cooling_detected", False))
        red_alert = bool(context.get("red_alert", False))

        is_late_game = bool(context.get("is_late_game") or context.get("field_vision_is_late_game") or minute >= 75)
        is_added_time = bool(context.get("is_added_time") or context.get("field_vision_is_added_time") or minute >= 90)

        status = "NORMAL"
        advice = "Lectura de oportunidad estándar."
        over_permission = "NORMAL"
        under_permission = "NORMAL"
        opportunity_bias = "NEUTRAL"
        opportunity_live_score = 50.0

        warnings: List[str] = []
        positives: List[str] = []

        if chaos_mode or field_vision_status == "CHAOS" or red_alert:
            status = "CHAOS_OPPORTUNITY"
            opportunity_bias = "OVER_WATCH"
            over_permission = "PROTECTED"
            opportunity_live_score += 18
            positives.append("OPP_CHAOS_OR_RED_ALERT")
            advice = "Partido volátil: posible ruptura del marcador."

        elif late_reactivation or field_vision_status == "REACTIVATION":
            status = "REACTIVATION_OPPORTUNITY"
            opportunity_bias = "OVER_WATCH"
            over_permission = "PROTECTED"
            opportunity_live_score += 14
            positives.append("OPP_LATE_REACTIVATION")
            advice = "Reactivación ofensiva: el minuto avanzado no debe bloquear automáticamente."

        if fake_pressure_detected or field_vision_status == "FAKE_PRESSURE":
            status = "FAKE_PRESSURE_RISK"
            opportunity_bias = "UNDER_WATCH"
            over_permission = "RESTRICTED"
            under_permission = "SUPPORTED"
            opportunity_live_score -= 12
            warnings.append("OPP_FAKE_PRESSURE")
            advice = "Presión aparente sin precisión: cuidado con OVER."

        if pressure_without_depth or field_vision_status == "PRESSURE_WITHOUT_DEPTH":
            if status == "NORMAL":
                status = "NO_DEPTH_RISK"
            opportunity_bias = "UNDER_WATCH"
            over_permission = "RESTRICTED"
            under_permission = "SUPPORTED"
            opportunity_live_score -= 8
            warnings.append("OPP_PRESSURE_WITHOUT_DEPTH")
            advice = "Hay acercamientos, pero falta profundidad real."

        if retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            status = "RETENTION_OPPORTUNITY"
            opportunity_bias = "UNDER"
            over_permission = "BLOCK_LATE_IF_WEAK"
            under_permission = "SUPPORTED"
            opportunity_live_score += 8
            warnings.append("OPP_RETENTION_SHAPE")
            advice = "Perfil de retención: posible oportunidad UNDER o mantener observación."

        if cooling_detected and not late_reactivation and not chaos_mode:
            if status == "NORMAL":
                status = "COOLING_OPPORTUNITY"
            opportunity_bias = "UNDER_WATCH"
            over_permission = "RESTRICTED"
            under_permission = "SUPPORTED"
            opportunity_live_score -= 6
            warnings.append("OPP_COOLING_DETECTED")

        if is_late_game and minute >= 80:
            if over_permission == "PROTECTED":
                positives.append("OPP_LATE_OVER_ALLOWED_WITH_CONFIRMATION")
            elif pressure >= 26 and rhythm >= 15 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
                over_permission = "PROTECTED"
                opportunity_bias = "OVER_WATCH"
                opportunity_live_score += 8
                positives.append("OPP_LATE_CONTEXT_PRESSURE_ACTIVE")
            else:
                over_permission = "RESTRICTED"
                warnings.append("OPP_LATE_REQUIRES_STRONG_CONFIRMATION")

        if is_added_time:
            if over_permission == "PROTECTED":
                positives.append("OPP_ADDED_TIME_DANGER")
            else:
                over_permission = "RESTRICTED"
                warnings.append("OPP_ADDED_TIME_CAUTION")

        if under_transition >= 70:
            under_permission = "SUPPORTED"
            if opportunity_bias == "NEUTRAL":
                opportunity_bias = "UNDER"
            opportunity_live_score += 8
            positives.append("OPP_UNDER_TRANSITION_CONFIRMED")

        if goal_probability >= 68 and over_probability >= 68 and over_permission != "RESTRICTED":
            opportunity_live_score += 6
            positives.append("OPP_OVER_PROB_ALIGNMENT")

        if under_probability >= 68 and under_permission == "SUPPORTED":
            opportunity_live_score += 6
            positives.append("OPP_UNDER_PROB_ALIGNMENT")

        return {
            "opportunity_live_status": status,
            "opportunity_live_score": round(max(0.0, min(opportunity_live_score, 100.0)), 2),
            "opportunity_live_bias": opportunity_bias,
            "opportunity_over_permission": over_permission,
            "opportunity_under_permission": under_permission,
            "opportunity_live_advice": advice,
            "opportunity_live_warnings": warnings,
            "opportunity_live_positive_factors": positives,
        }

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
        cooling_detected: bool,
        under_transition_score: float,
        live_read: Dict[str, Any],
    ) -> Dict[str, Any]:
        gate_min_score = self._safe_float(window.get("gate_min_score") or 60)

        over_permission = str(live_read.get("opportunity_over_permission") or "NORMAL").upper()
        live_status = str(live_read.get("opportunity_live_status") or "NORMAL").upper()

        late_over_protected = over_permission == "PROTECTED"
        over_restricted = over_permission in {"RESTRICTED", "BLOCK_LATE_IF_WEAK"}

        critical_failed: List[str] = []

        if minute < 15:
            critical_failed.append("OVER_MINUTE_TOO_EARLY")

        # Antes: minuto >= 80 bloqueaba siempre.
        # Ahora: minuto avanzado solo bloquea si no hay presión viva / caos / reactivación.
        if minute >= 80 and not late_over_protected:
            critical_failed.append("OVER_TOO_LATE_WITHOUT_LIVE_CONFIRMATION")

        if ai_score < 45:
            critical_failed.append("OVER_AI_CRITICAL_LOW")
        if goal_probability < 52:
            critical_failed.append("OVER_GOAL_PROB_CRITICAL_LOW")
        if over_probability < 52:
            critical_failed.append("OVER_PROB_CRITICAL_LOW")
        if context_state in {"MUERTO", "FRIO"} and not late_over_protected:
            critical_failed.append("OVER_CONTEXT_DEAD")
        if context_state == "CONTROLADO" and minute >= 65 and not late_over_protected:
            critical_failed.append("OVER_CONTROLLED_LATE_CONTEXT")
        if cooling_detected and not late_over_protected:
            critical_failed.append("OVER_COOLING_DETECTED")
        if under_transition_score >= 70 and not late_over_protected:
            critical_failed.append("OVER_UNDER_TRANSITION_ACTIVE")
        if risk_level == "ALTO" and risk_score >= 7.8:
            critical_failed.append("OVER_RISK_TOO_HIGH")

        if over_restricted and minute >= 75 and not late_over_protected:
            critical_failed.append("OVER_RESTRICTED_BY_LIVE_READ")

        if critical_failed:
            return self._fail("OVER_CRITICAL_FILTER_FAILED", [], critical_failed, 0.0)

        minute_ok = 15 <= minute <= 75 or late_over_protected

        checks = {
            "AI_OK": ai_score >= 58,
            "AI_STRONG": ai_score >= 68,
            "GOAL_PROB_OK": goal_probability >= 60,
            "GOAL_PROB_STRONG": goal_probability >= 70,
            "OVER_PROB_OK": over_probability >= 60,
            "OVER_PROB_STRONG": over_probability >= 70,
            "GATE_OK": ai_score >= max(gate_min_score - 12, 50),
            "CONTEXT_OK": context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"} or late_over_protected,
            "CONTEXT_STRONG": context_state in {"CALIENTE", "MUY_CALIENTE"} or live_status in {"CHAOS_OPPORTUNITY", "REACTIVATION_OPPORTUNITY"},
            "PRESSURE_OK": pressure_index >= 10,
            "PRESSURE_STRONG": pressure_index >= 18,
            "RHYTHM_OK": rhythm_index >= 7,
            "RHYTHM_STRONG": rhythm_index >= 12,
            "OVER_WINDOW_OK": over_window_score >= 12,
            "GOAL_WINDOW_OK": goal_window_score >= 12,
            "GAME_QUALITY_OK": game_quality in {"MEDIUM", "HIGH"},
            "DATA_USABLE": data_quality in {"LOW", "MEDIUM", "HIGH"},
            "DATA_GOOD": data_quality in {"MEDIUM", "HIGH"},
            "MINUTE_OK": minute_ok,
            "LIVE_READ_OK": not over_restricted or late_over_protected,
        }

        passed, failed, pass_ratio = self._score_checks(checks)

        if late_over_protected and minute >= 80:
            if (
                pass_ratio >= 0.70
                and ai_score >= 62
                and goal_probability >= 66
                and over_probability >= 66
                and pressure_index >= 18
                and rhythm_index >= 11
            ):
                return self._ok("BUENA", "OVER_LATE_REACTIVATION_CONFIRMED", passed, failed, pass_ratio)

            if (
                pass_ratio >= 0.62
                and ai_score >= 58
                and goal_probability >= 62
                and over_probability >= 62
            ):
                return self._ok("OPERABLE", "OVER_LATE_WATCH_OPERABLE", passed, failed, pass_ratio)

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
            and (15 <= minute <= 75 or late_over_protected)
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
        cooling_detected: bool,
        under_transition_score: float,
        live_read: Dict[str, Any],
    ) -> Dict[str, Any]:
        gate_min_score = self._safe_float(window.get("gate_min_score") or 60)

        under_permission = str(live_read.get("opportunity_under_permission") or "NORMAL").upper()
        live_bias = str(live_read.get("opportunity_live_bias") or "NEUTRAL").upper()

        under_supported = under_permission == "SUPPORTED" or live_bias in {"UNDER", "UNDER_WATCH"}

        critical_failed: List[str] = []

        if minute < 58 and not under_supported:
            critical_failed.append("UNDER_TOO_EARLY")
        if ai_score < 55 and under_transition_score < 70 and not cooling_detected and not under_supported:
            critical_failed.append("UNDER_AI_CRITICAL_LOW")
        if under_probability < 60 and not under_supported:
            critical_failed.append("UNDER_PROB_CRITICAL_LOW")
        if goal_probability > 58 and not under_supported:
            critical_failed.append("UNDER_GOAL_PROB_TOO_HIGH")
        if context_state in {"CALIENTE", "MUY_CALIENTE"} and not under_supported:
            critical_failed.append("UNDER_CONTEXT_TOO_HOT")
        if pressure_index > 28 and not under_supported:
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
            "MINUTE_OK": minute >= 60 or under_supported,
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
            "UNDER_TRANSITION_OK": under_transition_score >= 70,
            "COOLING_CONFIRMED": cooling_detected,
            "LIVE_UNDER_SUPPORTED": under_supported,
            "DATA_GOOD": data_quality in {"MEDIUM", "HIGH"},
            "GAME_NOT_HIGH": game_quality in {"LOW", "MEDIUM"},
        }

        passed, failed, pass_ratio = self._score_checks(checks)

        if under_supported and pass_ratio >= 0.68 and under_probability >= 62 and goal_probability <= 58:
            if under_transition_score >= 70 or cooling_detected:
                return self._ok("BUENA", "UNDER_LIVE_RETENTION_CONFIRMED", passed, failed, pass_ratio)
            return self._ok("OPERABLE", "UNDER_LIVE_RETENTION_WATCH", passed, failed, pass_ratio)

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
        live_read: Dict[str, Any],
    ) -> bool:
        if minute < 10:
            return False

        live_bias = str(live_read.get("opportunity_live_bias") or "NEUTRAL").upper()
        live_status = str(live_read.get("opportunity_live_status") or "NORMAL").upper()

        over_watch = (
            ai_score >= 45
            and goal_probability >= 52
            and over_probability >= 52
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        )

        if live_bias == "OVER_WATCH" and ai_score >= 42 and goal_probability >= 50:
            over_watch = True

        under_watch = (
            minute >= 55
            and under_probability >= 56
            and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
            and pressure_index <= 24
        )

        if live_bias in {"UNDER", "UNDER_WATCH"} and minute >= 55 and under_probability >= 54:
            under_watch = True

        activity_watch = (
            game_quality in {"MEDIUM", "HIGH"}
            and (pressure_index >= 8 or rhythm_index >= 6)
        )

        tactical_watch = live_status in {
            "CHAOS_OPPORTUNITY",
            "REACTIVATION_OPPORTUNITY",
            "RETENTION_OPPORTUNITY",
            "FAKE_PRESSURE_RISK",
            "NO_DEPTH_RISK",
            "COOLING_OPPORTUNITY",
        }

        return over_watch or under_watch or activity_watch or tactical_watch

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
