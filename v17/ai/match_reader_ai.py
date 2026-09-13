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


def normalize_text(value: Any) -> str:
    return str(value or "").strip().upper()


def normalize_market(value: Any) -> str:
    text = normalize_text(value)

    if "OVER" in text or "MAS" in text or "MÁS" in text or "SOBRE" in text:
        return "OVER"

    if "UNDER" in text or "MENOS" in text or "BAJO" in text:
        return "UNDER"

    return "OTHER"


class MatchReaderAI:
    """
    Lector futbolístico integral V17.

    Esta capa intenta interpretar el partido como una historia viva,
    no solamente como suma de filtros.

    No decide apuesta final.
    No reemplaza a MarketAI, TacticalAI, RiskAI ni PanelDecisionAI.

    Su función es responder:
    - Qué está pasando realmente en el partido.
    - Si el partido está abierto, cerrado, roto o en transición.
    - Si la presión es real o puede ser falsa.
    - Si OVER o UNDER tiene más sentido futbolístico.
    - Si la lectura principal y la alternativa están bien diferenciadas.
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
        over_candidate: Dict[str, Any],
        league_volatility: Dict[str, Any],
        decision_explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = safe_int(
            clock.get("api_minute")
            or match.get("api_minute")
            or match.get("minute"),
            0,
        )

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score
        goal_gap = abs(home_score - away_score)

        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        corners = safe_float(match.get("corners"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        market_gap = over_score - under_score

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        pressure_score = safe_float(tactical.get("pressure_score") or context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(tactical.get("rhythm_score") or context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(tactical.get("goal_need_score") or context.get("goal_need_score"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)

        score_hold_probability = safe_float(
            market.get("score_hold_probability")
            or context.get("score_hold_probability"),
            0.0,
        )
        under_transition_score = safe_float(
            market.get("under_transition_score")
            or context.get("under_transition_score"),
            0.0,
        )

        risk_status = normalize_text(risk.get("risk_status"))
        clock_status = normalize_text(clock.get("clock_status"))
        data_status = normalize_text(data_quality.get("data_quality") or match.get("data_quality"))
        contradiction_status = normalize_text(contradiction.get("contradiction_status"))

        league_group = normalize_text(league_volatility.get("league_context_group"))
        league_phase = normalize_text(league_volatility.get("league_minute_phase"))
        league_warning = league_volatility.get("league_warning")

        candidate_level = normalize_text(decision_explanation.get("candidate_level"))
        majority_support = bool(decision_explanation.get("majority_support"))
        support_ratio = safe_float(decision_explanation.get("support_ratio"), 0.0)

        over_candidate_level = normalize_text(over_candidate.get("over_candidate_level"))
        over_candidate_active = bool(over_candidate.get("over_candidate_active"))
        over_support_ratio = safe_float(over_candidate.get("over_support_ratio"), 0.0)

        real_offensive_volume = self._real_offensive_volume(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
        )

        game_phase = self._game_phase(minute)

        game_state = self._game_state(
            minute=minute,
            total_goals=total_goals,
            goal_gap=goal_gap,
            real_offensive_volume=real_offensive_volume,
            over_score=over_score,
            under_score=under_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
            false_pressure_risk=false_pressure_risk,
        )

        dominant_reading = self._dominant_reading(
            game_state=game_state,
            over_score=over_score,
            under_score=under_score,
            market_gap=market_gap,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
            real_offensive_volume=real_offensive_volume,
            over_candidate_level=over_candidate_level,
            over_candidate_active=over_candidate_active,
            candidate_level=candidate_level,
            majority_support=majority_support,
        )

        alternative_reading = self._alternative_reading(
            dominant_reading=dominant_reading,
            over_candidate_level=over_candidate_level,
            over_candidate_active=over_candidate_active,
            over_support_ratio=over_support_ratio,
            real_offensive_volume=real_offensive_volume,
            over_score=over_score,
            under_score=under_score,
        )

        football_confidence = self._football_confidence(
            clock_status=clock_status,
            data_status=data_status,
            risk_status=risk_status,
            contradiction_status=contradiction_status,
            majority_support=majority_support,
            support_ratio=support_ratio,
            real_offensive_volume=real_offensive_volume,
            dominant_reading=dominant_reading,
            game_state=game_state,
        )

        football_warning_level = self._warning_level(
            clock_status=clock_status,
            risk_status=risk_status,
            contradiction_status=contradiction_status,
            league_group=league_group,
            false_pressure_risk=false_pressure_risk,
            data_status=data_status,
        )

        support_points, caution_points = self._story_points(
            minute=minute,
            game_state=game_state,
            dominant_reading=dominant_reading,
            alternative_reading=alternative_reading,
            real_offensive_volume=real_offensive_volume,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
            league_group=league_group,
            league_phase=league_phase,
            risk_status=risk_status,
            clock_status=clock_status,
            false_pressure_risk=false_pressure_risk,
        )

        match_story = self._match_story(
            game_state=game_state,
            dominant_reading=dominant_reading,
            alternative_reading=alternative_reading,
            game_phase=game_phase,
            league_group=league_group,
            support_points=support_points,
            caution_points=caution_points,
        )

        return {
            "match_reader_version": "V17_MATCH_READER_1",
            "football_game_phase": game_phase,
            "football_game_state": game_state,
            "football_dominant_reading": dominant_reading,
            "football_alternative_reading": alternative_reading,
            "football_confidence": football_confidence,
            "football_warning_level": football_warning_level,
            "football_story": match_story,
            "football_support_points": support_points[:8],
            "football_caution_points": caution_points[:8],
            "football_league_note": league_warning or "",
            "football_real_offensive_volume": real_offensive_volume,
            "football_pressure_type": self._pressure_type(
                real_offensive_volume=real_offensive_volume,
                pressure_score=pressure_score,
                false_pressure_risk=false_pressure_risk,
            ),
        }

    def _game_phase(self, minute: int) -> str:
        if minute <= 15:
            return "EARLY_FIRST_HALF"

        if minute <= 30:
            return "FIRST_HALF_GROWTH"

        if minute <= 45:
            return "PRE_HALFTIME"

        if minute <= 60:
            return "SECOND_HALF_START"

        if minute <= 70:
            return "TACTICAL_REVALIDATION"

        if minute <= 80:
            return "BEST_UNDER_DECISION_ZONE"

        if minute <= 88:
            return "LATE_GAME_MANAGEMENT"

        return "FINAL_VOLATILITY"

    def _real_offensive_volume(
        self,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
    ) -> bool:
        return (
            shots >= 10
            or shots_on_target >= 3
            or corners >= 5
            or dangerous_attacks >= 15
            or xg >= 0.85
            or (
                offensive_volume_score >= 55
                and offensive_depth_score >= 48
            )
        )

    def _game_state(
        self,
        minute: int,
        total_goals: int,
        goal_gap: int,
        real_offensive_volume: bool,
        over_score: float,
        under_score: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        under_transition_score: float,
        false_pressure_risk: float,
    ) -> str:
        if false_pressure_risk >= 75:
            return "FALSE_PRESSURE"

        if real_offensive_volume and goal_need_score >= 55 and minute >= 50:
            return "LIVE_GOAL_THREAT"

        if real_offensive_volume and (pressure_score >= 50 or rhythm_score >= 48):
            return "OPEN_ATTACKING_GAME"

        if score_hold_probability >= 78 and under_transition_score >= 72 and minute >= 60:
            return "SCORE_CONTROL_CLOSING"

        if under_score >= over_score + 18 and not real_offensive_volume:
            return "LOW_TEMPO_CONTROL"

        if total_goals >= 3 and goal_gap <= 1 and minute <= 75:
            return "BROKEN_SCORELINE"

        if goal_gap >= 2 and minute >= 70:
            return "RESULT_MANAGEMENT"

        if minute >= 75 and not real_offensive_volume:
            return "LATE_UNDER_DRIFT"

        return "MIXED_READING"

    def _dominant_reading(
        self,
        game_state: str,
        over_score: float,
        under_score: float,
        market_gap: float,
        score_hold_probability: float,
        under_transition_score: float,
        real_offensive_volume: bool,
        over_candidate_level: str,
        over_candidate_active: bool,
        candidate_level: str,
        majority_support: bool,
    ) -> str:
        if game_state in {"SCORE_CONTROL_CLOSING", "LOW_TEMPO_CONTROL", "RESULT_MANAGEMENT", "LATE_UNDER_DRIFT"}:
            return "UNDER"

        if game_state in {"LIVE_GOAL_THREAT", "OPEN_ATTACKING_GAME", "BROKEN_SCORELINE"}:
            if over_score >= under_score - 8 or over_candidate_active:
                return "OVER"

        if under_score >= over_score + 12 and score_hold_probability >= 70:
            return "UNDER"

        if over_score >= under_score + 8 and real_offensive_volume:
            return "OVER"

        if over_candidate_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"} and real_offensive_volume:
            return "OVER"

        if candidate_level == "STRONG_CANDIDATE" and majority_support:
            if under_score >= over_score:
                return "UNDER"
            return "OVER"

        return "OTHER"

    def _alternative_reading(
        self,
        dominant_reading: str,
        over_candidate_level: str,
        over_candidate_active: bool,
        over_support_ratio: float,
        real_offensive_volume: bool,
        over_score: float,
        under_score: float,
    ) -> str:
        if dominant_reading == "UNDER":
            if over_candidate_active or over_support_ratio >= 0.60 or real_offensive_volume:
                return "OVER_WATCH"
            return "NONE"

        if dominant_reading == "OVER":
            if under_score >= over_score + 8:
                return "UNDER_RISK"
            return "NONE"

        if over_candidate_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"}:
            return "OVER_WATCH"

        return "NONE"

    def _football_confidence(
        self,
        clock_status: str,
        data_status: str,
        risk_status: str,
        contradiction_status: str,
        majority_support: bool,
        support_ratio: float,
        real_offensive_volume: bool,
        dominant_reading: str,
        game_state: str,
    ) -> int:
        score = 50

        if clock_status == "CLOCK_OK":
            score += 12
        elif clock_status in {"CLOCK_WARNING", "HALFTIME_WAIT"}:
            score -= 8
        elif clock_status == "BLOCKED_CLOCK":
            score -= 30

        if data_status == "HIGH":
            score += 10
        elif data_status == "MEDIUM":
            score += 5
        elif data_status == "LOW":
            score -= 8

        if risk_status == "LOW_RISK":
            score += 10
        elif risk_status == "MEDIUM_RISK":
            score += 2
        elif risk_status in {"HIGH_RISK", "EXTREME_RISK"}:
            score -= 20

        if contradiction_status in {"STRONG_CONTRADICTION", "CRITICAL_CONTRADICTION"}:
            score -= 20

        if majority_support:
            score += 10

        if support_ratio >= 0.70:
            score += 8
        elif support_ratio >= 0.60:
            score += 4

        if dominant_reading in {"OVER", "UNDER"}:
            score += 6

        if game_state in {"SCORE_CONTROL_CLOSING", "LIVE_GOAL_THREAT", "OPEN_ATTACKING_GAME"}:
            score += 4

        if real_offensive_volume:
            score += 2

        return max(0, min(100, int(score)))

    def _warning_level(
        self,
        clock_status: str,
        risk_status: str,
        contradiction_status: str,
        league_group: str,
        false_pressure_risk: float,
        data_status: str,
    ) -> str:
        if clock_status == "BLOCKED_CLOCK":
            return "TECHNICAL_BLOCK"

        if risk_status == "EXTREME_RISK":
            return "EXTREME"

        if contradiction_status in {"STRONG_CONTRADICTION", "CRITICAL_CONTRADICTION"}:
            return "HIGH"

        if false_pressure_risk >= 75:
            return "HIGH"

        if data_status == "LOW":
            return "MEDIUM"

        if league_group in {"CONMEBOL", "SOUTH_AMERICA"}:
            return "MEDIUM"

        return "LOW"

    def _pressure_type(
        self,
        real_offensive_volume: bool,
        pressure_score: float,
        false_pressure_risk: float,
    ) -> str:
        if false_pressure_risk >= 75:
            return "FALSE_PRESSURE"

        if real_offensive_volume:
            return "REAL_PRESSURE"

        if pressure_score >= 55:
            return "TACTICAL_PRESSURE_WITHOUT_DEPTH"

        return "LOW_PRESSURE"

    def _story_points(
        self,
        minute: int,
        game_state: str,
        dominant_reading: str,
        alternative_reading: str,
        real_offensive_volume: bool,
        shots: float,
        shots_on_target: float,
        corners: float,
        score_hold_probability: float,
        under_transition_score: float,
        league_group: str,
        league_phase: str,
        risk_status: str,
        clock_status: str,
        false_pressure_risk: float,
    ) -> tuple[List[str], List[str]]:
        support: List[str] = []
        caution: List[str] = []

        if dominant_reading == "UNDER":
            support.append("La lectura principal favorece conservación del marcador.")

        if dominant_reading == "OVER":
            support.append("La lectura principal favorece posibilidad de más goles.")

        if real_offensive_volume:
            support.append("Existe volumen ofensivo real detectable.")

        if shots:
            support.append(f"Remates totales detectados: {int(shots)}.")

        if shots_on_target:
            support.append(f"Remates al arco detectados: {int(shots_on_target)}.")

        if corners:
            support.append(f"Corners detectados: {int(corners)}.")

        if score_hold_probability >= 75:
            support.append("Alta probabilidad de conservación del marcador.")

        if under_transition_score >= 75:
            support.append("El partido muestra transición hacia cierre.")

        if alternative_reading != "NONE":
            caution.append(f"Existe lectura alternativa: {alternative_reading}.")

        if league_group in {"CONMEBOL", "SOUTH_AMERICA"}:
            caution.append("Contexto sudamericano requiere lectura dinámica por minuto.")

        if league_phase:
            caution.append(f"Fase de liga/minuto: {league_phase}.")

        if risk_status in {"HIGH_RISK", "EXTREME_RISK"}:
            caution.append("Riesgo operativo elevado.")

        if clock_status != "CLOCK_OK":
            caution.append("Reloj no totalmente confirmado.")

        if false_pressure_risk >= 70:
            caution.append("Posible presión falsa o no sostenida.")

        return support, caution

    def _match_story(
        self,
        game_state: str,
        dominant_reading: str,
        alternative_reading: str,
        game_phase: str,
        league_group: str,
        support_points: List[str],
        caution_points: List[str],
    ) -> str:
        base = (
            f"El partido está en fase {game_phase}, con estado futbolístico {game_state}. "
            f"La lectura dominante es {dominant_reading}."
        )

        if alternative_reading != "NONE":
            base += f" Existe lectura alternativa {alternative_reading}, por lo que no debe ocultarse."

        if league_group in {"CONMEBOL", "SOUTH_AMERICA"}:
            base += " El contexto sudamericano exige revalidación y no lectura automática."

        if support_points:
            base += " Soporte principal: " + support_points[0]

        if caution_points:
            base += " Cautela: " + caution_points[0]

        return base
