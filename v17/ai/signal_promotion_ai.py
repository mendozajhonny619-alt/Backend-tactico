from __future__ import annotations

from typing import Any, Dict, List


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _txt(value: Any) -> str:
    return str(value or "").strip().upper()


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if value is None or value == "":
        return []
    return [str(value)]


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if str(value).lower() in {"true", "1", "yes", "y", "active"}:
        return True
    return False


class SignalPromotionAI:
    """
    Capa promotora V17.

    Esta IA no reemplaza a las demás IA del sistema.

    Su función es leer el resultado final del análisis y decidir si una señal
    debe quedarse en observación o puede subir a:

    - EARLY_OVER_CANDIDATE
    - STRONG_CANDIDATE
    - MAIN_SIGNAL
    - TOP_SIGNAL

    Corrección principal:
    - Reconoce oficialmente OVER candidato temprano.
    - Evita mezclar promotion_market OVER con textos UNDER.
    - Respeta OVER WATCH cuando hay mayoría ofensiva suficiente.
    """

    VERSION = "V17_SIGNAL_PROMOTION_AI_4"

    TOP_SIGNAL_THRESHOLD = 92.0  # Umbral base para promoción TOP

    HARD_BLOCKERS = {
        "NO_REENTRY",
        "MATCH_MATURITY_BLOCK",
        "CLOCK_BLOCK",
        "BLOCKED_CLOCK",
        "DATA_INVALID",
        "CRITICAL_CONTRADICTION",
        "EXTREME_RISK",
        "RED_CARD_CHAOS",
    }

    BAD_CLOCK_STATUSES = {
        "BLOCKED_CLOCK",
        "CLOCK_BLOCKED",
        "UNSAFE_CLOCK",
        "CLOCK_UNSAFE",
    }

    BAD_DATA_STATUSES = {
        "INVALID",
        "DATA_INVALID",
        "NO_DATA",
        "VERY_LOW",
        "LOW_QUALITY_BLOCK",
        "BAD_DATA",
    }

    STRONG_CONTRADICTIONS = {
        "STRONG_CONTRADICTION",
        "CRITICAL_CONTRADICTION",
    }

    LOW_RISK_STATUSES = {
        "LOW_RISK",
        "CONTROLLED_RISK",
        "MEDIUM_LOW_RISK",
        "NORMAL_RISK",
    }

    def evaluate(
        self,
        signal: Dict[str, Any],
        match_reader: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._fallback("Señal inválida para promoción.")

        match_reader = match_reader or {}

        market = self._detect_market(signal)
        minute = _int(signal.get("api_minute") or signal.get("display_minute"), 0)

        hard_blockers = _as_list(signal.get("hard_blockers"))
        soft_warnings = _as_list(signal.get("soft_warnings"))
        maturity_warnings = _as_list(signal.get("match_maturity_warnings"))

        promotion_blockers: List[str] = []
        promotion_warnings: List[str] = []
        promotion_support: List[str] = []

        block_result = self._critical_block_check(signal, hard_blockers)
        if block_result:
            promotion_blockers.extend(block_result)

        clock_result = self._clock_check(signal)
        if clock_result:
            promotion_blockers.extend(clock_result)

        data_result = self._data_quality_check(signal)
        if data_result.get("blockers"):
            promotion_blockers.extend(data_result["blockers"])
        if data_result.get("warnings"):
            promotion_warnings.extend(data_result["warnings"])
        if data_result.get("support"):
            promotion_support.extend(data_result["support"])

        maturity_result = self._maturity_permission_check(signal)
        if maturity_result.get("blockers"):
            promotion_blockers.extend(maturity_result["blockers"])
        if maturity_result.get("warnings"):
            promotion_warnings.extend(maturity_result["warnings"])
        if maturity_result.get("support"):
            promotion_support.extend(maturity_result["support"])

        contradiction_result = self._contradiction_check(signal)
        if contradiction_result.get("blockers"):
            promotion_blockers.extend(contradiction_result["blockers"])
        if contradiction_result.get("warnings"):
            promotion_warnings.extend(contradiction_result["warnings"])
        if contradiction_result.get("support"):
            promotion_support.extend(contradiction_result["support"])

        risk_result = self._risk_check(signal)
        if risk_result.get("blockers"):
            promotion_blockers.extend(risk_result["blockers"])
        if risk_result.get("warnings"):
            promotion_warnings.extend(risk_result["warnings"])
        if risk_result.get("support"):
            promotion_support.extend(risk_result["support"])

        # --- COHERENCIA PREDICTIVA V17.3 ---
        # MatchPredictionAI ya puede detectar conflictos entre mercado, próximo gol
        # y marcador probable. PromotionAI no debe promover señales limpias cuando
        # esa capa ve contradicción.
        prediction_result = self._prediction_coherence_check(signal, market)
        if prediction_result.get("blockers"):
            promotion_blockers.extend(prediction_result["blockers"])
        if prediction_result.get("warnings"):
            promotion_warnings.extend(prediction_result["warnings"])
        if prediction_result.get("support"):
            promotion_support.extend(prediction_result["support"])

        # --- PERFIL DE BLOQUEO GRADUADO V17.3 ---
        # No todo blocker es crítico. Reloj en warning, descanso o timestamp ausente
        # debe bajar/promover a revalidación, no matar automáticamente la señal.
        blocker_profile = self._blocker_profile(signal, promotion_blockers)
        if blocker_profile.get("soft_blockers"):
            promotion_warnings.extend(blocker_profile["soft_blockers"])
        promotion_blockers = blocker_profile.get("critical_blockers", [])

        # --- FILTRO DE CALIDAD DE LIGA (V17.1) ---
        league_profile = _txt(signal.get("league_goal_profile"))
        if league_profile in {"UNKNOWN_LEAGUE", "LOW_DATA_LEAGUE", "DESCONOCIDO"}:
            promotion_warnings.append("Competencia con datos limitados. Nivel de confianza reducido.")
            # Las ligas inferiores nunca pueden ser TOP_SIGNAL por seguridad
            is_top_league = False
        else:
            is_top_league = True

        market_score = self._market_score(signal, market)
        live_score = self._live_confirmation_score(signal, market, minute)
        pre_match_score = self._pre_match_score(signal, market)
        phase_score = self._phase_score(signal, market, minute)
        maturity_score = _num(signal.get("match_maturity_score"), 0)
        evidence_confidence = max(
            _num(signal.get("market_confidence"), 0),
            _num(signal.get("prediction_confidence"), 0),
            _num(signal.get("football_confidence"), 0),
            _num(signal.get("pressure_confidence"), 0),
        )
        football_confidence = _num(signal.get("football_confidence"), 0)

        promotion_score = self._calculate_promotion_score(
            market_score=market_score,
            live_score=live_score,
            pre_match_score=pre_match_score,
            phase_score=phase_score,
            maturity_score=maturity_score,
            evidence_confidence=evidence_confidence,
            football_confidence=football_confidence,
            warning_count=len(set(promotion_warnings + soft_warnings + maturity_warnings)),
            blocker_count=len(set(promotion_blockers)),
        )

        promotion_score += _num(prediction_result.get("score_adjustment"), 0)
        promotion_score -= _num(blocker_profile.get("soft_penalty"), 0)
        promotion_score = max(0.0, min(100.0, promotion_score))

        if market_score >= 70:
            promotion_support.append(f"Lectura {market} con porcentaje competitivo.")
        if live_score >= 18:
            promotion_support.append("El live acompaña la lectura principal.")
        if pre_match_score >= 12:
            promotion_support.append("La memoria prepartido no contradice la lectura.")
        if phase_score >= 12:
            promotion_support.append("La fase del partido es compatible con la señal.")
        if maturity_score >= 65:
            promotion_support.append("La madurez de señal permite subir de nivel.")

        promotion_level = self._decide_level(
            signal=signal,
            market=market,
            minute=minute,
            promotion_score=promotion_score,
            promotion_blockers=promotion_blockers,
            promotion_warnings=promotion_warnings,
            market_score=market_score,
            live_score=live_score,
            pre_match_score=pre_match_score,
            phase_score=phase_score,
            maturity_score=maturity_score,
            prediction_result=prediction_result,
            blocker_profile=blocker_profile,
        )

        # Ajuste de rigor para 90% Winrate: Solo promovemos a TOP si es liga de calidad y score > 92
        if promotion_level == "TOP_SIGNAL":
            if not is_top_league or promotion_score < self.TOP_SIGNAL_THRESHOLD:
                promotion_level = "MAIN_SIGNAL"

        # Si existe conflicto predictivo o advertencia operativa seria, no se presenta
        # como señal limpia. Se queda en candidato/revalidación hasta nueva lectura.
        if prediction_result.get("conflict") and promotion_level in {"MAIN_SIGNAL", "TOP_SIGNAL"}:
            promotion_level = "STRONG_CANDIDATE"

        if blocker_profile.get("soft_block") and promotion_level in {"MAIN_SIGNAL", "TOP_SIGNAL"}:
            promotion_level = "WAIT_REVALIDATION"

        panel_label = self._panel_label(
            market=market,
            promotion_level=promotion_level,
        )

        action = self._action(
            promotion_level=promotion_level,
        )

        reason = self._reason(
            market=market,
            promotion_level=promotion_level,
            promotion_score=promotion_score,
            blockers=promotion_blockers,
            warnings=promotion_warnings,
            support=promotion_support,
        )

        can_publish = promotion_level in {"MAIN_SIGNAL", "TOP_SIGNAL"}

        should_observe = promotion_level in {
            "OBSERVE_ONLY",
            "WAIT_REVALIDATION",
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
        }

        return {
            "signal_promotion_version": self.VERSION,
            "promotion_role": "EVIDENCE_ONLY",
            "promotion_is_official_decision": False,
            "promotion_market": market,
            "promotion_score": round(promotion_score, 2),
            "promotion_level": promotion_level,
            "promotion_panel_label": panel_label,
            "promotion_action": action,
            "promotion_reason": reason,
            "promotion_support_points": self._unique(promotion_support)[:6],
            "promotion_warnings": self._unique(promotion_warnings)[:6],
            "promotion_blockers": self._unique(promotion_blockers)[:6],
            "promotion_can_publish": can_publish,
            "promotion_should_observe": should_observe,
            "promotion_is_main_signal": promotion_level in {"MAIN_SIGNAL", "TOP_SIGNAL"},
            "promotion_is_top_signal": promotion_level == "TOP_SIGNAL",
            "promotion_rank_class": self._rank_class(promotion_level),
            "promotion_priority": self._priority(promotion_level),
            "panel_signal_type": panel_label,
            "panel_promotion_label": panel_label,
            "panel_promotion_reason": reason,
        }

    def _prediction_coherence_check(self, signal: Dict[str, Any], market: str) -> Dict[str, Any]:
        """
        Evalúa si la predicción del partido acompaña o contradice la promoción.

        Regla central:
        - UNDER no puede promocionarse como limpio si la predicción ve próximo gol alto
          o recomienda OVER/OBSERVE_OVER_RISK.
        - OVER no puede promocionarse como limpio si la predicción ve conservación clara
          o recomienda UNDER/OBSERVE_UNDER_RISK.
        """
        warnings: List[str] = []
        blockers: List[str] = []
        support: List[str] = []

        prediction_market = _txt(signal.get("prediction_market"))
        alignment = _txt(signal.get("prediction_market_alignment"))
        final_recommendation = _txt(signal.get("final_market_recommendation"))
        conflict_level = _txt(signal.get("prediction_conflict_level"))
        next_goal_probability = _txt(signal.get("prediction_next_goal_probability"))
        prediction_confidence = _num(signal.get("prediction_confidence"), 0)

        no_goal_probability = _num(signal.get("prediction_no_goal_probability"), 0)
        one_goal_probability = _num(signal.get("prediction_one_goal_probability"), 0)
        two_plus_probability = _num(signal.get("prediction_two_plus_goal_probability"), 0)

        conflict = False
        critical_conflict = False
        score_adjustment = 0.0

        if conflict_level in {"HIGH", "CRITICAL"}:
            conflict = True
            critical_conflict = conflict_level == "CRITICAL"
            warnings.append("MatchPredictionAI detecta conflicto fuerte entre mercado y escenario probable.")
            score_adjustment -= 18 if critical_conflict else 12

        if alignment in {"CONFLICT", "STRONG_CONFLICT"}:
            conflict = True
            warnings.append("La predicción no está alineada con el mercado que se intenta promocionar.")
            score_adjustment -= 12

        if market == "UNDER":
            if next_goal_probability in {"HIGH", "VERY_HIGH"}:
                conflict = True
                warnings.append("UNDER con probabilidad alta de próximo gol. No debe ser señal limpia.")
                score_adjustment -= 16
            elif next_goal_probability == "MEDIUM_HIGH":
                warnings.append("UNDER con riesgo medio-alto de próximo gol. Requiere revalidación.")
                score_adjustment -= 8

            if final_recommendation in {"OVER", "OBSERVE_OVER_RISK"} or prediction_market == "OVER":
                conflict = True
                warnings.append("La predicción futura se inclina hacia OVER o riesgo de ruptura.")
                score_adjustment -= 14

            if no_goal_probability >= 55 and two_plus_probability <= 22:
                support.append("La predicción acompaña conservación del marcador para UNDER.")
                score_adjustment += 6

        elif market == "OVER":
            if final_recommendation in {"UNDER", "OBSERVE_UNDER_RISK"} or prediction_market == "UNDER":
                conflict = True
                warnings.append("La predicción futura se inclina hacia conservación/UNDER.")
                score_adjustment -= 14

            if next_goal_probability in {"LOW", "LOW_MEDIUM"} and no_goal_probability >= 55:
                conflict = True
                warnings.append("OVER con baja probabilidad de próximo gol y alta conservación.")
                score_adjustment -= 14

            if two_plus_probability >= 38 or next_goal_probability in {"HIGH", "VERY_HIGH"}:
                support.append("La predicción acompaña riesgo de más goles para OVER.")
                score_adjustment += 6

        if prediction_confidence >= 70 and not conflict:
            support.append("MatchPredictionAI acompaña la promoción con confianza útil.")
            score_adjustment += 4

        return {
            "blockers": blockers,
            "warnings": warnings,
            "support": support,
            "conflict": conflict,
            "critical_conflict": critical_conflict,
            "score_adjustment": score_adjustment,
        }

    def _blocker_profile(self, signal: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
        """
        Separa bloqueadores críticos de advertencias operativas.
        Esto evita que CLOCK_GUARD_NO_ENTER, HALFTIME_WAIT o timestamp faltante
        maten automáticamente una señal con lectura fuerte.
        """
        critical: List[str] = []
        soft: List[str] = []

        text_items = [str(item) for item in blockers]
        joined = " ".join(_txt(item) for item in text_items)

        critical_terms = {
            "NO_REENTRY",
            "MATCH_ENDED",
            "INVALID_MINUTE",
            "DATA_TOO_OLD",
            "CLOCK_FROZEN",
            "BLOCKED_CLOCK",
            "DATA_INVALID",
            "CRITICAL_CONTRADICTION",
            "EXTREME_RISK",
            "RED_CARD_CHAOS",
            "CORRUPTED_DATA",
        }

        soft_terms = {
            "CLOCK_GUARD_NO_ENTER",
            "EL RELOJ NO AUTORIZA ENTRADA",
            "HALFTIME_WAIT",
            "POSSIBLE_HALFTIME_PAUSE",
            "DATA_TIMESTAMP_MISSING",
            "CLOCK_WARNING",
            "WAIT_CONFIRMATION",
            "MATCHMATURITYAI EXIGE REVALIDACIÓN",
            "MATCHMATURITYAI DEGRADÓ",
            "PANORAMA",
        }

        clock_status = _txt(signal.get("clock_status"))
        master_status = _txt(signal.get("master_status"))
        risk_status = _txt(signal.get("risk_status"))
        contradiction = _txt(signal.get("contradiction_status"))

        for item in text_items:
            item_text = _txt(item)
            if any(term in item_text for term in critical_terms):
                critical.append(item)
            elif any(term in item_text for term in soft_terms):
                soft.append(item)
            else:
                # Bloqueos genéricos heredados del Master/Panel se tratan como suaves
                # salvo que el estado real confirme criticidad.
                soft.append(item)

        if clock_status == "BLOCKED_CLOCK":
            critical.append("Reloj bloqueado o congelado.")

        if "BLOCKED" in master_status and any(term in joined for term in critical_terms):
            critical.append("Master mantiene bloqueo crítico real.")

        if risk_status == "EXTREME_RISK":
            critical.append("Riesgo extremo confirmado.")

        if contradiction in {"CRITICAL_CONTRADICTION", "CRITICAL"}:
            critical.append("Contradicción crítica confirmada.")

        soft_penalty = min(12.0, len(set(soft)) * 3.0)

        return {
            "critical_blockers": self._unique(critical),
            "soft_blockers": self._unique(soft),
            "soft_block": bool(soft) and not bool(critical),
            "soft_penalty": soft_penalty,
        }

    def _detect_market(self, signal: Dict[str, Any]) -> str:
        """
        Detecta mercado principal para promoción.

        Prioridad corregida:
        - Si existe OVER WATCH fuerte, se respeta OVER aunque la lectura base venga como UNDER.
        - Evita que el panel diga UNDER EN OBSERVACIÓN cuando realmente se está viendo OVER temprano.
        """

        over_candidate_active = _bool(signal.get("over_candidate_active"))
        over_candidate_level = _txt(signal.get("over_candidate_level"))
        over_support_score = _num(signal.get("over_support_score"), 0)
        over_support_ratio = _num(signal.get("over_support_ratio"), 0)
        panel_section = _txt(signal.get("panel_section"))
        master_action = _txt(signal.get("master_action"))
        master_reason = _txt(signal.get("master_reason"))
        recommended_message = _txt(signal.get("recommended_panel_message"))

        if (
            over_candidate_active
            or over_candidate_level in {
                "OVER_HIGH_OBSERVATION",
                "OVER_STRONG_CANDIDATE",
                "EARLY_OVER_CANDIDATE",
            }
            or over_support_score >= 15
            or over_support_ratio >= 0.75
            or "OVER_HIGH" in panel_section
            or "OVER WATCH" in master_reason
            or "OVER_CANDIDATO" in master_action
            or "OVER" in recommended_message
        ):
            return "OVER"

        candidates = [
            signal.get("promotion_market"),
            signal.get("activation_market"),
            signal.get("narrative_reading_name"),
            signal.get("football_dominant_reading"),
            signal.get("panel_market"),
            signal.get("master_market"),
            signal.get("market"),
            signal.get("suggested_market"),
        ]

        for item in candidates:
            value = _txt(item)
            if "OVER" in value:
                return "OVER"
            if "UNDER" in value or "BAJO" in value:
                return "UNDER"

        over = _num(signal.get("over_score"), 0)
        under = _num(signal.get("under_score"), 0)

        if over > under + 5:
            return "OVER"
        if under > over + 5:
            return "UNDER"

        return "NO_BET"

    def _critical_block_check(
        self,
        signal: Dict[str, Any],
        hard_blockers: List[str],
    ) -> List[str]:
        blockers: List[str] = []

        master_status = _txt(signal.get("master_status"))
        master_action = _txt(signal.get("master_action"))
        should_block = bool(signal.get("should_block"))

        if should_block:
            blockers.append("La señal mantiene bloqueo interno activo.")

        if "BLOCKED" in master_status:
            blockers.append("La decisión maestra mantiene estado bloqueado.")

        if master_action in {"NO_OPERAR", "NO_BET", "AVOID"}:
            blockers.append("La acción maestra no permite operar.")

        for item in hard_blockers:
            normalized = _txt(item)
            if normalized in self.HARD_BLOCKERS:
                blockers.append(f"Bloqueador crítico activo: {normalized}.")

        return blockers

    def _clock_check(self, signal: Dict[str, Any]) -> List[str]:
        blockers: List[str] = []

        clock_status = _txt(signal.get("clock_status"))
        clock_can_enter = signal.get("clock_can_enter")

        if clock_status in self.BAD_CLOCK_STATUSES:
            blockers.append("Reloj no confiable para promover señal.")

        if clock_can_enter is False:
            blockers.append("El reloj no autoriza entrada.")

        return blockers

    def _data_quality_check(self, signal: Dict[str, Any]) -> Dict[str, List[str]]:
        blockers: List[str] = []
        warnings: List[str] = []
        support: List[str] = []

        data_quality = _txt(signal.get("data_quality"))
        data_status = _txt(signal.get("data_quality_status"))
        data_valid = signal.get("data_valid")
        stats_source = _txt(signal.get("stats_source"))

        if data_valid is False:
            blockers.append("Datos inválidos. No se promueve señal.")

        if data_quality in self.BAD_DATA_STATUSES or data_status in self.BAD_DATA_STATUSES:
            blockers.append("Calidad de datos demasiado baja para señal principal.")

        if data_quality in {"LOW", "LOW_DATA", "PARTIAL", "MEDIUM_LOW"}:
            warnings.append("Datos parciales. La señal solo puede subir si el live confirma fuerte.")

        if stats_source in {"NO_STATS", "EMPTY", "UNKNOWN"}:
            warnings.append("Fuente estadística débil o incompleta.")

        if not blockers and data_valid is not False:
            support.append("Datos mínimos aptos para evaluación de promoción.")

        return {
            "blockers": blockers,
            "warnings": warnings,
            "support": support,
        }

    def _maturity_permission_check(self, signal: Dict[str, Any]) -> Dict[str, List[str]]:
        blockers: List[str] = []
        warnings: List[str] = []
        support: List[str] = []

        permission = _txt(signal.get("match_maturity_entry_permission"))
        operative_state = _txt(signal.get("narrative_operative_state"))
        should_demote = bool(signal.get("match_maturity_should_demote"))
        no_strong_under = bool(signal.get("match_maturity_no_strong_under"))

        if permission == "BLOCK_ENTRY":
            blockers.append("MatchMaturityAI bloquea entrada.")

        if permission == "WAIT_REVALIDATION":
            warnings.append("MatchMaturityAI exige revalidación antes de señal principal.")

        if permission == "PANORAMA_ONLY":
            warnings.append("La lectura está en panorama. No puede ser señal principal todavía.")

        if operative_state in {"BLOCKED", "REVALIDATION", "PANORAMA"}:
            warnings.append(f"Estado operativo actual: {operative_state}.")

        if should_demote:
            warnings.append("MatchMaturityAI degradó la señal.")

        if no_strong_under:
            warnings.append("MatchMaturityAI impide UNDER fuerte en esta fase.")

        if permission in {"ALLOW_STRONG_SIGNAL", "ALLOW_CANDIDATE"}:
            support.append("MatchMaturityAI permite promoción controlada.")

        return {
            "blockers": blockers,
            "warnings": warnings,
            "support": support,
        }

    def _contradiction_check(self, signal: Dict[str, Any]) -> Dict[str, List[str]]:
        blockers: List[str] = []
        warnings: List[str] = []
        support: List[str] = []

        status = _txt(signal.get("contradiction_status"))

        if status in self.STRONG_CONTRADICTIONS:
            blockers.append("Contradicción fuerte activa.")

        elif status in {"MEDIUM_CONTRADICTION", "PARTIAL_CONTRADICTION"}:
            warnings.append("Contradicción parcial. Requiere prudencia.")

        elif status in {"NO_CONTRADICTION", "CLEAR", "OK"}:
            support.append("No hay contradicción interna relevante.")

        return {
            "blockers": blockers,
            "warnings": warnings,
            "support": support,
        }

    def _risk_check(self, signal: Dict[str, Any]) -> Dict[str, List[str]]:
        blockers: List[str] = []
        warnings: List[str] = []
        support: List[str] = []

        risk_status = _txt(signal.get("risk_status"))
        risk_score = _num(signal.get("risk_score"), 0)

        if risk_status == "EXTREME_RISK" or risk_score >= 85:
            blockers.append("Riesgo extremo. No se promueve señal.")

        elif risk_status == "HIGH_RISK" or risk_score >= 70:
            warnings.append("Riesgo alto. No conviene señal principal sin confirmación extra.")

        elif risk_status in self.LOW_RISK_STATUSES or risk_score <= 45:
            support.append("Riesgo operativo controlado.")

        return {
            "blockers": blockers,
            "warnings": warnings,
            "support": support,
        }

    def _market_score(self, signal: Dict[str, Any], market: str) -> float:
        if market == "OVER":
            over_support_ratio = _num(signal.get("over_support_ratio"), 0)

            if over_support_ratio <= 1:
                over_support_ratio *= 100

            values = [
                _num(signal.get("over_score"), 0),
                over_support_ratio,
                _num(signal.get("over_support_score"), 0) * 5,
                _num(signal.get("over_pre_match_score"), 0),
            ]

            return max(values)

        if market == "UNDER":
            values = [
                _num(signal.get("under_score"), 0),
                _num(signal.get("under_pre_match_score"), 0),
            ]

            return max(values)

        return 0.0

    def _live_confirmation_score(
        self,
        signal: Dict[str, Any],
        market: str,
        minute: int,
    ) -> float:
        pressure = _num(signal.get("pressure_score"), 0)
        rhythm = _num(signal.get("rhythm_score"), 0)
        offensive_volume = _num(
            signal.get("offensive_volume_score")
            or signal.get("match_maturity_live_volume_score"),
            0,
        )

        shots = _num(signal.get("shots"), 0)
        shots_on_target = _num(signal.get("shots_on_target"), 0)
        dangerous_attacks = _num(signal.get("dangerous_attacks"), 0)
        corners = _num(signal.get("corners"), 0)
        xg = _num(signal.get("xG") or signal.get("xg"), 0)

        score = 0.0

        if market == "OVER":
            if offensive_volume >= 65:
                score += 10
            elif offensive_volume >= 45:
                score += 7
            elif offensive_volume >= 30:
                score += 4

            if pressure >= 60:
                score += 8

            if rhythm >= 55:
                score += 6

            if shots_on_target >= 3:
                score += 8
            elif shots_on_target >= 2:
                score += 5
            elif shots_on_target >= 1:
                score += 3

            if shots >= 12:
                score += 7
            elif shots >= 8:
                score += 5
            elif shots >= 5:
                score += 3

            if dangerous_attacks >= 35:
                score += 5

            if corners >= 5:
                score += 3
            elif corners >= 3:
                score += 2

            if xg >= 1.2:
                score += 8
            elif xg >= 0.8:
                score += 4

            if 35 <= minute <= 55 and shots >= 6 and shots_on_target >= 2:
                score += 4

        elif market == "UNDER":
            total_goals = _num(signal.get("total_goals"), 0)
            over_candidate_active = bool(signal.get("over_candidate_active"))
            over_level = _txt(signal.get("over_candidate_level"))

            if offensive_volume <= 40:
                score += 10

            if pressure <= 45:
                score += 8

            if rhythm <= 45:
                score += 6

            if shots_on_target <= 2:
                score += 6

            if xg <= 0.8:
                score += 6

            if dangerous_attacks <= 30:
                score += 4

            if minute >= 65 and total_goals <= 2:
                score += 8

            if not over_candidate_active and over_level not in {
                "OVER_HIGH_OBSERVATION",
                "OVER_STRONG_CANDIDATE",
            }:
                score += 6

        return min(score, 40.0)

    def _pre_match_score(self, signal: Dict[str, Any], market: str) -> float:
        available = bool(signal.get("pre_match_available"))

        if not available:
            return 4.0

        league_profile = _txt(signal.get("league_goal_profile"))
        team_profile = _txt(signal.get("team_goal_profile"))

        over_support = _txt(signal.get("over_support_pre_match"))
        under_support = _txt(signal.get("under_support_pre_match"))

        over_pre = _num(signal.get("over_pre_match_score"), 0)
        under_pre = _num(signal.get("under_pre_match_score"), 0)

        score = 0.0

        if market == "OVER":
            if over_support in {"YES", "TRUE", "SUPPORTED", "HIGH"}:
                score += 8
            if over_pre >= 65:
                score += 8
            if league_profile in {"OPEN_LEAGUE", "VERY_OPEN_LEAGUE"}:
                score += 5
            if team_profile in {"OPEN_TEAMS", "OVER_TEAMS", "HIGH_GOAL_TEAMS"}:
                score += 5
            if under_pre >= 70:
                score -= 6

        elif market == "UNDER":
            if under_support in {"YES", "TRUE", "SUPPORTED", "HIGH"}:
                score += 8
            if under_pre >= 65:
                score += 8
            if league_profile in {"DEFENSIVE_LEAGUE", "BALANCED_LEAGUE"}:
                score += 5
            if team_profile in {"DEFENSIVE_TEAMS", "UNDER_TEAMS", "LOW_GOAL_TEAMS"}:
                score += 5
            if over_pre >= 70 or league_profile == "VERY_OPEN_LEAGUE":
                score -= 6

        return max(0.0, min(score, 25.0))

    def _phase_score(self, signal: Dict[str, Any], market: str, minute: int) -> float:
        total_goals = _num(signal.get("total_goals"), 0)
        score = 0.0

        if market == "OVER":
            if 50 <= minute <= 75:
                score += 12
            elif 35 <= minute < 50:
                score += 10
            elif 25 <= minute < 35:
                score += 6
            elif 76 <= minute <= 85:
                score += 6
            elif minute < 25:
                score += 3

            if total_goals == 0 and minute >= 55:
                score += 3

            if total_goals >= 1 and 35 <= minute <= 80:
                score += 3

        elif market == "UNDER":
            if 68 <= minute <= 82:
                score += 15
            elif 60 <= minute < 68:
                score += 10
            elif 45 <= minute < 60:
                score += 6
            elif 83 <= minute <= 90:
                score += 5
            elif minute < 35:
                score -= 6

            if total_goals <= 1 and minute >= 65:
                score += 4

            if total_goals >= 3 and minute < 70:
                score -= 5

        return max(0.0, min(score, 20.0))

    def _calculate_promotion_score(
        self,
        market_score: float,
        live_score: float,
        pre_match_score: float,
        phase_score: float,
        maturity_score: float,
        evidence_confidence: float,
        football_confidence: float,
        warning_count: int,
        blocker_count: int,
    ) -> float:
        score = 0.0

        score += min(market_score, 100) * 0.25
        score += live_score
        score += pre_match_score
        score += phase_score
        score += min(maturity_score, 100) * 0.15
        score += min(evidence_confidence, 100) * 0.08
        score += min(football_confidence, 100) * 0.07

        score -= warning_count * 4
        score -= blocker_count * 25

        return max(0.0, min(score, 100.0))

    def _decide_level(
        self,
        signal: Dict[str, Any],
        market: str,
        minute: int,
        promotion_score: float,
        promotion_blockers: List[str],
        promotion_warnings: List[str],
        market_score: float,
        live_score: float,
        pre_match_score: float,
        phase_score: float,
        maturity_score: float,
        prediction_result: Dict[str, Any] | None = None,
        blocker_profile: Dict[str, Any] | None = None,
    ) -> str:
        permission = _txt(signal.get("match_maturity_entry_permission"))
        data_quality = _txt(signal.get("data_quality"))
        risk_status = _txt(signal.get("risk_status"))
        prediction_result = prediction_result or {}
        blocker_profile = blocker_profile or {}

        if prediction_result.get("critical_conflict"):
            return "WAIT_REVALIDATION"

        if blocker_profile.get("soft_block") and promotion_score < 82:
            return "WAIT_REVALIDATION"

        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_candidate_level = _txt(signal.get("over_candidate_level"))
        over_support_score = _num(signal.get("over_support_score"), 0)
        over_support_ratio = _num(signal.get("over_support_ratio"), 0)
        over_market_gap = _num(signal.get("over_market_gap"), 0)
        panel_section = _txt(signal.get("panel_section"))

        if market == "NO_BET":
            return "OBSERVE_ONLY"

        if promotion_blockers:
            return "BLOCKED"

        if permission == "BLOCK_ENTRY":
            return "BLOCKED"

        early_over_watch = (
            market == "OVER"
            and (
                over_candidate_active
                or over_candidate_level in {
                    "OVER_HIGH_OBSERVATION",
                    "OVER_STRONG_CANDIDATE",
                    "EARLY_OVER_CANDIDATE",
                }
                or "OVER_HIGH" in panel_section
            )
            and (
                over_support_score >= 15
                or over_support_ratio >= 0.75
            )
            and 25 <= minute <= 55
        )

        if early_over_watch:
            if promotion_score >= 62 and live_score >= 18 and maturity_score >= 55:
                return "STRONG_CANDIDATE"

            if over_support_score >= 16 or over_support_ratio >= 0.80:
                return "EARLY_OVER_CANDIDATE"

            if over_market_gap > -45:
                return "EARLY_OVER_CANDIDATE"

            return "OBSERVE_ONLY"

        if permission in {"WAIT_REVALIDATION", "PANORAMA_ONLY"}:
            if promotion_score >= 72 and live_score >= 22 and not self._has_strong_warning(promotion_warnings):
                return "STRONG_CANDIDATE"

            return "WAIT_REVALIDATION"

        # --- ASCENSO CONTROLADO V17.4 ---
        # Si una oportunidad ya llegó a candidato fuerte / observación alta y la
        # lectura está limpia, no debe quedarse estancada. Esta ruta permite que
        # las mejores oportunidades del momento suban a señal directa sin volver
        # agresivo el sistema ni romper la jerarquía de MasterDecision.
        if self._elite_opportunity_to_main_signal(
            signal=signal,
            market=market,
            promotion_score=promotion_score,
            promotion_warnings=promotion_warnings,
            market_score=market_score,
            live_score=live_score,
            pre_match_score=pre_match_score,
            phase_score=phase_score,
            maturity_score=maturity_score,
            prediction_result=prediction_result,
            data_quality=data_quality,
            risk_status=risk_status,
        ):
            return "MAIN_SIGNAL"

        if data_quality in {"LOW", "LOW_DATA", "PARTIAL", "MEDIUM_LOW"}:
            if promotion_score >= 82 and live_score >= 28 and maturity_score >= 70:
                return "STRONG_CANDIDATE"

            return "OBSERVE_ONLY"

        if risk_status == "HIGH_RISK":
            if promotion_score >= 82 and live_score >= 26 and pre_match_score >= 10:
                return "STRONG_CANDIDATE"

            return "OBSERVE_ONLY"

        if promotion_score >= 88 and live_score >= 25 and maturity_score >= 75 and phase_score >= 10:
            return "TOP_SIGNAL"

        if promotion_score >= 76 and live_score >= 20 and maturity_score >= 65:
            return "MAIN_SIGNAL"

        if promotion_score >= 62 and market_score >= 65 and maturity_score >= 55:
            return "STRONG_CANDIDATE"

        if promotion_score >= 50:
            return "OBSERVE_ONLY"

        return "OBSERVE_ONLY"


    def _elite_opportunity_to_main_signal(
        self,
        signal: Dict[str, Any],
        market: str,
        promotion_score: float,
        promotion_warnings: List[str],
        market_score: float,
        live_score: float,
        pre_match_score: float,
        phase_score: float,
        maturity_score: float,
        prediction_result: Dict[str, Any],
        data_quality: str,
        risk_status: str,
    ) -> bool:
        """
        Promoción fina para oportunidades élite.

        Objetivo:
        - Permitir que una oportunidad/candidato fuerte suba a señal directa
          cuando ya cumple lo importante.
        - Evitar que todo quede eternamente en CANDIDATO/OPORTUNIDAD.
        - No saltarse bloqueos críticos, riesgo alto ni conflicto predictivo.
        """
        if market not in {"OVER", "UNDER"}:
            return False

        if prediction_result.get("conflict") or prediction_result.get("critical_conflict"):
            return False

        if risk_status in {"HIGH_RISK", "EXTREME_RISK"}:
            return False

        if self._has_strong_warning(promotion_warnings):
            return False

        clock_status = _txt(signal.get("clock_status"))
        clock_can_enter = signal.get("clock_can_enter")
        if clock_status in self.BAD_CLOCK_STATUSES or clock_can_enter is False:
            return False

        # En datos limitados se permite vivir como candidato fuerte, pero solo
        # sube directo si el live es especialmente fuerte.
        low_data = data_quality in {"LOW", "LOW_DATA", "PARTIAL", "MEDIUM_LOW"}
        if low_data and not (promotion_score >= 82 and live_score >= 30 and maturity_score >= 70):
            return False

        # Detecta si el sistema ya la trae marcada como oportunidad fuerte.
        texts = " ".join(
            _txt(signal.get(key))
            for key in [
                "promotion_level",
                "activation_level",
                "activation_status",
                "panel_section",
                "panel_signal_type",
                "recommended_panel_message",
                "narrative_operative_state",
                "master_action",
                "master_status",
                "over_candidate_level",
            ]
        )

        opportunity_hint = any(
            token in texts
            for token in {
                "STRONG_CANDIDATE",
                "CANDIDATO FUERTE",
                "HIGH_OBSERVATION",
                "OBSERVACIÓN ALTA",
                "OPPORTUNITY",
                "OPORTUNIDAD",
                "EARLY_OVER_CANDIDATE",
                "OVER_STRONG_CANDIDATE",
                "OVER_HIGH_OBSERVATION",
            }
        )

        confidence = max(
            _num(signal.get("master_confidence"), 0),
            _num(signal.get("football_confidence"), 0),
            _num(signal.get("prediction_confidence"), 0),
            _num(signal.get("confidence"), 0),
        )

        next_goal = _txt(signal.get("prediction_next_goal_probability"))
        final_recommendation = _txt(signal.get("final_market_recommendation"))
        prediction_market = _txt(signal.get("prediction_market"))

        prediction_supports_market = (
            final_recommendation == market
            or prediction_market == market
            or (market == "OVER" and next_goal in {"HIGH", "VERY_HIGH", "MEDIUM_HIGH"})
            or (market == "UNDER" and next_goal in {"LOW", "LOW_MEDIUM", "MEDIUM"})
        )

        core_clean = (
            promotion_score >= 70
            and market_score >= 65
            and live_score >= 18
            and maturity_score >= 60
            and phase_score >= 6
            and confidence >= 60
        )

        strong_clean = (
            promotion_score >= 74
            and live_score >= 20
            and maturity_score >= 62
            and confidence >= 65
        )

        # Ruta 1: ya venía como oportunidad/candidato fuerte y la predicción acompaña.
        if opportunity_hint and core_clean and prediction_supports_market:
            return True

        # Ruta 2: lectura muy limpia aunque no venga etiquetada como candidato fuerte.
        if strong_clean and market_score >= 70 and not low_data:
            return True

        return False

    def _has_strong_warning(self, warnings: List[str]) -> bool:
        joined = " ".join(_txt(item) for item in warnings)

        strong_terms = [
            "CONTRADICCIÓN",
            "CONTRADICTION",
            "RIESGO ALTO",
            "HIGH RISK",
            "DATOS INVÁLIDOS",
            "RELOJ",
            "BLOQUE",
            "BLOCK",
        ]

        return any(term in joined for term in strong_terms)

    def _panel_label(self, market: str, promotion_level: str) -> str:
        if promotion_level == "TOP_SIGNAL":
            return f"{market} TOP SIGNAL"

        if promotion_level == "MAIN_SIGNAL":
            return f"{market} SEÑAL PRINCIPAL"

        if promotion_level == "STRONG_CANDIDATE":
            return f"{market} CANDIDATO FUERTE"

        if promotion_level == "EARLY_OVER_CANDIDATE":
            return "OVER CANDIDATO TEMPRANO"

        if promotion_level == "WAIT_REVALIDATION":
            return f"{market} EN REVALIDACIÓN"

        if promotion_level == "BLOCKED":
            return "SEÑAL BLOQUEADA"

        if market == "OVER":
            return "OVER EN OBSERVACIÓN"

        if market == "UNDER":
            return "UNDER EN OBSERVACIÓN"

        return "OBSERVACIÓN"

    def _action(self, promotion_level: str) -> str:
        if promotion_level == "TOP_SIGNAL":
            return "PRIORIZAR_COMO_TOP_SIGNAL"

        if promotion_level == "MAIN_SIGNAL":
            return "MOSTRAR_COMO_SEÑAL_PRINCIPAL"

        if promotion_level == "STRONG_CANDIDATE":
            return "MOSTRAR_COMO_CANDIDATO_FUERTE"

        if promotion_level == "EARLY_OVER_CANDIDATE":
            return "MOSTRAR_COMO_OVER_CANDIDATO_TEMPRANO"

        if promotion_level == "WAIT_REVALIDATION":
            return "ESPERAR_REVALIDACION"

        if promotion_level == "BLOCKED":
            return "NO_OPERAR"

        return "OBSERVAR"

    def _reason(
        self,
        market: str,
        promotion_level: str,
        promotion_score: float,
        blockers: List[str],
        warnings: List[str],
        support: List[str],
    ) -> str:
        if promotion_level == "BLOCKED":
            detail = blockers[0] if blockers else "Existe bloqueo crítico."
            return f"La señal no puede promoverse. {detail}"

        if promotion_level == "TOP_SIGNAL":
            return (
                f"La lectura {market} alcanza nivel TOP porque el soporte live, "
                "la madurez, el riesgo y la fase del partido coinciden con suficiente fuerza."
            )

        if promotion_level == "MAIN_SIGNAL":
            return (
                f"La lectura {market} sube a señal principal porque supera el umbral operativo "
                "y no presenta bloqueos críticos."
            )

        if promotion_level == "STRONG_CANDIDATE":
            return (
                f"La lectura {market} sube a candidato fuerte porque tiene soporte relevante, "
                "aunque todavía requiere seguimiento antes de considerarse top."
            )

        if promotion_level == "EARLY_OVER_CANDIDATE":
            return (
                "La lectura OVER sube a candidato temprano porque existe OVER WATCH activo, "
                "volumen ofensivo medible y riesgo de ruptura antes de una confirmación tardía."
            )

        if promotion_level == "WAIT_REVALIDATION":
            detail = warnings[0] if warnings else "La señal requiere confirmación adicional."
            return f"La lectura {market} necesita revalidación. {detail}"

        if support:
            return (
                f"La lectura {market} existe, pero permanece en observación porque todavía "
                f"no alcanza promoción suficiente. Puntaje de promoción: {promotion_score:.0f}."
            )

        return "La señal permanece en observación porque no reúne respaldo suficiente para subir."

    def _rank_class(self, promotion_level: str) -> str:
        if promotion_level == "TOP_SIGNAL":
            return "top_signal"

        if promotion_level == "MAIN_SIGNAL":
            return "main_signal"

        if promotion_level == "STRONG_CANDIDATE":
            return "strong_candidate"

        if promotion_level == "EARLY_OVER_CANDIDATE":
            return "early_over_candidate"

        if promotion_level == "WAIT_REVALIDATION":
            return "revalidation"

        if promotion_level == "BLOCKED":
            return "blocked"

        return "observe"

    def _priority(self, promotion_level: str) -> int:
        if promotion_level == "TOP_SIGNAL":
            return 100

        if promotion_level == "MAIN_SIGNAL":
            return 85

        if promotion_level == "STRONG_CANDIDATE":
            return 70

        if promotion_level == "EARLY_OVER_CANDIDATE":
            return 62

        if promotion_level == "WAIT_REVALIDATION":
            return 45

        if promotion_level == "BLOCKED":
            return 0

        return 30

    def _unique(self, values: List[str]) -> List[str]:
        seen = set()
        result = []

        for value in values:
            clean = str(value).strip()

            if not clean:
                continue

            key = clean.upper()

            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result

    def _fallback(self, reason: str) -> Dict[str, Any]:
        return {
            "signal_promotion_version": self.VERSION,
            "promotion_role": "EVIDENCE_ONLY",
            "promotion_is_official_decision": False,
            "promotion_market": "NO_BET",
            "promotion_score": 0,
            "promotion_level": "OBSERVE_ONLY",
            "promotion_panel_label": "OBSERVACIÓN",
            "promotion_action": "OBSERVAR",
            "promotion_reason": reason,
            "promotion_support_points": [],
            "promotion_warnings": [reason],
            "promotion_blockers": [],
            "promotion_can_publish": False,
            "promotion_should_observe": True,
            "promotion_is_main_signal": False,
            "promotion_is_top_signal": False,
            "promotion_rank_class": "observe",
            "promotion_priority": 30,
            "panel_signal_type": "OBSERVACIÓN",
            "panel_promotion_label": "OBSERVACIÓN",
            "panel_promotion_reason": reason,
        }
