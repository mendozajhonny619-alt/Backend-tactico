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


class EntryTimingAI:
    """
    IA de momento de entrada V17.

    No decide el mercado.
    No reemplaza al análisis del partido.

    Su objetivo es responder:
    - ¿Conviene entrar ahora?
    - ¿Conviene esperar mejor minuto?
    - ¿Ya pasó la ventana?
    - ¿Debe evitarse por volatilidad, reloj o riesgo?

    Ajuste V17.1:
    - No cierra automáticamente por minuto 45/90 si el partido sigue LIVE.
    - No convierte advertencias suaves de reloj en bloqueo operativo.
    - Permite que STRONG_CANDIDATE / MAIN_SIGNAL sobrevivan como entrada posible
      o revalidación, especialmente en tramos tardíos con amenaza real.
    """

    def evaluate(
        self,
        signal: Dict[str, Any],
        match_reader: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._no_data()

        minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("estimated_minute"),
            0,
        )

        panel_market = normalize_market(
            signal.get("panel_market")
            or signal.get("market_direction")
            or signal.get("master_market")
            or signal.get("market")
            or signal.get("suggested_market")
        )

        football_dominant = normalize_market(match_reader.get("football_dominant_reading"))
        if panel_market == "OTHER" and football_dominant in {"OVER", "UNDER"}:
            panel_market = football_dominant

        clock_status = normalize_text(signal.get("clock_status"))
        risk_status = normalize_text(signal.get("risk_status"))
        panel_decision = normalize_text(signal.get("panel_decision"))
        panel_signal_type = normalize_text(signal.get("panel_signal_type"))
        candidate_level = normalize_text(signal.get("candidate_level"))
        league_group = normalize_text(signal.get("league_context_group"))
        league_phase = normalize_text(signal.get("league_minute_phase"))
        warning_level = normalize_text(match_reader.get("football_warning_level"))
        game_state = normalize_text(match_reader.get("football_game_state"))
        match_status = normalize_text(
            signal.get("real_time_status")
            or signal.get("status")
            or signal.get("match_status")
            or match_reader.get("match_status")
            or match_reader.get("football_match_status")
        )

        critical_block = bool(signal.get("critical_block"))
        hard_blockers = signal.get("hard_blockers", []) or []
        clock_blockers = signal.get("clock_blockers", []) or []

        majority_support = bool(signal.get("majority_support"))
        support_ratio = safe_float(signal.get("support_ratio"), 0.0)

        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_candidate_level = normalize_text(signal.get("over_candidate_level"))
        over_support_ratio = safe_float(signal.get("over_support_ratio"), 0.0)

        football_confidence = safe_int(match_reader.get("football_confidence"), 0)

        real_volume = bool(match_reader.get("football_real_offensive_volume"))
        score_hold_probability = safe_float(signal.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(signal.get("under_transition_score"), 0.0)
        false_pressure_risk = safe_float(signal.get("false_pressure_risk"), 0.0)
        risk_score = safe_float(signal.get("risk_score"), 0.0)

        real_goal_threat = safe_float(
            signal.get("real_goal_threat")
            or match_reader.get("real_goal_threat")
            or match_reader.get("football_real_goal_threat"),
            0.0,
        )
        prediction_live_over_probability = safe_float(signal.get("prediction_live_over_probability"), 0.0)
        prediction_live_under_probability = safe_float(signal.get("prediction_live_under_probability"), 0.0)
        break_risk = normalize_text(signal.get("break_risk") or match_reader.get("break_risk"))
        pressure_quality = normalize_text(
            signal.get("pressure_quality")
            or signal.get("pressure_quality_state")
            or match_reader.get("pressure_quality")
            or match_reader.get("football_pressure_quality")
        )

        is_live_status = self._is_live_status(match_status)
        is_added_time_live = self._is_added_time_live(minute, match_status)
        is_strong_signal = self._is_strong_signal(
            panel_decision=panel_decision,
            panel_signal_type=panel_signal_type,
            candidate_level=candidate_level,
            football_confidence=football_confidence,
            majority_support=majority_support,
            support_ratio=support_ratio,
        )

        if self._technical_block(
            critical_block=critical_block,
            hard_blockers=hard_blockers,
            clock_blockers=clock_blockers,
            clock_status=clock_status,
            risk_status=risk_status,
        ):
            return self._avoid(
                reason="Existe bloqueo técnico, riesgo extremo o reloj no operable.",
                label="NO ENTRAR",
                timing_type="TECHNICAL_BLOCK",
                priority=0,
            )

        if clock_status == "HALFTIME_WAIT":
            return self._wait(
                reason="El partido está en descanso o pausa de entretiempo. Esperar confirmación del segundo tiempo.",
                label="ESPERAR SEGUNDO TIEMPO",
                timing_type="HALFTIME_WAIT",
                target_zone="45_60",
                priority=35,
            )

        if clock_status != "CLOCK_OK":
            if self._is_soft_clock_status(clock_status) and is_strong_signal and is_live_status:
                # No autoriza por sí solo, pero tampoco mata una señal élite por una advertencia suave.
                # La decisión final sigue dependiendo de MasterDecision / Promotion / Ranker.
                pass
            else:
                return self._wait(
                    reason="El reloj no está completamente confirmado. Esperar nueva actualización.",
                    label="ESPERAR RELOJ",
                    timing_type="CLOCK_CONFIRMATION",
                    target_zone="NEXT_SCAN",
                    priority=30,
                )

        if warning_level in {"EXTREME", "TECHNICAL_BLOCK"}:
            return self._avoid(
                reason="La lectura futbolística indica riesgo técnico o extremo.",
                label="NO ENTRAR",
                timing_type="HIGH_WARNING",
                priority=5,
            )

        if panel_market == "OVER":
            return self._over_timing(
                minute=minute,
                panel_decision=panel_decision,
                panel_signal_type=panel_signal_type,
                candidate_level=candidate_level,
                league_group=league_group,
                league_phase=league_phase,
                majority_support=majority_support,
                support_ratio=support_ratio,
                over_candidate_active=over_candidate_active,
                over_candidate_level=over_candidate_level,
                over_support_ratio=over_support_ratio,
                football_confidence=football_confidence,
                real_volume=real_volume,
                game_state=game_state,
                false_pressure_risk=false_pressure_risk,
                risk_score=risk_score,
                real_goal_threat=real_goal_threat,
                prediction_live_over_probability=prediction_live_over_probability,
                break_risk=break_risk,
                pressure_quality=pressure_quality,
                is_added_time_live=is_added_time_live,
                is_strong_signal=is_strong_signal,
            )

        if panel_market == "UNDER":
            return self._under_timing(
                minute=minute,
                panel_decision=panel_decision,
                panel_signal_type=panel_signal_type,
                candidate_level=candidate_level,
                league_group=league_group,
                league_phase=league_phase,
                majority_support=majority_support,
                support_ratio=support_ratio,
                football_confidence=football_confidence,
                score_hold_probability=score_hold_probability,
                under_transition_score=under_transition_score,
                real_volume=real_volume,
                game_state=game_state,
                false_pressure_risk=false_pressure_risk,
                risk_score=risk_score,
                real_goal_threat=real_goal_threat,
                prediction_live_under_probability=prediction_live_under_probability,
                break_risk=break_risk,
                pressure_quality=pressure_quality,
                is_added_time_live=is_added_time_live,
                is_strong_signal=is_strong_signal,
            )

        return self._wait(
            reason="La lectura aún no define mercado principal claro.",
            label="OBSERVAR",
            timing_type="NO_CLEAR_MARKET",
            target_zone="NEXT_SCAN",
            priority=25,
        )

    def _over_timing(
        self,
        minute: int,
        panel_decision: str,
        panel_signal_type: str,
        candidate_level: str,
        league_group: str,
        league_phase: str,
        majority_support: bool,
        support_ratio: float,
        over_candidate_active: bool,
        over_candidate_level: str,
        over_support_ratio: float,
        football_confidence: int,
        real_volume: bool,
        game_state: str,
        false_pressure_risk: float,
        risk_score: float,
        real_goal_threat: float = 0.0,
        prediction_live_over_probability: float = 0.0,
        break_risk: str = "",
        pressure_quality: str = "",
        is_added_time_live: bool = False,
        is_strong_signal: bool = False,
    ) -> Dict[str, Any]:
        if false_pressure_risk >= 75 and not is_strong_signal:
            return self._avoid(
                reason="OVER tiene riesgo de presión falsa. Evitar entrada directa.",
                label="NO ENTRAR OVER",
                timing_type="OVER_FALSE_PRESSURE",
                priority=15,
            )

        if not real_volume:
            if is_strong_signal and real_goal_threat >= 62:
                return self._wait(
                    reason="OVER tiene lectura fuerte, pero necesita confirmar volumen real en el próximo escaneo.",
                    label="OVER FUERTE, REVALIDAR VOLUMEN",
                    timing_type="OVER_STRONG_REVALIDATE_VOLUME",
                    target_zone="NEXT_SCAN",
                    priority=58,
                )

            return self._wait(
                reason="OVER necesita volumen ofensivo real antes de considerar entrada.",
                label="ESPERAR VOLUMEN OVER",
                timing_type="OVER_WAIT_VOLUME",
                target_zone="NEXT_SCAN",
                priority=35,
            )

        if minute < 15:
            return self._wait(
                reason="Minuto muy temprano. OVER solo debe observarse salvo volumen extremo.",
                label="OVER TEMPRANO, ESPERAR",
                timing_type="OVER_EARLY_WAIT",
                target_zone="15_30",
                priority=40,
            )

        if 25 <= minute <= 35:
            if football_confidence >= 72 and over_support_ratio >= 0.62:
                return self._now(
                    reason="Ventana rentable de primer tiempo para OVER con volumen real y mayoría ofensiva.",
                    label="OVER POSIBLE AHORA",
                    timing_type="OVER_FIRST_HALF_WINDOW",
                    priority=82,
                )

            return self._wait(
                reason="OVER está en buena zona, pero requiere una confirmación más.",
                label="OVER EN CRECIMIENTO",
                timing_type="OVER_NEEDS_CONFIRMATION",
                target_zone="30_45",
                priority=60,
            )

        if 55 <= minute <= 68:
            if football_confidence >= 68 and over_support_ratio >= 0.58:
                return self._now(
                    reason="Ventana fuerte de segundo tiempo para OVER con volumen real.",
                    label="OVER POSIBLE AHORA",
                    timing_type="OVER_SECOND_HALF_WINDOW",
                    priority=86,
                )

            return self._wait(
                reason="OVER está vivo, pero todavía falta confirmación en la ventana 55-68.",
                label="OVER EN CRECIMIENTO",
                timing_type="OVER_SECOND_HALF_WAIT",
                target_zone="60_70",
                priority=64,
            )

        if 69 <= minute <= 75:
            if (
                over_candidate_level == "OVER_STRONG_CANDIDATE"
                and football_confidence >= 75
                and real_volume
            ):
                return self._now(
                    reason="OVER todavía es válido por asedio real antes del tramo final.",
                    label="OVER CON ASEDIO REAL",
                    timing_type="OVER_LATE_VALID",
                    priority=78,
                )

            return self._wait(
                reason="En esta fase conviene revalidar OVER. CONMEBOL y ligas volátiles pueden cerrarse.",
                label="REVALIDAR OVER",
                timing_type="OVER_REVALIDATE",
                target_zone="NEXT_SCAN",
                priority=55,
            )

        if minute > 75:
            strong_late_threat = (
                real_volume
                and (
                    game_state in {"LIVE_GOAL_THREAT", "OPEN_ATTACKING_GAME"}
                    or pressure_quality in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"}
                    or real_goal_threat >= 68
                    or prediction_live_over_probability >= 70
                    or break_risk in {"MEDIUM", "HIGH"}
                )
                and football_confidence >= 72
                and (over_support_ratio >= 0.62 or support_ratio >= 0.62 or is_strong_signal)
            )

            if strong_late_threat:
                return self._now(
                    reason="OVER tardío permitido por amenaza real, partido vivo y lectura fuerte.",
                    label="OVER TARDÍO VÁLIDO",
                    timing_type="OVER_LATE_VALID_THREAT",
                    priority=76 if not is_added_time_live else 72,
                )

            if is_strong_signal:
                return self._wait(
                    reason="OVER es candidato fuerte, pero en tramo tardío requiere una confirmación adicional de amenaza real.",
                    label="OVER TARDÍO, REVALIDAR",
                    timing_type="OVER_LATE_REVALIDATE",
                    target_zone="NEXT_SCAN",
                    priority=57,
                )

            return self._wait(
                reason="OVER después del 75 requiere confirmación fuerte. Mantener en observación, no descartar automáticamente.",
                label="OVER TARDÍO EN OBSERVACIÓN",
                timing_type="OVER_LATE_WATCH",
                target_zone="NEXT_SCAN",
                priority=42,
            )

        return self._wait(
            reason="OVER tiene lectura, pero no está en la mejor ventana de entrada.",
            label="ESPERAR MEJOR MOMENTO OVER",
            timing_type="OVER_WAIT_BETTER_WINDOW",
            target_zone="55_68",
            priority=50,
        )

    def _under_timing(
        self,
        minute: int,
        panel_decision: str,
        panel_signal_type: str,
        candidate_level: str,
        league_group: str,
        league_phase: str,
        majority_support: bool,
        support_ratio: float,
        football_confidence: int,
        score_hold_probability: float,
        under_transition_score: float,
        real_volume: bool,
        game_state: str,
        false_pressure_risk: float,
        risk_score: float,
        real_goal_threat: float = 0.0,
        prediction_live_under_probability: float = 0.0,
        break_risk: str = "",
        pressure_quality: str = "",
        is_added_time_live: bool = False,
        is_strong_signal: bool = False,
    ) -> Dict[str, Any]:
        if real_volume and game_state in {"LIVE_GOAL_THREAT", "OPEN_ATTACKING_GAME"}:
            return self._wait(
                reason="UNDER tiene riesgo porque todavía existe volumen ofensivo real.",
                label="UNDER CON RIESGO, ESPERAR",
                timing_type="UNDER_WAIT_VOLUME_DECAY",
                target_zone="NEXT_SCAN",
                priority=45,
            )

        if minute < 30:
            return self._wait(
                reason="UNDER demasiado temprano puede ser vulnerable a gol aislado.",
                label="UNDER TEMPRANO, ESPERAR",
                timing_type="UNDER_EARLY_WAIT",
                target_zone="30_45",
                priority=40,
            )

        if 30 <= minute <= 45:
            if (
                football_confidence >= 75
                and score_hold_probability >= 78
                and under_transition_score >= 72
                and not real_volume
            ):
                return self._now(
                    reason="UNDER de primer tiempo permitido por cierre claro y bajo volumen ofensivo.",
                    label="UNDER POSIBLE AHORA",
                    timing_type="UNDER_FIRST_HALF_CONTROL",
                    priority=72,
                )

            return self._wait(
                reason="UNDER en primer tiempo requiere mayor confirmación.",
                label="UNDER EN CONSERVACIÓN",
                timing_type="UNDER_FIRST_HALF_WAIT",
                target_zone="60_75",
                priority=55,
            )

        if 60 <= minute <= 75:
            if (
                football_confidence >= 68
                and score_hold_probability >= 72
                and under_transition_score >= 70
                and not real_volume
            ):
                return self._now(
                    reason="Ventana ideal para UNDER. El partido muestra conservación y bajo volumen real.",
                    label="UNDER POSIBLE AHORA",
                    timing_type="UNDER_IDEAL_WINDOW",
                    priority=88,
                )

            return self._wait(
                reason="UNDER está en zona ideal, pero falta confirmar caída ofensiva.",
                label="UNDER CERCA, ESPERAR",
                timing_type="UNDER_NEEDS_CONFIRMATION",
                target_zone="68_80",
                priority=68,
            )

        if 76 <= minute <= 85:
            if (
                football_confidence >= 65
                and score_hold_probability >= 70
                and under_transition_score >= 68
            ):
                return self._now(
                    reason="UNDER tardío viable por conservación del marcador.",
                    label="UNDER TARDÍO VIABLE",
                    timing_type="UNDER_LATE_CONTROL",
                    priority=78,
                )

            return self._wait(
                reason="UNDER tardío requiere confirmar que no hay reacción ofensiva real.",
                label="REVALIDAR UNDER",
                timing_type="UNDER_LATE_REVALIDATE",
                target_zone="NEXT_SCAN",
                priority=58,
            )

        if minute > 85:
            late_under_control = (
                not real_volume
                and football_confidence >= 67
                and score_hold_probability >= 74
                and under_transition_score >= 70
                and real_goal_threat <= 42
                and break_risk not in {"MEDIUM", "HIGH"}
                and prediction_live_under_probability >= 58
            )

            if late_under_control:
                return self._now(
                    reason="UNDER muy tardío permitido porque el partido muestra control, bajo peligro real y conservación del marcador.",
                    label="UNDER MUY TARDÍO CONTROLADO",
                    timing_type="UNDER_VERY_LATE_CONTROL",
                    priority=70 if not is_added_time_live else 66,
                )

            if is_strong_signal:
                return self._wait(
                    reason="UNDER es candidato fuerte, pero en minuto muy avanzado necesita confirmar ausencia de ruptura o evento aislado.",
                    label="UNDER MUY TARDÍO, REVALIDAR",
                    timing_type="UNDER_VERY_LATE_REVALIDATE",
                    target_zone="NEXT_SCAN",
                    priority=54,
                )

            return self._wait(
                reason="Minuto muy avanzado. Mantener UNDER en observación salvo control claro del marcador.",
                label="UNDER MUY TARDÍO EN OBSERVACIÓN",
                timing_type="UNDER_VERY_LATE_WATCH",
                target_zone="NEXT_SCAN",
                priority=38,
            )

        return self._wait(
            reason="UNDER tiene lectura, pero conviene esperar mejor ventana.",
            label="ESPERAR MEJOR MOMENTO UNDER",
            timing_type="UNDER_WAIT_BETTER_WINDOW",
            target_zone="60_75",
            priority=55,
        )

    def _technical_block(
        self,
        critical_block: bool,
        hard_blockers: List[Any],
        clock_blockers: List[Any],
        clock_status: str,
        risk_status: str,
    ) -> bool:
        if critical_block:
            return True

        if hard_blockers:
            return True

        if clock_blockers:
            return True

        if clock_status == "BLOCKED_CLOCK":
            return True

        if risk_status == "EXTREME_RISK":
            return True

        return False

    def _is_live_status(self, status: str) -> bool:
        if not status:
            return False
        if status in {"LIVE", "IN_PLAY", "1H", "2H", "FIRST_HALF", "SECOND_HALF", "ET", "EXTRA_TIME"}:
            return True
        if "+" in status and not any(end in status for end in {"FT", "FINISHED", "ENDED"}):
            return True
        return False

    def _is_added_time_live(self, minute: int, status: str) -> bool:
        if not self._is_live_status(status):
            return False
        # El minuto no cierra el partido. Si el estado sigue LIVE, 45/90/120 son tramos jugables.
        return minute >= 45

    def _is_soft_clock_status(self, clock_status: str) -> bool:
        return clock_status in {
            "CLOCK_WARNING",
            "CLOCK_SOFT_WARNING",
            "DATA_AGING",
            "DATA_TIMESTAMP_MISSING_BUT_STATS_CONFIRMED",
            "CLOCK_STALE_SOFT",
            "MINUTE_LAG_SOFT",
        }

    def _is_strong_signal(
        self,
        panel_decision: str,
        panel_signal_type: str,
        candidate_level: str,
        football_confidence: int,
        majority_support: bool,
        support_ratio: float,
    ) -> bool:
        strong_labels = {
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
            "STRONG_CANDIDATE",
            "ELITE_CANDIDATE",
            "DIRECT_SIGNAL",
            "SEÑAL_DIRECTA",
            "SENAL_DIRECTA",
        }
        if panel_decision in {"ENTER", "OPERABLE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
            return True
        if panel_signal_type in strong_labels or candidate_level in strong_labels:
            return True
        if football_confidence >= 75 and (majority_support or support_ratio >= 0.62):
            return True
        return False

    def _now(
        self,
        reason: str,
        label: str,
        timing_type: str,
        priority: int,
    ) -> Dict[str, Any]:
        return {
            "entry_timing_version": "V17_ENTRY_TIMING_1_1",
            "entry_window": "NOW",
            "entry_timing_label": label,
            "entry_timing_type": timing_type,
            "entry_priority": priority,
            "entry_permission": "ENTRADA_POSIBLE",
            "entry_target_zone": "NOW",
            "entry_reason": reason,
            "entry_wait_next_scan": False,
            "entry_avoid": False,
        }

    def _wait(
        self,
        reason: str,
        label: str,
        timing_type: str,
        target_zone: str,
        priority: int,
    ) -> Dict[str, Any]:
        return {
            "entry_timing_version": "V17_ENTRY_TIMING_1_1",
            "entry_window": "WAIT",
            "entry_timing_label": label,
            "entry_timing_type": timing_type,
            "entry_priority": priority,
            "entry_permission": "ESPERAR_CONFIRMACION",
            "entry_target_zone": target_zone,
            "entry_reason": reason,
            "entry_wait_next_scan": True,
            "entry_avoid": False,
        }

    def _avoid(
        self,
        reason: str,
        label: str,
        timing_type: str,
        priority: int,
    ) -> Dict[str, Any]:
        return {
            "entry_timing_version": "V17_ENTRY_TIMING_1_1",
            "entry_window": "AVOID",
            "entry_timing_label": label,
            "entry_timing_type": timing_type,
            "entry_priority": priority,
            "entry_permission": "NO_OPERAR",
            "entry_target_zone": "NONE",
            "entry_reason": reason,
            "entry_wait_next_scan": False,
            "entry_avoid": True,
        }

    def _no_data(self) -> Dict[str, Any]:
        return {
            "entry_timing_version": "V17_ENTRY_TIMING_1_1",
            "entry_window": "AVOID",
            "entry_timing_label": "SIN DATOS",
            "entry_timing_type": "NO_DATA",
            "entry_priority": 0,
            "entry_permission": "NO_OPERAR",
            "entry_target_zone": "NONE",
            "entry_reason": "No hay señal válida para evaluar momento de entrada.",
            "entry_wait_next_scan": False,
            "entry_avoid": True,
        }
