from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple


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


def safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí"}
    return bool(value)


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


class MatchPhaseAI:
    """
    V17.5 - MatchPhaseAI

    Rol:
    EVIDENCE_ONLY

    Propósito:
    Detectar cambios de fase del partido para que el sistema no arrastre lecturas antiguas
    después de eventos fuertes: goles, rojas, penales, segundo tiempo, minuto 60/75/85,
    cambios bruscos de ritmo o fases técnicas por datos no interpretables.

    No decide.
    No publica.
    No modifica official_*.
    No bloquea señales.
    """

    VERSION = "V17.5_MATCH_PHASE_AI_1.0"

    def __init__(self) -> None:
        self._memory: Dict[str, Dict[str, Any]] = {}

    def evaluate(
        self,
        *,
        match: Dict[str, Any],
        clock: Optional[Dict[str, Any]] = None,
        data_truth: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clock = clock or {}
        data_truth = data_truth or {}

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
        score_state = f"{home_score}-{away_score}"
        total_goals = home_score + away_score

        red_cards = safe_int(
            first_value(
                match.get("red_cards"),
                match.get("total_red_cards"),
                default=0,
            ),
            0,
        )

        home_red_cards = safe_int(
            first_value(
                match.get("home_red_cards"),
                match.get("red_cards_home"),
                default=0,
            ),
            0,
        )
        away_red_cards = safe_int(
            first_value(
                match.get("away_red_cards"),
                match.get("red_cards_away"),
                default=0,
            ),
            0,
        )
        total_red_cards = max(red_cards, home_red_cards + away_red_cards)

        total_shots = safe_int(
            first_value(match.get("total_shots"), match.get("shots"), default=0),
            0,
        )
        total_shots_on = safe_int(
            first_value(
                match.get("total_shots_on"),
                match.get("shots_on_target"),
                default=0,
            ),
            0,
        )
        total_corners = safe_int(
            first_value(match.get("total_corners"), match.get("corners"), default=0),
            0,
        )
        total_dangerous_attacks = safe_int(
            first_value(
                match.get("total_dangerous_attacks"),
                match.get("dangerous_attacks"),
                default=0,
            ),
            0,
        )
        total_xg = safe_float(
            first_value(match.get("total_xg"), match.get("xg"), match.get("xG"), default=0),
            0.0,
        )

        pressure_score = safe_float(
            first_value(
                match.get("pressure_score"),
                match.get("pressure"),
                match.get("football_pressure"),
                default=0,
            ),
            0.0,
        )
        rhythm_score = safe_float(
            first_value(
                match.get("rhythm_score"),
                match.get("volume_score"),
                match.get("match_maturity_live_volume_score"),
                default=0,
            ),
            0.0,
        )

        clock_status = upper(clock.get("clock_status") or match.get("clock_status"))
        data_truth_state = upper(data_truth.get("data_truth_state"))
        data_truth_can_interpret = data_truth.get("data_truth_can_interpret")
        if data_truth_can_interpret is None:
            data_truth_can_interpret = data_truth_state not in {
                "NO_INTERPRETABLE_DATA",
                "DATA_INSUFFICIENT",
                "WAIT_REAL_STATS",
                "STALE_CACHE",
            }

        previous = self._memory.get(fixture_id, {})

        triggers: List[str] = []
        support_points: List[str] = []
        warnings: List[str] = []

        previous_score = previous.get("score_state")
        previous_total_goals = safe_int(previous.get("total_goals"), total_goals)
        previous_red_cards = safe_int(previous.get("total_red_cards"), total_red_cards)
        previous_minute = safe_int(previous.get("minute"), minute)

        previous_pressure = safe_float(previous.get("pressure_score"), pressure_score)
        previous_rhythm = safe_float(previous.get("rhythm_score"), rhythm_score)
        previous_shots = safe_int(previous.get("total_shots"), total_shots)
        previous_sot = safe_int(previous.get("total_shots_on"), total_shots_on)
        previous_corners = safe_int(previous.get("total_corners"), total_corners)
        previous_dangerous = safe_int(
            previous.get("total_dangerous_attacks"),
            total_dangerous_attacks,
        )
        previous_xg = safe_float(previous.get("total_xg"), total_xg)

        first_seen = not bool(previous)

        # ------------------------------------------------------------
        # Eventos fuertes
        # ------------------------------------------------------------
        if not first_seen and previous_score and previous_score != score_state:
            if total_goals > previous_total_goals:
                triggers.append("GOAL")
                support_points.append(f"Marcador cambió de {previous_score} a {score_state}.")
            else:
                triggers.append("SCORE_CORRECTION")
                warnings.append(f"Marcador cambió sin aumento de goles: {previous_score} -> {score_state}.")

        if not first_seen and total_red_cards > previous_red_cards:
            triggers.append("RED_CARD")
            support_points.append("Aumentó el total de tarjetas rojas.")

        if self._has_penalty_event(match):
            triggers.append("PENALTY")
            support_points.append("Se detectó evento de penal en la fuente live.")

        # ------------------------------------------------------------
        # Tramos críticos
        # ------------------------------------------------------------
        critical_minute_trigger = self._critical_minute_trigger(
            minute=minute,
            previous_minute=previous_minute,
            first_seen=first_seen,
        )
        if critical_minute_trigger:
            triggers.append(critical_minute_trigger)
            support_points.append(f"El partido entró en tramo crítico: minuto {minute}.")

        # ------------------------------------------------------------
        # Cambio fuerte de ritmo solo si hay datos interpretables
        # ------------------------------------------------------------
        if not first_seen and data_truth_can_interpret:
            rhythm_trigger, rhythm_note = self._detect_rhythm_shift(
                pressure_score=pressure_score,
                rhythm_score=rhythm_score,
                total_shots=total_shots,
                total_shots_on=total_shots_on,
                total_corners=total_corners,
                total_dangerous_attacks=total_dangerous_attacks,
                total_xg=total_xg,
                previous_pressure=previous_pressure,
                previous_rhythm=previous_rhythm,
                previous_shots=previous_shots,
                previous_sot=previous_sot,
                previous_corners=previous_corners,
                previous_dangerous=previous_dangerous,
                previous_xg=previous_xg,
            )
            if rhythm_trigger:
                triggers.append(rhythm_trigger)
                support_points.append(rhythm_note)

        # ------------------------------------------------------------
        # Fase técnica: reloj/datos
        # ------------------------------------------------------------
        if clock_status in {"BLOCKED_CLOCK", "CLOCK_WARNING"}:
            triggers.append("TECHNICAL_CLOCK_PHASE")
            warnings.append("El reloj no está plenamente confirmado.")

        if data_truth_state in {
            "NO_INTERPRETABLE_DATA",
            "DATA_INSUFFICIENT",
            "WAIT_REAL_STATS",
            "STALE_CACHE",
        } or not data_truth_can_interpret:
            triggers.append("TECHNICAL_DATA_PHASE")
            warnings.append("Los datos live no son plenamente interpretables.")

        triggers = unique(triggers)
        support_points = unique(support_points)
        warnings = unique(warnings)

        phase_type = self._phase_type(
            triggers=triggers,
            minute=minute,
            total_goals=total_goals,
            data_truth_can_interpret=bool(data_truth_can_interpret),
        )

        primary_trigger = triggers[0] if triggers else "NORMAL_SCAN"
        phase_reset_required = primary_trigger in {
            "GOAL",
            "RED_CARD",
            "PENALTY",
            "SECOND_HALF_START",
            "MINUTE_60",
            "MINUTE_75",
            "MINUTE_85",
            "RHYTHM_ACCELERATION",
            "RHYTHM_COLLAPSE",
            "TECHNICAL_DATA_PHASE",
            "TECHNICAL_CLOCK_PHASE",
        }

        previous_phase_invalidated = primary_trigger in {
            "GOAL",
            "RED_CARD",
            "PENALTY",
            "RHYTHM_ACCELERATION",
            "RHYTHM_COLLAPSE",
        }

        phase_reason = self._phase_reason(
            phase_type=phase_type,
            primary_trigger=primary_trigger,
            score_state=score_state,
            minute=minute,
        )

        phase_started_minute = minute if phase_reset_required or first_seen else safe_int(
            previous.get("match_phase_started_minute"),
            minute,
        )

        phase_id = self._phase_id(
            fixture_id=fixture_id,
            phase_type=phase_type,
            trigger=primary_trigger,
            score_state=score_state,
            started_minute=phase_started_minute,
        )

        phase_memory_note = self._phase_memory_note(
            phase_type=phase_type,
            trigger=primary_trigger,
            previous_score=previous_score,
            score_state=score_state,
            previous_phase_invalidated=previous_phase_invalidated,
        )

        snapshot = {
            "fixture_id": fixture_id,
            "minute": minute,
            "score_state": score_state,
            "total_goals": total_goals,
            "total_red_cards": total_red_cards,
            "pressure_score": pressure_score,
            "rhythm_score": rhythm_score,
            "total_shots": total_shots,
            "total_shots_on": total_shots_on,
            "total_corners": total_corners,
            "total_dangerous_attacks": total_dangerous_attacks,
            "total_xg": total_xg,
            "match_phase_id": phase_id,
            "match_phase_type": phase_type,
            "match_phase_started_minute": phase_started_minute,
        }
        self._memory[fixture_id] = snapshot

        return {
            "match_phase_role": "EVIDENCE_ONLY",
            "match_phase_version": self.VERSION,
            "match_phase_id": phase_id,
            "match_phase_type": phase_type,
            "match_phase_trigger": primary_trigger,
            "match_phase_triggers": triggers,
            "match_phase_started_minute": phase_started_minute,
            "previous_phase_invalidated": previous_phase_invalidated,
            "phase_reset_required": phase_reset_required,
            "phase_reason": phase_reason,
            "phase_memory_note": phase_memory_note,
            "phase_warnings": warnings,
            "phase_support_points": support_points,
            "match_phase_context": {
                "fixture_id": fixture_id,
                "minute": minute,
                "previous_minute": previous_minute,
                "score_state": score_state,
                "previous_score_state": previous_score,
                "total_goals": total_goals,
                "previous_total_goals": previous_total_goals,
                "total_red_cards": total_red_cards,
                "previous_total_red_cards": previous_red_cards,
                "clock_status": clock_status,
                "data_truth_state": data_truth_state,
                "data_truth_can_interpret": bool(data_truth_can_interpret),
            },
        }

    def _critical_minute_trigger(
        self,
        *,
        minute: int,
        previous_minute: int,
        first_seen: bool,
    ) -> str:
        if minute <= 0:
            return ""

        windows = [
            (46, 50, "SECOND_HALF_START"),
            (60, 64, "MINUTE_60"),
            (75, 79, "MINUTE_75"),
            (85, 90, "MINUTE_85"),
        ]

        for start, end, label in windows:
            if start <= minute <= end:
                if first_seen or previous_minute < start:
                    return label

        return ""

    def _detect_rhythm_shift(
        self,
        *,
        pressure_score: float,
        rhythm_score: float,
        total_shots: int,
        total_shots_on: int,
        total_corners: int,
        total_dangerous_attacks: int,
        total_xg: float,
        previous_pressure: float,
        previous_rhythm: float,
        previous_shots: int,
        previous_sot: int,
        previous_corners: int,
        previous_dangerous: int,
        previous_xg: float,
    ) -> Tuple[str, str]:
        pressure_delta = pressure_score - previous_pressure
        rhythm_delta = rhythm_score - previous_rhythm
        shots_delta = total_shots - previous_shots
        sot_delta = total_shots_on - previous_sot
        corners_delta = total_corners - previous_corners
        dangerous_delta = total_dangerous_attacks - previous_dangerous
        xg_delta = total_xg - previous_xg

        activity_jump = (
            shots_delta >= 3
            or sot_delta >= 2
            or corners_delta >= 3
            or dangerous_delta >= 12
            or xg_delta >= 0.35
        )

        if pressure_delta >= 18 and rhythm_delta >= 14 and activity_jump:
            return (
                "RHYTHM_ACCELERATION",
                "Subida fuerte de ritmo/presión acompañada por actividad ofensiva real.",
            )

        if pressure_delta <= -22 and rhythm_delta <= -18:
            return (
                "RHYTHM_COLLAPSE",
                "Caída fuerte de ritmo/presión respecto al tramo anterior.",
            )

        return "", ""

    def _has_penalty_event(self, match: Dict[str, Any]) -> bool:
        raw_events = match.get("events") or match.get("fixture_events") or []
        if not isinstance(raw_events, list):
            return False

        for event in raw_events:
            if not isinstance(event, dict):
                continue

            event_type = upper(
                first_value(
                    event.get("type"),
                    event.get("detail"),
                    event.get("comments"),
                    event.get("description"),
                    default="",
                )
            )

            if "PENAL" in event_type or "PENALTY" in event_type:
                return True

        return False

    def _phase_type(
        self,
        *,
        triggers: List[str],
        minute: int,
        total_goals: int,
        data_truth_can_interpret: bool,
    ) -> str:
        trigger_set = set(triggers)

        if "TECHNICAL_DATA_PHASE" in trigger_set or "TECHNICAL_CLOCK_PHASE" in trigger_set:
            return "TECHNICAL_PHASE"

        if "GOAL" in trigger_set:
            return "POST_GOAL_REACTION"

        if "RED_CARD" in trigger_set:
            return "RED_CARD_GAME_STATE"

        if "PENALTY" in trigger_set:
            return "PENALTY_PHASE"

        if "RHYTHM_ACCELERATION" in trigger_set:
            return "RHYTHM_ACCELERATION_PHASE"

        if "RHYTHM_COLLAPSE" in trigger_set:
            return "RHYTHM_COLLAPSE_PHASE"

        if "SECOND_HALF_START" in trigger_set:
            return "SECOND_HALF_OPENING"

        if "MINUTE_60" in trigger_set:
            return "TACTICAL_ADJUSTMENT_WINDOW"

        if "MINUTE_75" in trigger_set:
            return "LATE_VOLATILITY_WINDOW"

        if "MINUTE_85" in trigger_set:
            return "FINAL_STRETCH"

        if not data_truth_can_interpret:
            return "WAIT_REAL_DATA_PHASE"

        if minute < 15:
            return "EARLY_CONTEXT_BUILDING"

        if minute < 45:
            return "FIRST_HALF_INTERPRETATION"

        if minute < 60:
            return "SECOND_HALF_SETTLING"

        if minute < 75:
            return "SECOND_HALF_TACTICAL_WINDOW"

        if minute < 85:
            return "LATE_GAME_WINDOW"

        return "FINAL_GAME_STATE"

    def _phase_reason(
        self,
        *,
        phase_type: str,
        primary_trigger: str,
        score_state: str,
        minute: int,
    ) -> str:
        if primary_trigger == "GOAL":
            return f"El marcador cambió a {score_state}; la lectura anterior debe revalidarse."
        if primary_trigger == "RED_CARD":
            return "Una roja cambia el equilibrio táctico; la fase anterior pierde validez parcial."
        if primary_trigger == "PENALTY":
            return "Un penal detectado altera el riesgo inmediato del partido."
        if primary_trigger == "TECHNICAL_DATA_PHASE":
            return "La fase actual está limitada por datos insuficientes o no interpretables."
        if primary_trigger == "TECHNICAL_CLOCK_PHASE":
            return "La fase actual está limitada por reloj no confirmado."
        if primary_trigger in {"SECOND_HALF_START", "MINUTE_60", "MINUTE_75", "MINUTE_85"}:
            return f"El partido entra en una ventana crítica de interpretación: minuto {minute}."
        if primary_trigger == "RHYTHM_ACCELERATION":
            return "El ritmo ofensivo subió de forma brusca y requiere nueva lectura."
        if primary_trigger == "RHYTHM_COLLAPSE":
            return "El ritmo cayó de forma brusca y requiere nueva lectura."
        return f"Fase actual: {phase_type}."

    def _phase_memory_note(
        self,
        *,
        phase_type: str,
        trigger: str,
        previous_score: Any,
        score_state: str,
        previous_phase_invalidated: bool,
    ) -> str:
        if previous_phase_invalidated:
            return (
                f"Nueva fase por {trigger}. La lectura anterior"
                f"{f' con marcador {previous_score}' if previous_score else ''} debe tratarse como contexto histórico,"
                f" no como decisión vigente. Marcador actual: {score_state}."
            )

        return (
            f"Fase {phase_type}. La memoria previa se conserva como contexto,"
            " pero no debe reemplazar la lectura live actual."
        )

    def _phase_id(
        self,
        *,
        fixture_id: str,
        phase_type: str,
        trigger: str,
        score_state: str,
        started_minute: int,
    ) -> str:
        raw = f"{fixture_id}|{phase_type}|{trigger}|{score_state}|{started_minute}"
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
        return f"PHASE:{fixture_id}:{started_minute}:{digest}"
