from __future__ import annotations

from typing import Any, Dict, List


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


class MarketAI:
    """
    Inteligencia de mercado V17.

    Decide orientación:
    - OVER
    - UNDER
    - OBSERVE
    - NO_BET

    No decide ENTER por sí sola.

    Criterio V17:
    - OVER no debe ser excesivamente castigado si hay presión, ritmo y profundidad real.
    - UNDER debe ser más conservador, porque un solo gol tardío rompe la lectura.
    - OBSERVE aparece cuando hay señal interesante, pero falta confirmación.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = safe_int(
            match.get("api_minute")
            or match.get("display_minute")
            or match.get("minute"),
            0,
        )

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score

        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        corners = safe_float(match.get("corners"), 0.0)
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)

        data_quality = str(
            match.get("data_quality")
            or match.get("calidad_datos")
            or "LOW"
        ).upper()

        over_context_score = safe_float(context.get("over_context_score"), 0.0)
        under_context_score = safe_float(context.get("under_context_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        pressure_score = safe_float(tactical.get("pressure_score"), 0.0)
        rhythm_score = safe_float(tactical.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(tactical.get("goal_need_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)

        market_warnings: List[str] = []
        market_strengths: List[str] = []

        offensive_volume_score = self._offensive_volume_score(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
        )

        data_quality_bonus = self._data_quality_bonus(data_quality)

        late_phase = minute >= 75
        very_late_phase = minute >= 85
        early_phase = minute < 20

        # OVER se apoya más en volumen ofensivo, presión, ritmo y necesidad real de gol.
        over_score = (
            over_context_score * 0.26
            + tactical_score * 0.18
            + offensive_depth_score * 0.17
            + pressure_score * 0.12
            + rhythm_score * 0.10
            + goal_need_score * 0.08
            + recent_attack_proxy * 0.05
            + offensive_volume_score * 0.04
            + data_quality_bonus
        )

        # UNDER se mantiene útil, pero no debe entrar demasiado fácil.
        under_score = (
            under_context_score * 0.30
            + score_hold_probability * 0.25
            + under_transition_score * 0.20
            + max(0, 100 - tactical_score) * 0.08
            + max(0, 100 - pressure_score) * 0.07
            + max(0, 100 - rhythm_score) * 0.05
            + max(0, 100 - offensive_volume_score) * 0.05
        )

        # ==========================================================
        # Ajustes a favor de OVER cuando hay ataque real
        # ==========================================================

        if offensive_volume_score >= 70:
            over_score += 8
            under_score -= 6
            market_strengths.append("REAL_OFFENSIVE_VOLUME_SUPPORTS_OVER")

        if shots_on_target >= 4:
            over_score += 6
            under_score -= 4
            market_strengths.append("SHOTS_ON_TARGET_SUPPORTS_OVER")

        if shots >= 14:
            over_score += 5
            under_score -= 3
            market_strengths.append("TOTAL_SHOTS_SUPPORTS_OVER")

        if corners >= 6:
            over_score += 4
            market_strengths.append("CORNERS_SUPPORT_OVER_PRESSURE")

        if xg >= 1.20:
            over_score += 7
            under_score -= 5
            market_strengths.append("XG_SUPPORTS_OVER")

        if dangerous_attacks >= 25:
            over_score += 4
            market_strengths.append("DANGEROUS_ATTACKS_SUPPORT_OVER")

        if goal_need_score >= 70 and minute <= 82:
            over_score += 6
            under_score -= 4
            market_strengths.append("GOAL_NEED_SUPPORTS_OVER")

        if pressure_score >= 70 and rhythm_score >= 65:
            over_score += 6
            under_score -= 4
            market_strengths.append("PRESSURE_AND_RHYTHM_SUPPORT_OVER")

        # ==========================================================
        # Ajustes conservadores para UNDER
        # ==========================================================

        if under_transition_score >= 75:
            market_strengths.append("UNDER_TRANSITION_SUPPORTS_UNDER")

        if score_hold_probability >= 75:
            market_strengths.append("SCORE_HOLD_SUPPORTS_UNDER")

        if offensive_volume_score <= 35 and pressure_score <= 45 and rhythm_score <= 45:
            under_score += 7
            market_strengths.append("LOW_VOLUME_SUPPORTS_UNDER")

        if minute >= 75 and offensive_volume_score <= 40:
            under_score += 6
            over_score -= 5
            market_strengths.append("LATE_LOW_VOLUME_SUPPORTS_UNDER")

        # ==========================================================
        # Advertencias y castigos
        # ==========================================================

        if false_pressure_risk >= 70:
            over_score -= 14
            market_warnings.append("OVER_FALSE_PRESSURE")

        elif false_pressure_risk >= 55:
            over_score -= 7
            market_warnings.append("OVER_MODERATE_FALSE_PRESSURE")

        if score_hold_probability >= 80 and offensive_volume_score < 55:
            over_score -= 10
            market_warnings.append("SCORE_HOLD_AGAINST_OVER")

        if under_transition_score >= 80 and offensive_volume_score < 55:
            over_score -= 8
            market_warnings.append("UNDER_TRANSITION_AGAINST_OVER")

        if very_late_phase and recent_attack_proxy < 55 and offensive_volume_score < 55:
            over_score -= 10
            market_warnings.append("VERY_LATE_WITHOUT_REACTIVATION")

        elif late_phase and recent_attack_proxy < 45 and offensive_volume_score < 45:
            over_score -= 6
            market_warnings.append("LATE_WITHOUT_REACTIVATION")

        if early_phase:
            over_score -= 3
            under_score -= 3
            market_warnings.append("EARLY_MATCH_LOW_DECISION_SECURITY")

        if data_quality == "LOW":
            over_score -= 4
            under_score -= 6
            market_warnings.append("LOW_DATA_QUALITY_MARKET_CAUTION")

        # UNDER es delicado si el partido tiene volumen ofensivo real.
        if offensive_volume_score >= 60:
            under_score -= 8
            market_warnings.append("UNDER_RISK_WITH_OFFENSIVE_VOLUME")

        if shots_on_target >= 3 and minute < 80:
            under_score -= 5
            market_warnings.append("UNDER_RISK_WITH_SOT")

        if xg >= 1.0:
            under_score -= 5
            market_warnings.append("UNDER_RISK_WITH_XG")

        if total_goals >= 3 and minute < 80:
            under_score -= 8
            market_warnings.append("UNDER_RISK_OPEN_SCORELINE")

        # ==========================================================
        # Fortalezas generales
        # ==========================================================

        if offensive_depth_score >= 70:
            market_strengths.append("DEPTH_SUPPORTS_OVER")

        if tactical_score >= 70:
            market_strengths.append("TACTICAL_SUPPORTS_OVER")

        if pressure_score >= 70:
            market_strengths.append("PRESSURE_SUPPORTS_OVER")

        if rhythm_score >= 70:
            market_strengths.append("RHYTHM_SUPPORTS_OVER")

        over_score = clamp(over_score)
        under_score = clamp(under_score)

        score_gap = abs(over_score - under_score)
        market_confidence = max(over_score, under_score)

        # ==========================================================
        # Decisión de mercado
        # ==========================================================
        # OVER baja un poco su umbral para no quedar demasiado estricto.
        # UNDER sube su exigencia porque es más frágil ante un gol aislado.

        if (
            over_score >= 66
            and over_score >= under_score + 6
            and offensive_volume_score >= 45
        ):
            market = "OVER"
            category = "OVER_CANDIDATE"
            market_status = "OVER_EDGE"

        elif (
            under_score >= 72
            and under_score >= over_score + 9
            and offensive_volume_score <= 58
            and false_pressure_risk < 70
        ):
            market = "UNDER"
            category = "UNDER_CANDIDATE"
            market_status = "UNDER_EDGE"

        elif market_confidence >= 58:
            market = "OBSERVE"
            category = "OBSERVE"
            market_status = "MIXED_MARKET"

            if score_gap < 8:
                market_warnings.append("MARKET_EDGE_NOT_CLEAR")

        else:
            market = "NO_BET"
            category = "NO_BET"
            market_status = "NO_MARKET_EDGE"

        return {
            "market_status": market_status,
            "suggested_market": market,
            "market": market,
            "market_direction": market if market in {"OVER", "UNDER"} else "OTHER",
            "market_category": category,
            "over_score": round(over_score, 2),
            "under_score": round(under_score, 2),
            "market_confidence": round(market_confidence, 2),
            "market_gap": round(score_gap, 2),
            "offensive_volume_score": round(offensive_volume_score, 2),
            "market_strengths": market_strengths,
            "market_warnings": market_warnings,
            "market_reading": self._build_market_reading(
                market=market,
                over_score=over_score,
                under_score=under_score,
                offensive_volume_score=offensive_volume_score,
                minute=minute,
            ),
        }

    def _offensive_volume_score(
        self,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
    ) -> float:
        """
        Resume el volumen ofensivo real del partido.
        No depende de una sola métrica.
        """

        shots_score = min(100.0, shots * 4.5)
        sot_score = min(100.0, shots_on_target * 16.0)
        corner_score = min(100.0, corners * 10.0)
        xg_score = min(100.0, xg * 55.0)
        danger_score = min(100.0, dangerous_attacks * 2.4)

        return clamp(
            shots_score * 0.25
            + sot_score * 0.25
            + corner_score * 0.15
            + xg_score * 0.20
            + danger_score * 0.15
        )

    def _data_quality_bonus(self, data_quality: str) -> float:
        if data_quality == "HIGH":
            return 4.0

        if data_quality == "MEDIUM":
            return 1.5

        return -2.0

    def _build_market_reading(
        self,
        market: str,
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        minute: int,
    ) -> str:
        if market == "OVER":
            return (
                f"Lectura OVER con volumen ofensivo {offensive_volume_score:.0f}/100. "
                f"OVER {over_score:.0f} supera a UNDER {under_score:.0f}."
            )

        if market == "UNDER":
            return (
                f"Lectura UNDER conservadora. UNDER {under_score:.0f} supera a OVER {over_score:.0f}, "
                f"con volumen ofensivo {offensive_volume_score:.0f}/100."
            )

        if market == "OBSERVE":
            return (
                f"Mercado en observación. OVER {over_score:.0f}, UNDER {under_score:.0f}, "
                f"volumen ofensivo {offensive_volume_score:.0f}/100, minuto {minute}."
            )

        return (
            f"Sin ventaja clara de mercado. OVER {over_score:.0f}, UNDER {under_score:.0f}, "
            f"volumen ofensivo {offensive_volume_score:.0f}/100."
        )
