from __future__ import annotations

from typing import Any, Dict


class EliteAnalystFilter:
    """
    Filtro final de analista élite.

    Objetivo:
    - No generar más señales por generar.
    - Mejorar la selección final.
    - Evitar señales débiles disfrazadas.
    - Permitir UNDER cuando el partido realmente está cerrado.
    """

    def validate(
        self,
        signal: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, Any]:
        signal = signal or {}
        context = context or {}
        ai = ai or {}
        risk = risk or {}

        market = str(signal.get("market") or "").upper()
        rank = str(signal.get("rank") or "").upper()

        minute = self._safe_int(signal.get("minute") or context.get("minute"))
        ai_score = self._safe_float(ai.get("ai_score") or signal.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability") or signal.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability") or signal.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability") or signal.get("under_probability"))

        risk_score = self._safe_float(risk.get("risk_score") or signal.get("risk_score"))
        risk_level = str(risk.get("risk_level") or signal.get("risk_level") or "").upper()

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        data_quality = str(context.get("data_quality") or signal.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or signal.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or signal.get("context_state") or "").upper()

        if rank not in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}:
            return self._reject("ANALYST_INVALID_RANK")

        if data_quality == "LOW":
            return self._downgrade("OBSERVACION", "ANALYST_LOW_DATA_OBSERVE")

        if risk_level == "ALTO" and risk_score >= 7.3:
            return self._downgrade("OBSERVACION", "ANALYST_RISK_TOO_HIGH")

        if minute < 12:
            return self._reject("ANALYST_TOO_EARLY")

        if "OVER" in market:
            return self._validate_over(
                rank=rank,
                minute=minute,
                ai_score=ai_score,
                goal_probability=goal_probability,
                over_probability=over_probability,
                pressure=pressure,
                rhythm=rhythm,
                context_state=context_state,
                data_quality=data_quality,
                game_quality=game_quality,
                risk_score=risk_score,
            )

        if "UNDER" in market:
            return self._validate_under(
                rank=rank,
                minute=minute,
                ai_score=ai_score,
                goal_probability=goal_probability,
                under_probability=under_probability,
                pressure=pressure,
                rhythm=rhythm,
                context_state=context_state,
                data_quality=data_quality,
                game_quality=game_quality,
                risk_score=risk_score,
            )

        return self._reject("ANALYST_UNKNOWN_MARKET")

    def _validate_over(
        self,
        rank: str,
        minute: int,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        pressure: float,
        rhythm: float,
        context_state: str,
        data_quality: str,
        game_quality: str,
        risk_score: float,
    ) -> Dict[str, Any]:
        if minute > 88:
            return self._downgrade("OBSERVACION", "ANALYST_OVER_TOO_LATE")

        if context_state in {"MUERTO", "FRIO"}:
            return self._downgrade("OBSERVACION", "ANALYST_OVER_CONTEXT_NOT_ALIVE")

        if pressure < 8 and rhythm < 6:
            return self._downgrade("OBSERVACION", "ANALYST_OVER_NO_REAL_PRESSURE")

        if rank == "OPERABLE":
            if (
                ai_score >= 58
                and goal_probability >= 62
                and over_probability >= 62
                and pressure >= 9
                and rhythm >= 6
                and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
                and risk_score <= 6.8
            ):
                return self._approve("ANALYST_OVER_OPERABLE_OK")

            return self._downgrade("OBSERVACION", "ANALYST_OVER_OPERABLE_WEAK")

        if rank == "BUENA":
            if (
                ai_score >= 62
                and goal_probability >= 66
                and over_probability >= 66
                and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
                and risk_score <= 6.8
            ):
                return self._approve("ANALYST_OVER_GOOD_OK")

            return self._downgrade("OPERABLE", "ANALYST_OVER_GOOD_DOWNGRADED")

        if rank == "FUERTE":
            if (
                ai_score >= 68
                and goal_probability >= 70
                and over_probability >= 70
                and context_state in {"CALIENTE", "MUY_CALIENTE"}
                and data_quality in {"MEDIUM", "HIGH"}
                and risk_score <= 6.6
            ):
                return self._approve("ANALYST_OVER_STRONG_OK")

            return self._downgrade("BUENA", "ANALYST_OVER_STRONG_DOWNGRADED")

        if rank == "PREMIUM":
            if (
                ai_score >= 74
                and goal_probability >= 76
                and over_probability >= 76
                and context_state in {"CALIENTE", "MUY_CALIENTE"}
                and data_quality == "HIGH"
                and game_quality in {"MEDIUM", "HIGH"}
                and risk_score <= 6.2
            ):
                return self._approve("ANALYST_OVER_PREMIUM_OK")

            return self._downgrade("FUERTE", "ANALYST_OVER_PREMIUM_DOWNGRADED")

        return self._reject("ANALYST_OVER_NOT_VALID")

    def _validate_under(
        self,
        rank: str,
        minute: int,
        ai_score: float,
        goal_probability: float,
        under_probability: float,
        pressure: float,
        rhythm: float,
        context_state: str,
        data_quality: str,
        game_quality: str,
        risk_score: float,
    ) -> Dict[str, Any]:
        if minute < 58:
            return self._downgrade("OBSERVACION", "ANALYST_UNDER_TOO_EARLY")

        if context_state in {"CALIENTE", "MUY_CALIENTE"}:
            return self._reject("ANALYST_UNDER_CONTEXT_TOO_HOT")

        if pressure > 22:
            return self._reject("ANALYST_UNDER_PRESSURE_TOO_HIGH")

        if rhythm > 16:
            return self._downgrade("OBSERVACION", "ANALYST_UNDER_RHYTHM_TOO_HIGH")

        if goal_probability > 55:
            return self._reject("ANALYST_UNDER_GOAL_PROB_TOO_HIGH")

        if rank == "OPERABLE":
            if (
                ai_score >= 60
                and under_probability >= 64
                and goal_probability <= 50
                and pressure <= 18
                and rhythm <= 14
                and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
                and data_quality in {"MEDIUM", "HIGH"}
                and risk_score <= 6.5
            ):
                return self._approve("ANALYST_UNDER_OPERABLE_OK")

            return self._downgrade("OBSERVACION", "ANALYST_UNDER_OPERABLE_WEAK")

        if rank == "BUENA":
            if (
                ai_score >= 62
                and under_probability >= 66
                and goal_probability <= 48
                and pressure <= 17
                and rhythm <= 13
                and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
                and data_quality in {"MEDIUM", "HIGH"}
                and risk_score <= 6.3
            ):
                return self._approve("ANALYST_UNDER_GOOD_OK")

            return self._downgrade("OPERABLE", "ANALYST_UNDER_GOOD_DOWNGRADED")

        if rank == "FUERTE":
            if (
                ai_score >= 68
                and under_probability >= 70
                and goal_probability <= 45
                and pressure <= 15
                and rhythm <= 11
                and context_state in {"CONTROLADO", "FRIO", "MUERTO"}
                and data_quality == "HIGH"
                and risk_score <= 6.0
            ):
                return self._approve("ANALYST_UNDER_STRONG_OK")

            return self._downgrade("BUENA", "ANALYST_UNDER_STRONG_DOWNGRADED")

        if rank == "PREMIUM":
            if (
                ai_score >= 74
                and under_probability >= 74
                and goal_probability <= 42
                and pressure <= 13
                and rhythm <= 10
                and context_state in {"CONTROLADO", "FRIO", "MUERTO"}
                and data_quality == "HIGH"
                and risk_score <= 5.8
            ):
                return self._approve("ANALYST_UNDER_PREMIUM_OK")

            return self._downgrade("FUERTE", "ANALYST_UNDER_PREMIUM_DOWNGRADED")

        return self._reject("ANALYST_UNDER_NOT_VALID")

    def _approve(self, reason: str) -> Dict[str, Any]:
        return {
            "approved": True,
            "action": "APPROVE",
            "rank": None,
            "reason": reason,
        }

    def _downgrade(self, rank: str, reason: str) -> Dict[str, Any]:
        return {
            "approved": rank not in {"OBSERVACION", "NO_BET"},
            "action": "DOWNGRADE",
            "rank": rank,
            "reason": reason,
        }

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "approved": False,
            "action": "REJECT",
            "rank": "NO_BET",
            "reason": reason,
        }

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
