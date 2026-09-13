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


class LiveHypothesisAI:
    """
    V17.5 - LiveHypothesisAI

    Rol:
    EVIDENCE_ONLY

    Propósito:
    Construir una hipótesis viva del partido usando evidencias ya existentes:
    - DataTruthAI
    - MatchPhaseAI
    - MomentumTrendAI
    - PressureQualityAI
    - contexto táctico
    - marcador
    - minuto
    - calidad de datos

    No decide.
    No publica.
    No modifica official_*.
    No reemplaza MasterDecisionAI.
    """

    VERSION = "V17.5_LIVE_HYPOTHESIS_AI_1.0"

    def evaluate(
        self,
        *,
        match: Dict[str, Any],
        clock: Optional[Dict[str, Any]] = None,
        data_quality: Optional[Dict[str, Any]] = None,
        data_truth: Optional[Dict[str, Any]] = None,
        match_phase: Optional[Dict[str, Any]] = None,
        momentum_trend: Optional[Dict[str, Any]] = None,
        pressure_quality: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        tactical: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clock = clock or {}
        data_quality = data_quality or {}
        data_truth = data_truth or {}
        match_phase = match_phase or {}
        momentum_trend = momentum_trend or {}
        pressure_quality = pressure_quality or {}
        context = context or {}
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

        home_team = str(match.get("home_team") or "Local")
        away_team = str(match.get("away_team") or "Visitante")

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        scoreline = f"{home_score}-{away_score}"
        total_goals = home_score + away_score

        data_truth_state = upper(data_truth.get("data_truth_state"))
        data_truth_can_interpret = data_truth.get("data_truth_can_interpret")
        if data_truth_can_interpret is None:
            data_truth_can_interpret = data_truth_state not in {
                "NO_INTERPRETABLE_DATA",
                "DATA_INSUFFICIENT",
                "WAIT_REAL_STATS",
                "STALE_CACHE",
            }

        phase_type = upper(match_phase.get("match_phase_type"))
        phase_trigger = upper(match_phase.get("match_phase_trigger"))
        phase_reset_required = bool(match_phase.get("phase_reset_required"))

        momentum_direction = upper(momentum_trend.get("momentum_direction"))
        momentum_owner = upper(momentum_trend.get("momentum_owner"))
        momentum_quality = upper(momentum_trend.get("momentum_quality"))
        momentum_shift_detected = bool(momentum_trend.get("momentum_shift_detected"))

        pressure_type = upper(pressure_quality.get("pressure_type"))
        pressure_owner = upper(pressure_quality.get("pressure_owner"))
        pressure_real_score = safe_float(pressure_quality.get("pressure_real_score"), 0.0)
        pressure_false_score = safe_float(pressure_quality.get("pressure_false_score"), 0.0)
        sterile_dominance = bool(pressure_quality.get("sterile_dominance_detected"))
        transition_threat = bool(pressure_quality.get("transition_threat_detected"))

        pressure_score = safe_float(
            first_value(
                tactical.get("pressure_score"),
                context.get("pressure_score"),
                match.get("pressure_score"),
                default=0,
            ),
            0.0,
        )
        rhythm_score = safe_float(
            first_value(
                tactical.get("rhythm_score"),
                context.get("rhythm_score"),
                match.get("rhythm_score"),
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

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        support_points: List[str] = []
        warnings: List[str] = []

        if not data_truth_can_interpret:
            live_match_state = "DATA_WEAK_MATCH"
            match_direction = "WAIT_REAL_DATA"
            uncertainty_level = "HIGH"
            uncertainty_reason = data_truth.get("data_truth_reason") or "Datos live insuficientes."
            dominant_team = "NONE"
            attacking_trend = "DATA_WEAK"
            pressure_interpretation = "DATA_WEAK"
            score_fairness = "UNKNOWN"
            next_goal_context = "No se puede estimar próximo gol con datos insuficientes."
            under_over_context = "No Stats no es Under; esperar estadísticas reales."
            hypothesis_confidence = 10
            warnings.append("Datos no interpretables: hipótesis limitada.")
            warnings.append("No convertir ausencia de estadísticas en UNDER.")
        else:
            live_match_state = self._classify_live_state(
                phase_type=phase_type,
                phase_trigger=phase_trigger,
                momentum_direction=momentum_direction,
                momentum_quality=momentum_quality,
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
                pressure_false_score=pressure_false_score,
                sterile_dominance=sterile_dominance,
                transition_threat=transition_threat,
                score_hold_probability=score_hold_probability,
                under_transition_score=under_transition_score,
                minute=minute,
                total_goals=total_goals,
            )

            dominant_team = self._dominant_team(
                momentum_owner=momentum_owner,
                pressure_owner=pressure_owner,
                home_team=home_team,
                away_team=away_team,
            )

            attacking_trend = self._attacking_trend(
                momentum_direction=momentum_direction,
                momentum_shift_detected=momentum_shift_detected,
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
            )

            pressure_interpretation = self._pressure_interpretation(
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
                pressure_false_score=pressure_false_score,
            )

            match_direction = self._match_direction(
                live_match_state=live_match_state,
                momentum_direction=momentum_direction,
                pressure_type=pressure_type,
                minute=minute,
            )

            score_fairness = self._score_fairness(
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
                pressure_false_score=pressure_false_score,
                total_goals=total_goals,
                score_hold_probability=score_hold_probability,
            )

            next_goal_context = self._next_goal_context(
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
                transition_threat=transition_threat,
                momentum_direction=momentum_direction,
                dominant_team=dominant_team,
            )

            under_over_context = self._under_over_context(
                live_match_state=live_match_state,
                pressure_type=pressure_type,
                momentum_direction=momentum_direction,
                score_hold_probability=score_hold_probability,
                under_transition_score=under_transition_score,
            )

            uncertainty_level, uncertainty_reason = self._uncertainty(
                phase_reset_required=phase_reset_required,
                momentum_shift_detected=momentum_shift_detected,
                pressure_type=pressure_type,
                pressure_false_score=pressure_false_score,
                data_quality=data_quality,
            )

            hypothesis_confidence = self._confidence(
                data_truth_can_interpret=bool(data_truth_can_interpret),
                pressure_type=pressure_type,
                pressure_real_score=pressure_real_score,
                pressure_false_score=pressure_false_score,
                momentum_shift_detected=momentum_shift_detected,
                uncertainty_level=uncertainty_level,
            )

            if phase_reset_required:
                support_points.append("MatchPhaseAI detectó fase nueva; la lectura anterior debe revalidarse.")
            if momentum_shift_detected:
                support_points.append("MomentumTrendAI detectó cambio de tendencia.")
            if pressure_type:
                support_points.append(f"PressureQualityAI clasifica presión como {pressure_type}.")
            if dominant_team != "NONE":
                support_points.append(f"Dominio contextual inclinado hacia {dominant_team}.")
            if transition_threat:
                support_points.append("Amenaza de transición detectada.")
            if sterile_dominance:
                warnings.append("Dominio estéril: no elevar confianza solo por posesión o presión territorial.")
            if pressure_type == "FALSE_PRESSURE":
                warnings.append("Presión falsa: cuidado con proyectar gol solo por volumen superficial.")
            if phase_reset_required:
                warnings.append("Cambio de fase activo: evitar arrastrar hipótesis anterior sin confirmación.")

        summary = self._summary(
            minute=minute,
            scoreline=scoreline,
            live_match_state=live_match_state,
            dominant_team=dominant_team,
            attacking_trend=attacking_trend,
            pressure_interpretation=pressure_interpretation,
            match_direction=match_direction,
            uncertainty_level=uncertainty_level,
        )

        return {
            "live_hypothesis_role": "EVIDENCE_ONLY",
            "live_hypothesis_version": self.VERSION,
            "live_match_state": live_match_state,
            "live_hypothesis_summary": summary,
            "dominant_team": dominant_team,
            "attacking_trend": attacking_trend,
            "pressure_interpretation": pressure_interpretation,
            "match_direction": match_direction,
            "score_fairness": score_fairness,
            "next_goal_context": next_goal_context,
            "under_over_context": under_over_context,
            "uncertainty_level": uncertainty_level,
            "uncertainty_reason": uncertainty_reason,
            "hypothesis_confidence": round(float(hypothesis_confidence), 2),
            "hypothesis_support_points": unique(support_points),
            "hypothesis_warnings": unique(warnings),
            "live_hypothesis_context": {
                "minute": minute,
                "scoreline": scoreline,
                "home_team": home_team,
                "away_team": away_team,
                "data_truth_state": data_truth_state,
                "phase_type": phase_type,
                "phase_trigger": phase_trigger,
                "momentum_direction": momentum_direction,
                "momentum_owner": momentum_owner,
                "pressure_type": pressure_type,
                "pressure_owner": pressure_owner,
                "pressure_real_score": round(pressure_real_score, 2),
                "pressure_false_score": round(pressure_false_score, 2),
                "pressure_score": round(pressure_score, 2),
                "rhythm_score": round(rhythm_score, 2),
                "offensive_volume_score": round(offensive_volume_score, 2),
                "score_hold_probability": round(score_hold_probability, 2),
                "under_transition_score": round(under_transition_score, 2),
            },
        }

    def _classify_live_state(
        self,
        *,
        phase_type: str,
        phase_trigger: str,
        momentum_direction: str,
        momentum_quality: str,
        pressure_type: str,
        pressure_real_score: float,
        pressure_false_score: float,
        sterile_dominance: bool,
        transition_threat: bool,
        score_hold_probability: float,
        under_transition_score: float,
        minute: int,
        total_goals: int,
    ) -> str:
        if phase_type == "TECHNICAL_PHASE":
            return "DATA_WEAK_MATCH"

        if phase_type == "POST_GOAL_REACTION" or phase_trigger == "GOAL":
            return "POST_GOAL_REACTION"

        if minute >= 85 and momentum_direction in {"CHAOTIC", "HOME_RISING", "AWAY_RISING", "REVERSING"}:
            return "FINAL_STRETCH_UNSTABLE"

        if momentum_direction == "CHAOTIC":
            return "CHAOTIC_MATCH"

        if transition_threat:
            return "TRANSITION_THREAT"

        if pressure_type == "REAL_PRESSURE" and pressure_real_score >= 60:
            return "REAL_PRESSURE_BUILDING"

        if sterile_dominance or pressure_type == "STERILE_DOMINANCE":
            return "STERILE_DOMINANCE"

        if momentum_direction == "COOLING_DOWN":
            return "GAME_COOLING_DOWN"

        if pressure_type == "NO_PRESSURE" and score_hold_probability >= 62 and under_transition_score >= 55:
            return "CLOSED_REAL_MATCH"

        if momentum_direction == "HOME_RISING":
            return "HOME_CONTROL"

        if momentum_direction == "AWAY_RISING":
            return "AWAY_CONTROL"

        if total_goals >= 3 or pressure_real_score >= 55:
            return "OPEN_MATCH"

        return "CLOSED_REAL_MATCH"

    def _dominant_team(
        self,
        *,
        momentum_owner: str,
        pressure_owner: str,
        home_team: str,
        away_team: str,
    ) -> str:
        owner = pressure_owner if pressure_owner in {"HOME", "AWAY"} else momentum_owner

        if owner == "HOME":
            return home_team
        if owner == "AWAY":
            return away_team
        return "NONE"

    def _attacking_trend(
        self,
        *,
        momentum_direction: str,
        momentum_shift_detected: bool,
        pressure_type: str,
        pressure_real_score: float,
    ) -> str:
        if momentum_direction in {"HOME_RISING", "AWAY_RISING"} and momentum_shift_detected:
            return "RISING"
        if momentum_direction == "CHAOTIC":
            return "CHAOTIC"
        if momentum_direction in {"FALLING", "COOLING_DOWN"}:
            return "FALLING"
        if pressure_type == "REAL_PRESSURE" and pressure_real_score >= 55:
            return "SUSTAINED"
        if pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"}:
            return "STERILE"
        return "STABLE"

    def _pressure_interpretation(
        self,
        *,
        pressure_type: str,
        pressure_real_score: float,
        pressure_false_score: float,
    ) -> str:
        if pressure_type == "REAL_PRESSURE":
            return "Presión real con amenaza verificable."
        if pressure_type == "FALSE_PRESSURE":
            return "Presión aparente; falta amenaza limpia."
        if pressure_type == "STERILE_DOMINANCE":
            return "Dominio estéril sin profundidad suficiente."
        if pressure_type == "TRANSITION_THREAT":
            return "Amenaza en transición aunque el dominio no sea sostenido."
        if pressure_type == "NO_PRESSURE":
            return "Sin presión ofensiva relevante."
        if pressure_type == "DATA_WEAK":
            return "Presión no interpretable por datos débiles."

        if pressure_real_score >= pressure_false_score:
            return "Presión mixta con ligera base real."
        return "Presión mixta con riesgo de ser falsa."

    def _match_direction(
        self,
        *,
        live_match_state: str,
        momentum_direction: str,
        pressure_type: str,
        minute: int,
    ) -> str:
        if live_match_state in {"CHAOTIC_MATCH", "REAL_PRESSURE_BUILDING", "TRANSITION_THREAT"}:
            return "BREAKING"
        if live_match_state in {"CLOSED_REAL_MATCH", "GAME_COOLING_DOWN"}:
            return "CLOSING"
        if live_match_state in {"POST_GOAL_REACTION", "FINAL_STRETCH_UNSTABLE"}:
            return "UNSTABLE"
        if momentum_direction in {"HOME_RISING", "AWAY_RISING", "REVERSING"}:
            return "SHIFTING"
        if pressure_type == "STERILE_DOMINANCE":
            return "CONTROLLED_BUT_STERILE"
        return "STABLE"

    def _score_fairness(
        self,
        *,
        pressure_type: str,
        pressure_real_score: float,
        pressure_false_score: float,
        total_goals: int,
        score_hold_probability: float,
    ) -> str:
        if pressure_type == "DATA_WEAK":
            return "UNKNOWN"
        if pressure_type == "REAL_PRESSURE" and pressure_real_score >= 65 and total_goals <= 1:
            return "UNDERSTATED_DOMINANCE"
        if pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"} and total_goals >= 2:
            return "OVERSTATED_DOMINANCE"
        if score_hold_probability >= 70:
            return "FAIR_SCORE_HOLD"
        return "FAIR_SCORE"

    def _next_goal_context(
        self,
        *,
        pressure_type: str,
        pressure_real_score: float,
        transition_threat: bool,
        momentum_direction: str,
        dominant_team: str,
    ) -> str:
        if pressure_type == "DATA_WEAK":
            return "No hay datos suficientes para contexto de próximo gol."
        if transition_threat:
            return "El próximo gol puede venir por transición, no necesariamente por dominio sostenido."
        if pressure_type == "REAL_PRESSURE" and pressure_real_score >= 65:
            if dominant_team != "NONE":
                return f"La amenaza de próximo gol se inclina hacia {dominant_team}, pero sigue siendo evidencia."
            return "Existe amenaza real de próximo gol, pero sin dueño claro."
        if pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"}:
            return "La presión actual no basta para proyectar próximo gol con seguridad."
        if momentum_direction == "COOLING_DOWN":
            return "La probabilidad contextual de próximo gol baja por enfriamiento."
        return "Contexto de próximo gol estable, sin amenaza clara."

    def _under_over_context(
        self,
        *,
        live_match_state: str,
        pressure_type: str,
        momentum_direction: str,
        score_hold_probability: float,
        under_transition_score: float,
    ) -> str:
        if live_match_state == "DATA_WEAK_MATCH":
            return "No Stats no es Under; datos insuficientes para mercado."
        if live_match_state in {"REAL_PRESSURE_BUILDING", "CHAOTIC_MATCH", "TRANSITION_THREAT"}:
            return "Contexto más compatible con riesgo de gol que con cierre limpio."
        if pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"}:
            return "UNDER puede tener lectura contextual, pero la presión debe validarse como baja real."
        if score_hold_probability >= 68 and under_transition_score >= 58 and momentum_direction in {"STABLE", "COOLING_DOWN"}:
            return "Contexto compatible con conservación del marcador, si los datos son confiables."
        return "Sin ventaja clara entre OVER/UNDER desde la hipótesis viva."

    def _uncertainty(
        self,
        *,
        phase_reset_required: bool,
        momentum_shift_detected: bool,
        pressure_type: str,
        pressure_false_score: float,
        data_quality: Dict[str, Any],
    ) -> tuple[str, str]:
        if not data_quality.get("data_valid", True):
            return "HIGH", "Calidad de datos limitada o inválida."

        if phase_reset_required:
            return "MEDIUM_HIGH", "Cambio de fase: la lectura anterior necesita revalidación."

        if momentum_shift_detected:
            return "MEDIUM", "Cambio de momentum detectado; el partido puede estar moviéndose."

        if pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"} or pressure_false_score >= 60:
            return "MEDIUM", "Riesgo de interpretar presión falsa como amenaza real."

        return "LOW", "Evidencia live razonablemente estable."

    def _confidence(
        self,
        *,
        data_truth_can_interpret: bool,
        pressure_type: str,
        pressure_real_score: float,
        pressure_false_score: float,
        momentum_shift_detected: bool,
        uncertainty_level: str,
    ) -> float:
        if not data_truth_can_interpret:
            return 10.0

        confidence = 48.0

        if pressure_type == "REAL_PRESSURE":
            confidence += 14
        elif pressure_type == "TRANSITION_THREAT":
            confidence += 10
        elif pressure_type in {"FALSE_PRESSURE", "STERILE_DOMINANCE"}:
            confidence -= 8
        elif pressure_type == "NO_PRESSURE":
            confidence += 3

        if pressure_real_score >= 65:
            confidence += 8
        if pressure_false_score >= 60:
            confidence -= 10
        if momentum_shift_detected:
            confidence += 6

        if uncertainty_level == "LOW":
            confidence += 8
        elif uncertainty_level == "MEDIUM":
            confidence -= 2
        elif uncertainty_level == "MEDIUM_HIGH":
            confidence -= 8
        elif uncertainty_level == "HIGH":
            confidence -= 18

        return max(0.0, min(100.0, confidence))

    def _summary(
        self,
        *,
        minute: int,
        scoreline: str,
        live_match_state: str,
        dominant_team: str,
        attacking_trend: str,
        pressure_interpretation: str,
        match_direction: str,
        uncertainty_level: str,
    ) -> str:
        owner = dominant_team if dominant_team != "NONE" else "sin dominio claro"

        return (
            f"Minuto {minute}, marcador {scoreline}. "
            f"Estado live: {live_match_state}. "
            f"Dominio contextual: {owner}. "
            f"Tendencia ofensiva: {attacking_trend}. "
            f"{pressure_interpretation} "
            f"Dirección del partido: {match_direction}. "
            f"Incertidumbre: {uncertainty_level}."
        )
