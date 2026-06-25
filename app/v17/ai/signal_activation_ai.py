from typing import Any, Dict, List, Optional


class SignalActivationAI:
    """
    V17_SIGNAL_ACTIVATION_AI

    Capa final de activación operativa.

    Mejora V17:
    - No bloquea automáticamente por cualquier blocker.
    - Diferencia bloqueo crítico real vs advertencia operativa.
    - Respeta la coherencia de MatchPredictionAI.
    - Evita activar UNDER limpio si la predicción ve riesgo alto de gol.
    - Evita activar OVER limpio si la predicción ve conservación clara.
    """

    VERSION = "V17_SIGNAL_ACTIVATION_AI_2"

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        blockers = self._collect_blockers(signal)
        soft_warnings = self._collect_warnings(signal)

        market = self._detect_market(signal)
        minute = self._minute(signal)

        over_score = self._num(signal.get("over_score"))
        under_score = self._num(signal.get("under_score"))

        promotion_level = self._txt(signal.get("promotion_level"))
        master_status = self._txt(signal.get("master_status"))
        panel_section = self._txt(signal.get("panel_section"))
        entry_window = self._txt(signal.get("entry_window"))

        over_candidate_level = self._txt(signal.get("over_candidate_level"))
        panel_signal_type = self._txt(signal.get("panel_signal_type"))
        football_reading = self._txt(signal.get("football_dominant_reading"))
        narrative_reading = self._txt(signal.get("narrative_reading_name"))

        pressure_score = self._num(signal.get("pressure_score"))
        offensive_volume_score = self._num(
            signal.get("offensive_volume_score")
            or signal.get("match_maturity_live_volume_score")
        )
        rhythm_score = self._num(signal.get("rhythm_score"))
        risk_score = self._num(signal.get("risk_score"))
        maturity_score = self._num(signal.get("match_maturity_score"))
        data_quality = self._txt(signal.get("data_quality") or signal.get("data_quality_status"))

        prediction_market = self._txt(signal.get("prediction_market"))
        prediction_alignment = self._txt(signal.get("prediction_market_alignment"))
        prediction_final_recommendation = self._txt(signal.get("final_market_recommendation"))
        prediction_conflict_level = self._txt(signal.get("prediction_conflict_level"))
        next_goal_probability = self._txt(signal.get("prediction_next_goal_probability"))

        block_profile = self._block_profile(signal=signal, blockers=blockers)
        is_blocked = block_profile["critical_block"]

        useful_minute = self._is_useful_minute(minute)
        late_useful_minute = self._is_late_useful_minute(minute)

        is_high_observation = self._is_high_observation(
            promotion_level=promotion_level,
            panel_section=panel_section,
            panel_signal_type=panel_signal_type,
            over_candidate_level=over_candidate_level,
            entry_window=entry_window,
        )

        over_watch = self._is_over_watch(
            market=market,
            over_candidate_level=over_candidate_level,
            panel_signal_type=panel_signal_type,
            football_reading=football_reading,
            narrative_reading=narrative_reading,
            signal=signal,
        )

        under_watch = (
            market == "UNDER"
            or "UNDER" in football_reading
            or "UNDER" in narrative_reading
            or prediction_market == "UNDER"
        )

        pressure_alive = pressure_score >= 55 or offensive_volume_score >= 55 or rhythm_score >= 55
        strong_pressure_alive = pressure_score >= 65 or offensive_volume_score >= 65 or rhythm_score >= 65

        risk_ok = risk_score <= 72
        risk_good = risk_score <= 62
        data_ok = data_quality not in {"BAD", "LOW", "STALE", "OLD", "NO_DATA"}

        predictive_conflict = self._has_predictive_conflict(
            market=market,
            prediction_market=prediction_market,
            prediction_alignment=prediction_alignment,
            prediction_final_recommendation=prediction_final_recommendation,
            prediction_conflict_level=prediction_conflict_level,
            next_goal_probability=next_goal_probability,
        )

        if predictive_conflict:
            soft_warnings.append("PREDICTION_MARKET_CONFLICT")

        convergence_score = self._convergence_score(
            signal=signal,
            market=market,
            minute=minute,
            over_watch=over_watch,
            under_watch=under_watch,
            is_high_observation=is_high_observation,
            useful_minute=useful_minute,
            late_useful_minute=late_useful_minute,
            pressure_alive=pressure_alive,
            strong_pressure_alive=strong_pressure_alive,
            risk_ok=risk_ok,
            risk_good=risk_good,
            data_ok=data_ok,
            over_score=over_score,
            under_score=under_score,
            maturity_score=maturity_score,
            predictive_conflict=predictive_conflict,
            block_score=block_profile["block_score"],
        )

        if is_blocked:
            return self._blocked_result(
                blockers=blockers,
                soft_warnings=soft_warnings,
                market=market,
                convergence_score=convergence_score,
                reason=block_profile["reason"],
            )

        if block_profile["soft_block"]:
            soft_warnings.append(block_profile["reason"])

        if predictive_conflict:
            return self._result(
                activation_level="RISKY_CANDIDATE",
                activation_market=market,
                activation_score=max(min(convergence_score, 68), 50),
                activation_action="MANTENER_EN_OBSERVACION_POR_CONFLICTO",
                activation_label="CANDIDATO CON CONFLICTO PREDICTIVO",
                activation_reason=(
                    "La señal tiene soporte, pero existe conflicto entre mercado, predicción de goles "
                    "y escenario probable. No debe presentarse como señal limpia."
                ),
                can_publish=False,
                should_observe=True,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if promotion_level == "TOP_SIGNAL" or master_status == "TOP_SIGNAL":
            return self._result(
                activation_level="TOP_SIGNAL",
                activation_market=market,
                activation_score=max(convergence_score, 92),
                activation_action="MANTENER_TOP_SIGNAL",
                activation_label="TOP SIGNAL",
                activation_reason="La señal ya venía promovida como TOP y no presenta bloqueo crítico.",
                can_publish=True,
                should_observe=False,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if promotion_level == "MAIN_SIGNAL" or master_status == "MAIN_SIGNAL":
            return self._result(
                activation_level="MAIN_SIGNAL",
                activation_market=market,
                activation_score=max(convergence_score, 84),
                activation_action="MANTENER_SEÑAL_PRINCIPAL",
                activation_label="SEÑAL PRINCIPAL",
                activation_reason="La señal ya venía como principal y no presenta bloqueo crítico.",
                can_publish=True,
                should_observe=False,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if over_watch and is_high_observation and useful_minute and risk_ok and data_ok:
            if strong_pressure_alive and convergence_score >= 76:
                return self._result(
                    activation_level="STRONG_CANDIDATE",
                    activation_market="OVER",
                    activation_score=max(convergence_score, 78),
                    activation_action="PROMOVER_OVER_CANDIDATO_FUERTE",
                    activation_label="OVER CANDIDATO FUERTE",
                    activation_reason=(
                        "El partido estaba en observación alta, pero el patrón OVER muestra volumen vivo, "
                        "minuto útil y ausencia de bloqueo crítico."
                    ),
                    can_publish=False,
                    should_observe=True,
                    should_block=False,
                    blockers=[],
                    warnings=soft_warnings,
                )

            return self._result(
                activation_level="EARLY_OVER_CANDIDATE",
                activation_market="OVER",
                activation_score=max(convergence_score, 68),
                activation_action="PROMOVER_OVER_CANDIDATO_TEMPRANO",
                activation_label="OVER CANDIDATO TEMPRANO",
                activation_reason=(
                    "Hay OVER WATCH activo en observación alta. La lectura sugiere oportunidad "
                    "de gol antes de confirmación tardía."
                ),
                can_publish=False,
                should_observe=True,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if market == "OVER" and useful_minute and risk_ok and pressure_alive and convergence_score >= 72:
            return self._result(
                activation_level="STRONG_CANDIDATE",
                activation_market="OVER",
                activation_score=max(convergence_score, 74),
                activation_action="ACTIVAR_OVER_CANDIDATO",
                activation_label="OVER CANDIDATO FUERTE",
                activation_reason=(
                    "La lectura OVER tiene convergencia suficiente entre mercado, minuto útil, "
                    "presión ofensiva y ausencia de bloqueo crítico."
                ),
                can_publish=False,
                should_observe=True,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if under_watch and useful_minute and risk_good and convergence_score >= 72:
            if over_watch or pressure_alive or next_goal_probability in {"HIGH", "VERY_HIGH", "MEDIUM_HIGH"}:
                soft_warnings.append("UNDER dominante, pero con riesgo de ruptura OVER activo.")

                return self._result(
                    activation_level="RISKY_CANDIDATE",
                    activation_market="UNDER",
                    activation_score=max(convergence_score, 70),
                    activation_action="MANTENER_UNDER_CON_ALERTA",
                    activation_label="UNDER CANDIDATO CON RIESGO DE GOL",
                    activation_reason=(
                        "La lectura UNDER tiene soporte, pero existe presión, amenaza ofensiva "
                        "o riesgo de próximo gol. No se debe presentar como UNDER limpio."
                    ),
                    can_publish=False,
                    should_observe=True,
                    should_block=False,
                    blockers=[],
                    warnings=soft_warnings,
                )

            return self._result(
                activation_level="STRONG_CANDIDATE",
                activation_market="UNDER",
                activation_score=max(convergence_score, 74),
                activation_action="MANTENER_UNDER_CANDIDATO",
                activation_label="UNDER CANDIDATO FUERTE",
                activation_reason=(
                    "La lectura UNDER mantiene convergencia entre marcador, reloj, riesgo controlado "
                    "y baja señal de ruptura."
                ),
                can_publish=False,
                should_observe=True,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        if is_high_observation or block_profile["soft_block"]:
            return self._result(
                activation_level="HIGH_OBSERVATION",
                activation_market=market,
                activation_score=max(convergence_score, 58),
                activation_action="MANTENER_OBSERVACION_ALTA",
                activation_label="OBSERVACIÓN ALTA OPERATIVA",
                activation_reason=(
                    "El partido tiene elementos interesantes, pero todavía no alcanza convergencia "
                    "suficiente para subir a candidato fuerte."
                ),
                can_publish=False,
                should_observe=True,
                should_block=False,
                blockers=[],
                warnings=soft_warnings,
            )

        return self._result(
            activation_level="OBSERVATION",
            activation_market=market,
            activation_score=convergence_score,
            activation_action="OBSERVAR",
            activation_label="OBSERVACIÓN",
            activation_reason="La señal no tiene convergencia suficiente para promoción operativa.",
            can_publish=False,
            should_observe=True,
            should_block=False,
            blockers=[],
            warnings=soft_warnings,
        )

    def _convergence_score(
        self,
        signal: Dict[str, Any],
        market: str,
        minute: int,
        over_watch: bool,
        under_watch: bool,
        is_high_observation: bool,
        useful_minute: bool,
        late_useful_minute: bool,
        pressure_alive: bool,
        strong_pressure_alive: bool,
        risk_ok: bool,
        risk_good: bool,
        data_ok: bool,
        over_score: float,
        under_score: float,
        maturity_score: float,
        predictive_conflict: bool,
        block_score: float,
    ) -> int:
        score = 35

        if is_high_observation:
            score += 10
        if useful_minute:
            score += 10
        if late_useful_minute:
            score += 6
        if data_ok:
            score += 8
        if risk_good:
            score += 10
        elif risk_ok:
            score += 5
        if pressure_alive:
            score += 9
        if strong_pressure_alive:
            score += 8
        if maturity_score >= 60:
            score += 6
        if maturity_score >= 72:
            score += 6

        if market == "OVER":
            if over_score >= 45:
                score += 5
            if over_score >= 55:
                score += 7
            if over_score >= 65:
                score += 8
            if over_watch:
                score += 10

        if market == "UNDER":
            if under_score >= 55:
                score += 6
            if under_score >= 65:
                score += 7
            if under_score >= 75:
                score += 6
            if under_watch:
                score += 5

        if over_watch and over_score >= 35:
            score += 7

        if predictive_conflict:
            score -= 18

        if block_score > 0:
            score -= int(block_score * 10)

        if signal.get("entry_avoid"):
            score -= 20

        if self._txt(signal.get("clock_status")) == "BLOCKED_CLOCK":
            score -= 25

        if self._txt(signal.get("contradiction_status")) in {"CRITICAL", "HIGH", "CRITICAL_CONTRADICTION"}:
            score -= 18

        return max(0, min(100, int(score)))

    def _block_profile(self, signal: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
        text = " ".join(str(x).upper() for x in blockers)

        critical_terms = {
            "INVALID_MINUTE",
            "DATA_TOO_OLD",
            "CLOCK_FROZEN",
            "BLOCKED_CLOCK",
            "EXTREME_RISK",
            "CRITICAL_CONTRADICTION",
            "NO_REENTRY",
            "MATCH_ENDED",
            "CORRUPTED_DATA",
        }

        soft_terms = {
            "CLOCK_GUARD_NO_ENTER",
            "EL RELOJ NO AUTORIZA ENTRADA",
            "DATA_TIMESTAMP_MISSING",
            "HALFTIME_WAIT",
            "POSSIBLE_HALFTIME_PAUSE",
            "CLOCK_WARNING",
            "LOW_DATA_BUT_MAJORITY_SUPPORT",
        }

        promotion_level = self._txt(signal.get("promotion_level"))
        master_status = self._txt(signal.get("master_status"))
        panel_section = self._txt(signal.get("panel_section"))
        clock_status = self._txt(signal.get("clock_status"))
        entry_window = self._txt(signal.get("entry_window"))
        contradiction = self._txt(signal.get("contradiction_status"))

        if (
            promotion_level == "BLOCKED"
            and any(term in text for term in critical_terms)
        ):
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Bloqueo crítico real detectado.",
            }

        if (
            panel_section == "BLOCKED"
            and any(term in text for term in critical_terms)
        ):
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Panel marcado como bloqueado por causa crítica.",
            }

        if (
            "BLOCKED" in master_status
            and any(term in text for term in critical_terms)
        ):
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Master status bloqueado por causa crítica.",
            }

        if master_status == "NO_REENTRY":
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "La señal expiró y no permite reentrada.",
            }

        if clock_status == "BLOCKED_CLOCK":
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Reloj bloqueado o congelado.",
            }

        if entry_window == "AVOID" or bool(signal.get("entry_avoid")):
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 1.7,
                "reason": "Entrada marcada como evitar.",
            }

        if contradiction in {"CRITICAL", "CRITICAL_CONTRADICTION"}:
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Contradicción crítica detectada.",
            }

        if any(term in text for term in critical_terms):
            return {
                "critical_block": True,
                "soft_block": False,
                "block_score": 2.0,
                "reason": "Bloqueador crítico real detectado.",
            }

        soft_count = sum(1 for term in soft_terms if term in text)
        if soft_count > 0:
            return {
                "critical_block": False,
                "soft_block": True,
                "block_score": min(1.2, soft_count * 0.35),
                "reason": "Advertencia operativa no crítica. La señal debe observarse o revalidarse.",
            }

        if len(blockers) >= 4:
            return {
                "critical_block": False,
                "soft_block": True,
                "block_score": 1.2,
                "reason": "Múltiples advertencias acumuladas. Requiere observación.",
            }

        return {
            "critical_block": False,
            "soft_block": False,
            "block_score": 0.0,
            "reason": "",
        }

    def _has_predictive_conflict(
        self,
        market: str,
        prediction_market: str,
        prediction_alignment: str,
        prediction_final_recommendation: str,
        prediction_conflict_level: str,
        next_goal_probability: str,
    ) -> bool:
        if prediction_conflict_level in {"HIGH", "CRITICAL"}:
            return True

        if prediction_alignment in {"CONFLICT", "STRONG_CONFLICT"}:
            return True

        if market == "UNDER" and next_goal_probability in {"HIGH", "VERY_HIGH"}:
            return True

        if market == "OVER" and prediction_final_recommendation in {
            "UNDER",
            "OBSERVE_UNDER_RISK",
        }:
            return True

        if market == "UNDER" and prediction_final_recommendation in {
            "OVER",
            "OBSERVE_OVER_RISK",
        }:
            return True

        if prediction_market in {"OVER", "UNDER"} and market in {"OVER", "UNDER"}:
            if prediction_market != market and prediction_alignment in {
                "MISALIGNED",
                "CONFLICT",
                "STRONG_CONFLICT",
            }:
                return True

        return False

    def _detect_market(self, signal: Dict[str, Any]) -> str:
        values = [
            signal.get("promotion_market"),
            signal.get("panel_market"),
            signal.get("master_market"),
            signal.get("market"),
            signal.get("suggested_market"),
            signal.get("football_dominant_reading"),
            signal.get("narrative_reading_name"),
            signal.get("panel_narrative_title"),
            signal.get("prediction_market"),
            signal.get("final_market_recommendation"),
        ]

        for value in values:
            text = self._txt(value)
            if "OVER" in text:
                return "OVER"
            if "UNDER" in text or "BAJO" in text:
                return "UNDER"

        over = self._num(signal.get("over_score"))
        under = self._num(signal.get("under_score"))

        if over > under + 5:
            return "OVER"

        if under > over + 5:
            return "UNDER"

        return "OBSERVE"

    def _is_over_watch(
        self,
        market: str,
        over_candidate_level: str,
        panel_signal_type: str,
        football_reading: str,
        narrative_reading: str,
        signal: Dict[str, Any],
    ) -> bool:
        if market == "OVER":
            return True

        values = [
            over_candidate_level,
            panel_signal_type,
            football_reading,
            narrative_reading,
            self._txt(signal.get("panel_narrative_alternative")),
            self._txt(signal.get("football_alternative_reading")),
            self._txt(signal.get("narrative_alternative_message")),
            self._txt(signal.get("prediction_market")),
            self._txt(signal.get("final_market_recommendation")),
        ]

        return any("OVER" in value for value in values)

    def _is_high_observation(
        self,
        promotion_level: str,
        panel_section: str,
        panel_signal_type: str,
        over_candidate_level: str,
        entry_window: str,
    ) -> bool:
        return (
            promotion_level == "WAIT_REVALIDATION"
            or panel_section in {"OVER_HIGH_OBSERVATION", "HIGH_OBSERVATION"}
            or "HIGH_OBSERVATION" in panel_signal_type
            or over_candidate_level == "OVER_HIGH_OBSERVATION"
            or entry_window == "WAIT"
        )

    def _collect_blockers(self, signal: Dict[str, Any]) -> List[str]:
        blockers = []

        for key in ["hard_blockers", "promotion_blockers", "blockers"]:
            value = signal.get(key)
            if isinstance(value, list):
                blockers.extend([str(x) for x in value if x])

        if signal.get("entry_avoid"):
            blockers.append("Entrada marcada como evitar.")

        if self._txt(signal.get("clock_status")) == "BLOCKED_CLOCK":
            blockers.append("Reloj bloqueado o no confiable.")

        if self._txt(signal.get("contradiction_status")) in {"CRITICAL", "CRITICAL_CONTRADICTION"}:
            blockers.append("Contradicción crítica.")

        return list(dict.fromkeys(blockers))

    def _collect_warnings(self, signal: Dict[str, Any]) -> List[str]:
        warnings = []

        for key in ["soft_warnings", "promotion_warnings", "match_maturity_warnings"]:
            value = signal.get(key)
            if isinstance(value, list):
                warnings.extend([str(x) for x in value if x])

        return list(dict.fromkeys(warnings))

    def _blocked_result(
        self,
        blockers: List[str],
        soft_warnings: List[str],
        market: str,
        convergence_score: int,
        reason: str,
    ) -> Dict[str, Any]:
        return self._result(
            activation_level="BLOCKED",
            activation_market=market,
            activation_score=min(convergence_score, 35),
            activation_action="BLOQUEAR",
            activation_label="BLOQUEADO",
            activation_reason=reason or "La señal presenta bloqueo crítico y no debe promoverse.",
            can_publish=False,
            should_observe=False,
            should_block=True,
            blockers=blockers,
            warnings=soft_warnings,
        )

    def _result(
        self,
        activation_level: str,
        activation_market: str,
        activation_score: int,
        activation_action: str,
        activation_label: str,
        activation_reason: str,
        can_publish: bool,
        should_observe: bool,
        should_block: bool,
        blockers: List[str],
        warnings: List[str],
    ) -> Dict[str, Any]:
        return {
            "signal_activation_version": self.VERSION,
            "activation_role": "EVIDENCE_ONLY",
            "activation_is_official_decision": False,
            "activation_level": activation_level,
            "activation_market": activation_market,
            "activation_score": activation_score,
            "activation_action": activation_action,
            "activation_label": activation_label,
            "activation_reason": activation_reason,
            "activation_blockers": blockers,
            "activation_warnings": warnings,
            "activation_can_publish": can_publish,
            "activation_should_observe": should_observe,
            "activation_should_block": should_block,
            "panel_activation_label": activation_label,
            "panel_activation_reason": activation_reason,
        }

    def _minute(self, signal: Dict[str, Any]) -> int:
        for key in ["display_minute", "api_minute", "estimated_minute", "minute"]:
            value = signal.get(key)
            n = self._num(value)
            if n > 0:
                return int(n)
        return 0

    def _is_useful_minute(self, minute: int) -> bool:
        return 35 <= minute <= 88

    def _is_late_useful_minute(self, minute: int) -> bool:
        return 60 <= minute <= 86

    def _num(self, value: Any) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _txt(self, value: Any) -> str:
        return str(value or "").strip().upper()
