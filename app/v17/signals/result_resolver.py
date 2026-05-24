from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class ResultResolver:
    """
    Resuelve el resultado de una señal.

    Reglas:
    - No cerrar señal si el reloj está atrasado.
    - No cerrar señal si el marcador no es confiable.
    - OVER gana si aparece un gol adicional después de la entrada.
    - UNDER gana si pasa la ventana de seguimiento sin gol adicional.
    - Si hay datos malos, queda pendiente por confirmación.
    """

    def resolve(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(tracked_signal, dict) or not isinstance(current_match, dict):
            return self._pending(
                tracked_signal=tracked_signal,
                reason="Datos insuficientes para resolver la señal.",
                pending_reason="INVALID_RESOLUTION_INPUT",
            )

        market = str(tracked_signal.get("market") or tracked_signal.get("master_market") or "").upper()

        entry_minute = safe_int(tracked_signal.get("entry_minute"), 0)
        current_minute = safe_int(
            current_match.get("api_minute")
            or current_match.get("display_minute")
            or current_match.get("minute"),
            0,
        )

        entry_home_score = safe_int(tracked_signal.get("entry_home_score"), 0)
        entry_away_score = safe_int(tracked_signal.get("entry_away_score"), 0)
        current_home_score = safe_int(current_match.get("home_score"), entry_home_score)
        current_away_score = safe_int(current_match.get("away_score"), entry_away_score)

        entry_total_goals = safe_int(
            tracked_signal.get("entry_total_goals"),
            entry_home_score + entry_away_score,
        )
        current_total_goals = current_home_score + current_away_score

        follow_minutes = max(0, current_minute - entry_minute)

        clock_status = str(current_match.get("clock_status") or "").upper()
        clock_can_enter = bool(current_match.get("clock_can_enter", True))
        data_age_seconds = safe_int(current_match.get("data_age_seconds"), 0)

        if clock_status in {"BLOCKED_CLOCK", "CLOCK_WARNING"} or not clock_can_enter:
            return self._pending(
                tracked_signal=tracked_signal,
                reason="No se cierra la señal porque el reloj live no está confirmado.",
                pending_reason="CLOCK_NOT_CONFIRMED",
                current_match=current_match,
            )

        if data_age_seconds > 90:
            return self._pending(
                tracked_signal=tracked_signal,
                reason="No se cierra la señal porque el dato está atrasado.",
                pending_reason="DATA_TOO_OLD",
                current_match=current_match,
            )

        if current_minute <= 0 or current_minute < entry_minute:
            return self._pending(
                tracked_signal=tracked_signal,
                reason="No se cierra la señal porque el minuto actual no es confiable.",
                pending_reason="INVALID_CURRENT_MINUTE",
                current_match=current_match,
            )

        if current_total_goals < entry_total_goals:
            return self._pending(
                tracked_signal=tracked_signal,
                reason="No se cierra la señal porque el marcador actual es inconsistente.",
                pending_reason="INVALID_SCORE_REGRESSION",
                current_match=current_match,
            )

        if market == "OVER":
            return self._resolve_over(
                tracked_signal=tracked_signal,
                current_match=current_match,
                entry_total_goals=entry_total_goals,
                current_total_goals=current_total_goals,
                follow_minutes=follow_minutes,
            )

        if market == "UNDER":
            return self._resolve_under(
                tracked_signal=tracked_signal,
                current_match=current_match,
                entry_total_goals=entry_total_goals,
                current_total_goals=current_total_goals,
                follow_minutes=follow_minutes,
            )

        return self._void(
            tracked_signal=tracked_signal,
            reason="Mercado no resoluble para tracking.",
            void_reason="UNSUPPORTED_MARKET",
            current_match=current_match,
        )

    def _resolve_over(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
        entry_total_goals: int,
        current_total_goals: int,
        follow_minutes: int,
    ) -> Dict[str, Any]:
        max_follow_minutes = safe_int(tracked_signal.get("max_follow_minutes"), 20)

        if current_total_goals > entry_total_goals:
            return self._won(
                tracked_signal=tracked_signal,
                current_match=current_match,
                reason="La señal OVER acertó porque hubo al menos un gol después de la entrada.",
                win_reason="GOAL_AFTER_ENTRY",
            )

        if follow_minutes >= max_follow_minutes:
            failure_reason = self._detect_failure_reason(tracked_signal, current_match)

            return self._lost(
                tracked_signal=tracked_signal,
                current_match=current_match,
                reason="La señal OVER falló porque no hubo gol dentro de la ventana de seguimiento.",
                failure_reason=failure_reason,
            )

        return self._pending(
            tracked_signal=tracked_signal,
            current_match=current_match,
            reason="La señal OVER sigue pendiente porque todavía está dentro de la ventana de seguimiento.",
            pending_reason="OVER_WAITING_GOAL",
        )

    def _resolve_under(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
        entry_total_goals: int,
        current_total_goals: int,
        follow_minutes: int,
    ) -> Dict[str, Any]:
        max_follow_minutes = safe_int(tracked_signal.get("max_follow_minutes"), 20)

        if current_total_goals > entry_total_goals:
            return self._lost(
                tracked_signal=tracked_signal,
                current_match=current_match,
                reason="La señal UNDER falló porque hubo un gol después de la entrada.",
                failure_reason="GOAL_AGAINST_UNDER",
            )

        if follow_minutes >= max_follow_minutes:
            return self._won(
                tracked_signal=tracked_signal,
                current_match=current_match,
                reason="La señal UNDER acertó porque el marcador se sostuvo durante la ventana de seguimiento.",
                win_reason="SCORE_HELD",
            )

        return self._pending(
            tracked_signal=tracked_signal,
            current_match=current_match,
            reason="La señal UNDER sigue pendiente porque todavía está dentro de la ventana de seguimiento.",
            pending_reason="UNDER_WAITING_WINDOW",
        )

    def _detect_failure_reason(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
    ) -> str:
        failed_filters = tracked_signal.get("failed_secondary_filters") or []
        soft_warnings = tracked_signal.get("soft_warnings") or []
        risk_reasons = tracked_signal.get("risk_reasons") or []

        total_shots_on = safe_int(current_match.get("total_shots_on"), 0)
        false_pressure_risk = safe_float(tracked_signal.get("false_pressure_risk"), 0.0)
        score_hold_probability = safe_float(tracked_signal.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(tracked_signal.get("under_transition_score"), 0.0)

        text_pool = " ".join(map(str, failed_filters + soft_warnings + risk_reasons)).upper()

        if "CLOCK" in text_pool:
            return "MINUTO_ATRASADO"

        if false_pressure_risk >= 70 or "FALSE_PRESSURE" in text_pool:
            return "PRESION_FALSA"

        if total_shots_on <= 1:
            return "OVER_SIN_TIRO_AL_ARCO"

        if score_hold_probability >= 75:
            return "RETENCION_NO_SUPERADA"

        if under_transition_score >= 75:
            return "TRANSICION_UNDER_NO_DETECTADA"

        if "CONMEBOL" in text_pool:
            return "CONMEBOL_SIN_CONFIRMACION"

        if "SCORE_HOLD" in text_pool:
            return "RESULTADO_PROBABLE_CONTRARIO"

        if "SIGNAL_AGED" in text_pool or "NO_REENTRY" in text_pool:
            return "SENAL_ENVEJECIDA"

        return "SIN_GOL_EN_VENTANA"

    def _won(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
        reason: str,
        win_reason: str,
    ) -> Dict[str, Any]:
        return self._base_result(
            tracked_signal=tracked_signal,
            current_match=current_match,
            result_status="WON",
            result_label="ACERTADA",
            resolved=True,
            reason=reason,
            result_reason=win_reason,
        )

    def _lost(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
        reason: str,
        failure_reason: str,
    ) -> Dict[str, Any]:
        return self._base_result(
            tracked_signal=tracked_signal,
            current_match=current_match,
            result_status="LOST",
            result_label="FALLIDA",
            resolved=True,
            reason=reason,
            result_reason=failure_reason,
        )

    def _pending(
        self,
        tracked_signal: Dict[str, Any],
        reason: str,
        pending_reason: str,
        current_match: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return self._base_result(
            tracked_signal=tracked_signal,
            current_match=current_match or {},
            result_status="PENDING",
            result_label="PENDIENTE",
            resolved=False,
            reason=reason,
            result_reason=pending_reason,
        )

    def _void(
        self,
        tracked_signal: Dict[str, Any],
        reason: str,
        void_reason: str,
        current_match: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return self._base_result(
            tracked_signal=tracked_signal,
            current_match=current_match or {},
            result_status="VOID",
            result_label="ANULADA",
            resolved=True,
            reason=reason,
            result_reason=void_reason,
        )

    def _base_result(
        self,
        tracked_signal: Dict[str, Any],
        current_match: Dict[str, Any],
        result_status: str,
        result_label: str,
        resolved: bool,
        reason: str,
        result_reason: str,
    ) -> Dict[str, Any]:
        current_home_score = safe_int(
            current_match.get("home_score"),
            safe_int(tracked_signal.get("entry_home_score"), 0),
        )
        current_away_score = safe_int(
            current_match.get("away_score"),
            safe_int(tracked_signal.get("entry_away_score"), 0),
        )

        current_minute = safe_int(
            current_match.get("api_minute")
            or current_match.get("display_minute")
            or current_match.get("minute"),
            safe_int(tracked_signal.get("entry_minute"), 0),
        )

        return {
            **tracked_signal,
            "result_status": result_status,
            "result_label": result_label,
            "resolved": resolved,
            "resolved_at": utc_now_iso() if resolved else None,
            "result_reason": result_reason,
            "result_explanation": reason,
            "current_minute": current_minute,
            "current_home_score": current_home_score,
            "current_away_score": current_away_score,
            "current_score": f"{current_home_score}-{current_away_score}",
            "current_total_goals": current_home_score + current_away_score,
          }
