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


class MomentumTrendAI:
    """
    V17.5 - MomentumTrendAI

    Rol:
    EVIDENCE_ONLY

    Propósito:
    Interpretar tendencia live del partido:
    - presión subiendo;
    - presión bajando;
    - partido estable;
    - partido enfriándose;
    - partido caótico;
    - reacción de un equipo;
    - datos débiles.

    No decide.
    No publica.
    No modifica official_*.
    """

    VERSION = "V17.5_MOMENTUM_TREND_AI_1.0"

    def __init__(self) -> None:
        self._memory: Dict[str, Dict[str, Any]] = {}

    def evaluate(
        self,
        *,
        match: Dict[str, Any],
        clock: Optional[Dict[str, Any]] = None,
        data_truth: Optional[Dict[str, Any]] = None,
        match_phase: Optional[Dict[str, Any]] = None,
        tactical: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clock = clock or {}
        data_truth = data_truth or {}
        match_phase = match_phase or {}
        tactical = tactical or {}

        fixture_id = str(
            first_value(
                match.get("fixture_id"),
                match.get("match_id"),
                match.get("id"),
                default="UNKNOWN_FIXTURE",
            )
        )

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

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        scoreline = f"{home_score}-{away_score}"

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
            return self._data_weak(
                fixture_id=fixture_id,
                minute=minute,
                scoreline=scoreline,
                reason="Los datos live no son interpretables; no se calcula momentum real.",
            )

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
                match.get("match_maturity_live_volume_score"),
                default=0,
            ),
            0.0,
        )

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

        home_pressure = safe_float(
            first_value(
                match.get("home_pressure_score"),
                match.get("pressure_home"),
                match.get("home_dangerous_attacks"),
                match.get("dangerous_attacks_home"),
                default=0,
            ),
            0.0,
        )
        away_pressure = safe_float(
            first_value(
                match.get("away_pressure_score"),
                match.get("pressure_away"),
                match.get("away_dangerous_attacks"),
                match.get("dangerous_attacks_away"),
                default=0,
            ),
            0.0,
        )

        previous = self._memory.get(fixture_id, {})
        first_seen = not bool(previous)

        previous_pressure = safe_float(previous.get("pressure_score"), pressure_score)
        previous_rhythm = safe_float(previous.get("rhythm_score"), rhythm_score)
        previous_volume = safe_float(previous.get("offensive_volume_score"), offensive_volume_score)
        previous_shots = safe_int(previous.get("shots"), shots)
        previous_sot = safe_int(previous.get("shots_on_target"), shots_on_target)
        previous_corners = safe_int(previous.get("corners"), corners)
        previous_dangerous = safe_int(previous.get("dangerous_attacks"), dangerous_attacks)
        previous_xg = safe_float(previous.get("xg"), xg)
        previous_scoreline = previous.get("scoreline", scoreline)

        pressure_delta = pressure_score - previous_pressure
        rhythm_delta = rhythm_score - previous_rhythm
        volume_delta = offensive_volume_score - previous_volume
        shots_delta = shots - previous_shots
        sot_delta = shots_on_target - previous_sot
        corners_delta = corners - previous_corners
        dangerous_delta = dangerous_attacks - previous_dangerous
        xg_delta = xg - previous_xg

        support_points: List[str] = []
        warnings: List[str] = []

        if first_seen:
            direction = "STABLE"
            quality = "INITIAL_SAMPLE"
            reason = "Primera lectura de momentum; se necesita otro ciclo para confirmar tendencia."
            sustainability = "UNKNOWN"
            shift_detected = False
        else:
            activity_jump = (
                shots_delta >= 3
                or sot_delta >= 2
                or corners_delta >= 3
                or dangerous_delta >= 12
                or xg_delta >= 0.30
            )

            if pressure_delta >= 18 and rhythm_delta >= 12 and activity_jump:
                direction = "CHAOTIC" if shots_delta >= 5 or dangerous_delta >= 20 else self._owner_rising(home_pressure, away_pressure)
                quality = "REAL_MOMENTUM"
                sustainability = "GROWING"
                shift_detected = True
                reason = "La presión y el ritmo suben con actividad ofensiva real."
                support_points.append("Ritmo y presión suben respecto al ciclo anterior.")
            elif pressure_delta <= -18 and rhythm_delta <= -14:
                direction = "COOLING_DOWN"
                quality = "COOLING"
                sustainability = "FALLING"
                shift_detected = True
                reason = "El partido pierde ritmo y presión respecto al ciclo anterior."
                warnings.append("Posible enfriamiento del partido.")
            elif volume_delta <= -18 and shots_delta <= 0 and sot_delta <= 0:
                direction = "FALLING"
                quality = "LOWERING_VOLUME"
                sustainability = "FALLING"
                shift_detected = True
                reason = "El volumen ofensivo cae sin nueva producción de remates."
            elif pressure_delta >= 12 and rhythm_delta <= -5:
                direction = "REVERSING"
                quality = "UNSTABLE"
                sustainability = "UNCLEAR"
                shift_detected = True
                reason = "La presión sube, pero el ritmo no acompaña; posible reacción incompleta."
                warnings.append("Momentum todavía no confirmado por ritmo.")
            elif rhythm_score >= 72 and pressure_score >= 68 and offensive_volume_score >= 62:
                direction = "CHAOTIC"
                quality = "HIGH_INTENSITY"
                sustainability = "ACTIVE"
                shift_detected = False
                reason = "El partido mantiene intensidad alta y riesgo de ruptura."
            else:
                direction = "STABLE"
                quality = "CONTROLLED"
                sustainability = "STABLE"
                shift_detected = False
                reason = "No hay cambio de momentum suficientemente fuerte."

        if direction in {"HOME_RISING", "AWAY_RISING"}:
            support_points.append(f"Momentum favorece a {direction.replace('_RISING', '')}.")
        if shots_delta > 0:
            support_points.append(f"Remates aumentaron +{shots_delta}.")
        if sot_delta > 0:
            support_points.append(f"Remates al arco aumentaron +{sot_delta}.")
        if corners_delta > 0:
            support_points.append(f"Córners aumentaron +{corners_delta}.")
        if dangerous_delta > 0:
            support_points.append(f"Ataques peligrosos aumentaron +{dangerous_delta}.")
        if xg_delta > 0.05:
            support_points.append(f"xG aumentó +{xg_delta:.2f}.")

        if match_phase.get("phase_reset_required"):
            warnings.append("MatchPhaseAI detectó cambio de fase; no arrastrar lectura anterior sin revalidación.")

        self._memory[fixture_id] = {
            "minute": minute,
            "scoreline": scoreline,
            "pressure_score": pressure_score,
            "rhythm_score": rhythm_score,
            "offensive_volume_score": offensive_volume_score,
            "shots": shots,
            "shots_on_target": shots_on_target,
            "corners": corners,
            "dangerous_attacks": dangerous_attacks,
            "xg": xg,
        }

        return {
            "momentum_trend_role": "EVIDENCE_ONLY",
            "momentum_trend_version": self.VERSION,
            "momentum_direction": direction,
            "momentum_owner": self._owner(home_pressure, away_pressure),
            "momentum_quality": quality,
            "momentum_sustainability": sustainability,
            "momentum_shift_detected": shift_detected,
            "momentum_reason": reason,
            "momentum_support_points": unique(support_points),
            "momentum_warnings": unique(warnings),
            "momentum_context": {
                "fixture_id": fixture_id,
                "minute": minute,
                "scoreline": scoreline,
                "previous_scoreline": previous_scoreline,
                "pressure_score": round(pressure_score, 2),
                "rhythm_score": round(rhythm_score, 2),
                "offensive_volume_score": round(offensive_volume_score, 2),
                "pressure_delta": round(pressure_delta, 2),
                "rhythm_delta": round(rhythm_delta, 2),
                "volume_delta": round(volume_delta, 2),
                "shots_delta": shots_delta,
                "shots_on_target_delta": sot_delta,
                "corners_delta": corners_delta,
                "dangerous_attacks_delta": dangerous_delta,
                "xg_delta": round(xg_delta, 2),
            },
        }

    def _owner(self, home_pressure: float, away_pressure: float) -> str:
        if home_pressure >= away_pressure + 8:
            return "HOME"
        if away_pressure >= home_pressure + 8:
            return "AWAY"
        return "NONE"

    def _owner_rising(self, home_pressure: float, away_pressure: float) -> str:
        owner = self._owner(home_pressure, away_pressure)
        if owner == "HOME":
            return "HOME_RISING"
        if owner == "AWAY":
            return "AWAY_RISING"
        return "CHAOTIC"

    def _data_weak(self, *, fixture_id: str, minute: int, scoreline: str, reason: str) -> Dict[str, Any]:
        return {
            "momentum_trend_role": "EVIDENCE_ONLY",
            "momentum_trend_version": self.VERSION,
            "momentum_direction": "DATA_WEAK",
            "momentum_owner": "NONE",
            "momentum_quality": "DATA_WEAK",
            "momentum_sustainability": "UNKNOWN",
            "momentum_shift_detected": False,
            "momentum_reason": reason,
            "momentum_support_points": [],
            "momentum_warnings": ["Datos insuficientes para confirmar momentum real."],
            "momentum_context": {
                "fixture_id": fixture_id,
                "minute": minute,
                "scoreline": scoreline,
            },
        }
