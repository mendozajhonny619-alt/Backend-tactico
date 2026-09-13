from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def upper(value: Any) -> str:
    return str(value or "").strip().upper()


def first_value(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def unique(items: List[str]) -> List[str]:
    return list(dict.fromkeys([str(x) for x in items if x is not None and str(x).strip()]))


class PressureQualityAIV17:
    """
    V17.5 - PressureQualityAI

    Rol:
    EVIDENCE_ONLY

    Propósito:
    Diferenciar:
    - presión real;
    - presión falsa;
    - dominio estéril;
    - amenaza de transición;
    - ausencia de presión;
    - datos débiles.

    No decide.
    No publica.
    No modifica official_*.
    """

    VERSION = "V17.5_PRESSURE_QUALITY_AI_1.0"

    def evaluate(
        self,
        *,
        match: Dict[str, Any],
        clock: Optional[Dict[str, Any]] = None,
        data_truth: Optional[Dict[str, Any]] = None,
        match_phase: Optional[Dict[str, Any]] = None,
        momentum_trend: Optional[Dict[str, Any]] = None,
        tactical: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clock = clock or {}
        data_truth = data_truth or {}
        match_phase = match_phase or {}
        momentum_trend = momentum_trend or {}
        tactical = tactical or {}

        minute = safe_int(
            first_value(
                match.get("api_minute"),
                match.get("display_minute"),
                match.get("estimated_minute"),
                clock.get("api_minute"),
                default=0,
            ),
            0,
        )

        data_truth_state = upper(data_truth.get("data_truth_state"))
        data_truth_can_interpret = data_truth.get("data_truth_can_interpret")
        if data_truth_can_interpret is None:
            data_truth_can_interpret = data_truth_state not in {
                "NO_INTERPRETABLE_DATA",
                "DATA_INSUFFICIENT",
                "WAIT_REAL_STATS",
                "STALE_CACHE",
            }

        if not data_truth_can_interpret:
            return self._data_weak(minute=minute)

        shots = safe_int(first_value(match.get("total_shots"), match.get("shots"), default=0), 0)
        shots_on_target = safe_int(
            first_value(match.get("total_shots_on"), match.get("shots_on_target"), default=0),
            0,
        )
        corners = safe_int(first_value(match.get("total_corners"), match.get("corners"), default=0), 0)
        dangerous_attacks = safe_int(
            first_value(match.get("total_dangerous_attacks"), match.get("dangerous_attacks"), default=0),
            0,
        )
        xg = safe_float(first_value(match.get("total_xg"), match.get("xg"), match.get("xG"), default=0), 0.0)

        pressure_score = safe_float(
            first_value(
                tactical.get("pressure_score"),
                match.get("pressure_score"),
                match.get("pressure"),
                default=0,
            ),
            0.0,
        )
        rhythm_score = safe_float(
            first_value(
                tactical.get("rhythm_score"),
                match.get("rhythm_score"),
                match.get("volume_score"),
                default=0,
            ),
            0.0,
        )
        offensive_volume_score = safe_float(
            first_value(
                tactical.get("offensive_volume_score"),
                match.get("offensive_volume_score"),
                default=0,
            ),
            0.0,
        )

        home_dangerous = safe_float(
            first_value(
                match.get("home_dangerous_attacks"),
                match.get("dangerous_attacks_home"),
                match.get("attacks_home"),
                default=0,
            ),
            0.0,
        )
        away_dangerous = safe_float(
            first_value(
                match.get("away_dangerous_attacks"),
                match.get("dangerous_attacks_away"),
                match.get("attacks_away"),
                default=0,
            ),
            0.0,
        )
        home_shots_on = safe_float(
            first_value(match.get("home_shots_on_target"), match.get("sot_home"), default=0),
            0.0,
        )
        away_shots_on = safe_float(
            first_value(match.get("away_shots_on_target"), match.get("sot_away"), default=0),
            0.0,
        )

        support_points: List[str] = []
        warnings: List[str] = []

        pressure_owner = self._owner(
            home_value=home_dangerous + home_shots_on * 8,
            away_value=away_dangerous + away_shots_on * 8,
        )

        real_score = 0.0
        false_score = 0.0

        real_score += min(28.0, shots_on_target * 9.0)
        real_score += min(20.0, xg * 18.0)
        real_score += min(18.0, dangerous_attacks * 0.45)
        real_score += min(12.0, corners * 2.0)
        real_score += min(12.0, offensive_volume_score * 0.12)
        real_score += min(10.0, rhythm_score * 0.10)

        false_score += max(0.0, pressure_score - offensive_volume_score) * 0.45
        if pressure_score >= 65 and shots_on_target <= 1:
            false_score += 22
            warnings.append("Presión alta con pocos remates al arco.")
        if dangerous_attacks >= 35 and xg <= 0.35:
            false_score += 15
            warnings.append("Ataques peligrosos sin xG proporcional.")
        if corners >= 5 and shots_on_target <= 1:
            false_score += 10
            warnings.append("Córners sin remate claro al arco.")
        if shots >= 8 and shots_on_target <= 1:
            false_score += 12
            warnings.append("Volumen de remates con baja precisión.")

        real_score = max(0.0, min(100.0, real_score))
        false_score = max(0.0, min(100.0, false_score))

        sterile_dominance = (
            pressure_score >= 60
            and offensive_volume_score < 45
            and shots_on_target <= 1
            and xg < 0.45
        )

        transition_threat = (
            shots_on_target >= 2
            and xg >= 0.55
            and pressure_score < 55
            and dangerous_attacks < 35
        )

        if real_score >= 62 and real_score >= false_score + 15:
            pressure_type = "REAL_PRESSURE"
            reason = "La presión tiene remates, xG o ataques peligrosos suficientes para considerarse real."
            support_points.append("Amenaza ofensiva respaldada por métricas reales.")
        elif transition_threat:
            pressure_type = "TRANSITION_THREAT"
            reason = "Hay amenaza con pocas posesiones o ataques, pero con producción de calidad."
            support_points.append("Amenaza de transición detectada.")
        elif sterile_dominance:
            pressure_type = "STERILE_DOMINANCE"
            reason = "Existe dominio territorial, pero no se transforma en peligro real."
            warnings.append("Dominio estéril: no elevar confianza solo por presión.")
        elif false_score >= 55 and false_score >= real_score:
            pressure_type = "FALSE_PRESSURE"
            reason = "La presión parece inflada o poco productiva frente a la calidad de ocasiones."
            warnings.append("Presión falsa o poco profunda.")
        elif real_score < 30 and pressure_score < 45:
            pressure_type = "NO_PRESSURE"
            reason = "No hay evidencia suficiente de presión ofensiva relevante."
        else:
            pressure_type = "REAL_PRESSURE" if real_score >= false_score else "FALSE_PRESSURE"
            reason = "La presión es mixta; se clasifica por la relación entre amenaza real y presión falsa."

        if shots_on_target > 0:
            support_points.append(f"Remates al arco: {shots_on_target}.")
        if xg > 0:
            support_points.append(f"xG total: {xg:.2f}.")
        if dangerous_attacks > 0:
            support_points.append(f"Ataques peligrosos: {dangerous_attacks}.")
        if corners > 0:
            support_points.append(f"Córners: {corners}.")

        if momentum_trend.get("momentum_shift_detected"):
            support_points.append("MomentumTrendAI detectó cambio de tendencia.")
        if match_phase.get("phase_reset_required"):
            warnings.append("La presión debe revalidarse por cambio de fase del partido.")

        return {
            "pressure_quality_role": "EVIDENCE_ONLY",
            "pressure_quality_version": self.VERSION,
            "pressure_type": pressure_type,
            "pressure_owner": pressure_owner,
            "pressure_real_score": round(real_score, 2),
            "pressure_false_score": round(false_score, 2),
            "sterile_dominance_detected": sterile_dominance,
            "transition_threat_detected": transition_threat,
            "pressure_quality_reason": reason,
            "pressure_support_points": unique(support_points),
            "pressure_warnings": unique(warnings),
            "pressure_quality_context": {
                "minute": minute,
                "shots": shots,
                "shots_on_target": shots_on_target,
                "corners": corners,
                "dangerous_attacks": dangerous_attacks,
                "xg": round(xg, 2),
                "pressure_score": round(pressure_score, 2),
                "rhythm_score": round(rhythm_score, 2),
                "offensive_volume_score": round(offensive_volume_score, 2),
            },
        }

    def _owner(self, *, home_value: float, away_value: float) -> str:
        if home_value >= away_value + 8:
            return "HOME"
        if away_value >= home_value + 8:
            return "AWAY"
        return "NONE"

    def _data_weak(self, *, minute: int) -> Dict[str, Any]:
        return {
            "pressure_quality_role": "EVIDENCE_ONLY",
            "pressure_quality_version": self.VERSION,
            "pressure_type": "DATA_WEAK",
            "pressure_owner": "NONE",
            "pressure_real_score": 0,
            "pressure_false_score": 0,
            "sterile_dominance_detected": False,
            "transition_threat_detected": False,
            "pressure_quality_reason": "Datos insuficientes para clasificar la presión real del partido.",
            "pressure_support_points": [],
            "pressure_warnings": ["No se puede distinguir presión real de presión falsa sin datos live confiables."],
            "pressure_quality_context": {
                "minute": minute,
            },
        }
