from __future__ import annotations

from typing import Any, Dict

from app.v17.core.constants import (
    FRESH_SIGNAL_MINUTES,
    VALIDATING_SIGNAL_MINUTES,
    AGING_SIGNAL_MINUTES,
    HIGH_RISK_SIGNAL_MINUTES,
)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


class SignalLifecycle:
    """
    Controla la vida útil de una señal.

    Regla V17:
    - Una señal fresca puede seguir viva.
    - Una señal en validación no debe forzar entrada.
    - Una señal envejecida requiere confirmación.
    - Una señal reactivada no entra automáticamente.
    - Una señal expirada queda en NO_REENTRY.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        current_minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("minute"),
            0,
        )

        entry_minute = safe_int(
            signal.get("entry_minute")
            or signal.get("signal_minute")
            or signal.get("created_minute")
            or current_minute,
            current_minute,
        )

        age_minutes = max(0, current_minute - entry_minute)

        if age_minutes <= FRESH_SIGNAL_MINUTES:
            life_status = "SIGNAL_FRESH"
            life_action = "VALID"
            life_penalty = 0
            life_label = "SEÑAL FRESCA"

        elif age_minutes <= VALIDATING_SIGNAL_MINUTES:
            life_status = "SIGNAL_VALIDATING"
            life_action = "KEEP_VALIDATING"
            life_penalty = 4
            life_label = "SEÑAL EN VALIDACIÓN"

        elif age_minutes <= AGING_SIGNAL_MINUTES:
            life_status = "SIGNAL_COOLING"
            life_action = "DEGRADE_CONFIDENCE"
            life_penalty = 10
            life_label = "SEÑAL ENFRIÁNDOSE"

        elif age_minutes <= HIGH_RISK_SIGNAL_MINUTES:
            life_status = "SIGNAL_AGED"
            life_action = "WAIT_CONFIRMATION"
            life_penalty = 18
            life_label = "SEÑAL ENVEJECIDA"

        else:
            life_status = "SIGNAL_EXPIRED"
            life_action = "NO_REENTRY"
            life_penalty = 35
            life_label = "NO REENTRY"

        reactivation = bool(signal.get("reactivation_detected", False))

        if reactivation and life_status in {"SIGNAL_COOLING", "SIGNAL_AGED"}:
            life_status = "SIGNAL_REACTIVATED"
            life_action = "REQUIRES_CONFIRMATION"
            life_penalty = max(6, life_penalty - 8)
            life_label = "REACTIVADA, PERO REQUIERE CONFIRMACIÓN"

        return {
            "lifecycle_role": "EVIDENCE_ONLY",
            "lifecycle_is_official_decision": False,
            "entry_minute": entry_minute,
            "current_minute": current_minute,
            "signal_age_minutes": age_minutes,

            "signal_life_status": life_status,
            "signal_life_action": life_action,
            "signal_life_penalty": life_penalty,
            "signal_life_label": life_label,

            "signal_expired": life_status == "SIGNAL_EXPIRED",
            "no_reentry": life_action == "NO_REENTRY",

            "reactivation_detected": reactivation,
            "reactivation_requires_confirmation": life_status == "SIGNAL_REACTIVATED",

            "lifecycle_can_publish": life_action == "VALID",
            "lifecycle_requires_wait": life_action in {
                "KEEP_VALIDATING",
                "DEGRADE_CONFIDENCE",
                "WAIT_CONFIRMATION",
                "REQUIRES_CONFIRMATION",
            },
        }
