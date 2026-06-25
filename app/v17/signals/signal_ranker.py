from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.v17.core.constants import MAX_PUBLISHED_SIGNALS, RANK_WEIGHTS


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


def normalize_market(value: Any) -> str:
    text = str(value or "").upper()

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    if "SOBRE" in text:
        return "OVER"

    if "BAJO" in text:
        return "UNDER"

    return "OTHER"


class SignalRanker:
    """
    Ranking élite V17.

    Reglas:
    - No fuerza 6 señales.
    - Publica máximo 6 señales.
    - Si solo hay 1 señal buena, muestra 1.
    - Si una señal falla filtro principal, no puede ser PREMIUM ni FUERTE.
    - Si falla filtro principal crítico, pasa a OBSERVE.
    - UNDER es más exigente porque un gol aislado rompe la lectura.
    - OVER puede subir si hay volumen ofensivo real, ritmo y presión.
    - La predicción de resultado no decide sola, pero sí puede degradar o reforzar.
    """

    def rank(self, analyzed_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        publishable: List[Dict[str, Any]] = []
        observe: List[Dict[str, Any]] = []
        no_bet: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for source in analyzed_matches or []:
            if not isinstance(source, dict):
                continue

            item = dict(source)

            status = str(
                item.get("official_status")
                or item.get("master_status")
                or "NO_BET"
            ).upper()

            if "official_can_publish" in item:
                can_publish = bool(item.get("official_can_publish"))
            else:
                can_publish = bool(item.get("can_publish"))

            if can_publish:
                publishable.append(item)
            elif status in {"BLOCKED", "NO_REENTRY"}:
                blocked.append(item)
            elif status == "NO_BET":
                no_bet.append(item)
            else:
                observe.append(item)

        publishable = sorted(
            publishable,
            key=self._sort_key,
            reverse=True,
        )
        observe = sorted(observe, key=self._sort_key, reverse=True)
        no_bet = sorted(no_bet, key=self._sort_key, reverse=True)
        blocked = sorted(blocked, key=self._sort_key, reverse=True)

        top_signals = publishable[:MAX_PUBLISHED_SIGNALS]

        for index, item in enumerate(top_signals, start=1):
            item["elite_position"] = index
            item["published"] = True
            item["panel_section"] = "TOP_SIGNAL"

        for item in observe:
            item["published"] = False
            item["panel_section"] = (
                item.get("panel_section")
                or "OBSERVE"
            )

        for item in no_bet:
            item["published"] = False
            item["panel_section"] = "NO_BET"

        for item in blocked:
            item["published"] = False
            item["panel_section"] = "BLOCKED"

        all_analyzed = top_signals + observe + no_bet + blocked

        return {
            "top_signals": top_signals,
            "observe": observe,
            "no_bet": no_bet,
            "blocked": blocked,
            "all_analyzed": all_analyzed,
            "summary": {
                "published_count": len(top_signals),
                "observe_count": len(observe),
                "no_bet_count": len(no_bet),
                "blocked_count": len(blocked),
                "max_allowed": MAX_PUBLISHED_SIGNALS,
                "by_competition_tier": self._summary_by_competition_tier(
                    all_analyzed
                ),
                "published_by_competition_tier": (
                    self._summary_by_competition_tier(top_signals)
                ),
            },
        }

    def _score_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        signal = dict(item)
        signal = self._attach_market_direction(signal)

        master_confidence = safe_float(signal.get("master_confidence"), 0.0)
        prediction_confidence = safe_float(signal.get("prediction_confidence"), 0.0)
        market_confidence = safe_float(signal.get("market_confidence"), 0.0)
        tactical_score = safe_float(signal.get("tactical_score"), 0.0)
        offensive_volume_score = safe_float(signal.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(signal.get("offensive_depth_score"), 0.0)
        pressure_score = safe_float(signal.get("pressure_score"), 0.0)
        rhythm_score = safe_float(signal.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(signal.get("goal_need_score"), 0.0)
        risk_score = safe_float(signal.get("risk_score"), 0.0)
        contradiction_score = safe_float(signal.get("contradiction_score"), 0.0)
        signal_life_penalty = safe_float(signal.get("signal_life_penalty"), 0.0)

        competition_tier = str(signal.get("competition_tier") or "").upper()
        competition_weight = safe_float(signal.get("competition_weight"), 0.0)
        world_cup_flag = bool(signal.get("world_cup_flag"))
        national_team_flag = bool(signal.get("national_team_flag"))
        major_tournament_flag = bool(signal.get("major_tournament_flag"))

        over_score = safe_float(signal.get("over_score"), 0.0)
        under_score = safe_float(signal.get("under_score"), 0.0)
        score_hold_probability = safe_float(signal.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(signal.get("under_transition_score"), 0.0)
        false_pressure_risk = safe_float(signal.get("false_pressure_risk"), 0.0)

        soft_warnings = signal.get("soft_warnings", []) or []
        failed_secondary_filters = signal.get("failed_secondary_filters", []) or []

        primary_failures = self._extract_primary_failures(soft_warnings)
        has_primary_failure = len(primary_failures) > 0

        clock_bonus = 8 if signal.get("clock_can_enter") else -18
        data_bonus = 6 if signal.get("data_valid") else -25

        rank_name = str(signal.get("master_rank") or "NO_BET").upper()
        rank_bonus = RANK_WEIGHTS.get(rank_name, 0) * 4

        suggested_market = signal.get("market_direction") or normalize_market(
            signal.get("master_market")
            or signal.get("market")
            or signal.get("suggested_market")
            or signal.get("market_category")
        )

        if suggested_market == "OVER":
            market_specific = (
                over_score * 0.09
                + goal_need_score * 0.10
                + pressure_score * 0.09
                + rhythm_score * 0.08
                + offensive_volume_score * 0.10
                + offensive_depth_score * 0.08
                - score_hold_probability * 0.06
                - under_transition_score * 0.06
                - false_pressure_risk * 0.09
            )

        elif suggested_market == "UNDER":
            market_specific = (
                under_score * 0.07
                + score_hold_probability * 0.10
                + under_transition_score * 0.09
                - tactical_score * 0.05
                - pressure_score * 0.05
                - offensive_volume_score * 0.10
                - offensive_depth_score * 0.07
            )

        else:
            market_specific = 0.0

        elite_score = (
            master_confidence * 0.29
            + market_confidence * 0.17
            + tactical_score * 0.15
            + offensive_volume_score * 0.08
            + pressure_score * 0.08
            + rhythm_score * 0.06
            + goal_need_score * 0.06
            + max(0, 100 - risk_score) * 0.07
            + max(0, 100 - contradiction_score) * 0.04
            + prediction_confidence * 0.12
            + market_specific
            + clock_bonus
            + data_bonus
            + rank_bonus
            - signal_life_penalty
        )

        if has_primary_failure:
            elite_score -= 18
            signal["ranker_guard"] = "PRIMARY_FILTER_FAILED"
            signal["ranker_guard_reason"] = ",".join(primary_failures)

        if len(failed_secondary_filters) >= 4:
            elite_score -= 8
            signal["ranker_secondary_warning"] = "TOO_MANY_SECONDARY_FILTERS_FAILED"

        if suggested_market == "UNDER":
            elite_score = self._adjust_under_score(
                elite_score=elite_score,
                signal=signal,
                over_score=over_score,
                under_score=under_score,
                offensive_volume_score=offensive_volume_score,
                tactical_score=tactical_score,
                pressure_score=pressure_score,
            )

        if suggested_market == "OVER":
            elite_score = self._adjust_over_score(
                elite_score=elite_score,
                signal=signal,
                over_score=over_score,
                under_score=under_score,
                offensive_volume_score=offensive_volume_score,
                offensive_depth_score=offensive_depth_score,
                false_pressure_risk=false_pressure_risk,
            )

        elite_score = self._adjust_by_candidate_layers(
            elite_score=elite_score,
            signal=signal,
        )

        elite_score = self._adjust_by_competition_context(
            elite_score=elite_score,
            signal=signal,
            suggested_market=suggested_market,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        elite_score = max(0, min(100, elite_score))
        signal["elite_score"] = round(elite_score, 2)

        signal = self._apply_prediction_score_adjustment(
            signal=signal,
            suggested_market=suggested_market,
        )

        elite_score = safe_float(signal.get("elite_score"), 0.0)

        can_publish = bool(signal.get("can_publish"))
        signal["elite_rank"] = self._elite_rank(
            elite_score=elite_score,
            can_publish=can_publish,
            has_primary_failure=has_primary_failure,
            suggested_market=suggested_market,
            signal=signal,
        )

        return signal

    def _apply_prediction_score_adjustment(
        self,
        signal: Dict[str, Any],
        suggested_market: str,
    ) -> Dict[str, Any]:
        item = dict(signal)

        prediction_alignment = str(item.get("prediction_market_alignment") or "").upper()
        elite_score = safe_float(item.get("elite_score"), 0.0)

        if prediction_alignment == "ALIGNED_WITH_OVER" and suggested_market == "OVER":
            item["elite_score"] = round(min(100, elite_score + 4), 2)
            item["ranker_prediction_bonus"] = "PREDICTION_ALIGNED_WITH_OVER"

        elif prediction_alignment == "ALIGNED_WITH_UNDER" and suggested_market == "UNDER":
            item["elite_score"] = round(min(100, elite_score + 4), 2)
            item["ranker_prediction_bonus"] = "PREDICTION_ALIGNED_WITH_UNDER"

        elif prediction_alignment in {"OVER_NEEDS_REACTIVATION", "UNDER_HAS_RUPTURE_RISK"}:
            item["elite_score"] = round(max(0, elite_score - 10), 2)
            item["ranker_prediction_warning"] = prediction_alignment

        return item

    def _apply_publication_guard(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(signal)

        soft_warnings = item.get("soft_warnings", []) or []
        primary_failures = self._extract_primary_failures(soft_warnings)
        market = normalize_market(
            item.get("market_direction")
            or item.get("master_market")
            or item.get("market")
            or item.get("suggested_market")
        )

        elite_rank = str(item.get("elite_rank") or "").upper()
        master_status = str(item.get("master_status") or "").upper()

        offensive_volume_score = safe_float(item.get("offensive_volume_score"), 0.0)
        tactical_score = safe_float(item.get("tactical_score"), 0.0)
        over_score = safe_float(item.get("over_score"), 0.0)
        under_score = safe_float(item.get("under_score"), 0.0)
        false_pressure_risk = safe_float(item.get("false_pressure_risk"), 0.0)

        candidate_level = str(item.get("candidate_level") or "").upper()
        over_candidate_level = str(item.get("over_candidate_level") or "").upper()

        low_stats = self._has_low_stats_warning(item)
        real_offensive_volume = self._has_real_offensive_volume(item)
        critical_block = bool(item.get("critical_block"))

        prediction_alignment = str(item.get("prediction_market_alignment") or "").upper()
        competition_tier = str(item.get("competition_tier") or "").upper()
        competition_weight = safe_float(item.get("competition_weight"), 0.0)
        is_elite_competition = self._is_elite_competition(item)
        is_late_game = safe_int(item.get("api_minute") or item.get("display_minute"), 0) >= 70
        recent_attack_proxy = safe_float(item.get("recent_attack_proxy"), 0.0)
        offensive_depth_score = safe_float(item.get("offensive_depth_score"), 0.0)

        if prediction_alignment in {"OVER_NEEDS_REACTIVATION", "UNDER_HAS_RUPTURE_RISK"}:
            item["can_publish"] = False
            item["published"] = False
            item["should_observe"] = True
            item["master_status"] = "WAIT_CONFIRMATION"
            item["master_rank"] = "OBSERVE"
            item["elite_rank"] = "OBSERVE"
            item["ranker_guard"] = "PREDICTION_MARKET_NOT_ALIGNED"
            item["ranker_guard_reason"] = prediction_alignment
            return item

        if critical_block:
            item["can_publish"] = False
            item["published"] = False
            item["should_observe"] = False
            item["should_block"] = True
            item["master_status"] = "BLOCKED"
            item["master_rank"] = "BLOCKED"
            item["elite_rank"] = "BLOCKED"
            item["ranker_guard"] = "CRITICAL_BLOCK"
            return item

        if primary_failures:
            item["can_publish"] = False
            item["published"] = False
            item["should_observe"] = True
            item["master_status"] = "WAIT_CONFIRMATION"
            item["master_rank"] = "OBSERVE"
            item["elite_rank"] = "OBSERVE"
            item["ranker_guard"] = "DEMOTED_BY_PRIMARY_FILTER"
            item["ranker_guard_reason"] = ",".join(primary_failures)
            return item

        if low_stats and not real_offensive_volume:
            if elite_rank == "PREMIUM":
                item["elite_rank"] = "FUERTE"
                item["ranker_guard"] = "PREMIUM_LIMITED_BY_LOW_STATS"

            if candidate_level in {"STRONG_CANDIDATE", "HIGH_OBSERVATION"}:
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "LOW_STATS_CANDIDATE_HELD"
                return item

        if market == "UNDER":
            if offensive_volume_score >= 62 or real_offensive_volume and over_candidate_level in {
                "OVER_HIGH_OBSERVATION",
                "OVER_STRONG_CANDIDATE",
            }:
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "UNDER_DEMOTED_BY_OVER_GROWTH"
                return item

            if under_score < over_score + 8:
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "UNDER_EDGE_NOT_CLEAR"
                return item

        if market == "OVER":
            if (
                is_elite_competition
                and is_late_game
                and offensive_depth_score < 55
                and recent_attack_proxy < 42
            ):
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "ELITE_TOURNAMENT_LATE_OVER_NEEDS_CONFIRMATION"
                item["ranker_guard_reason"] = (
                    f"{competition_tier or 'ELITE'} weight={competition_weight}: "
                    "OVER tardío requiere profundidad ofensiva y ataque reciente."
                )
                return item

            if false_pressure_risk >= 78:
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "OVER_FALSE_PRESSURE_TOO_HIGH"
                return item

            if offensive_volume_score < 38 and tactical_score < 55 and not real_offensive_volume:
                item["can_publish"] = False
                item["published"] = False
                item["should_observe"] = True
                item["master_status"] = "WAIT_CONFIRMATION"
                item["master_rank"] = "OBSERVE"
                item["elite_rank"] = "OBSERVE"
                item["ranker_guard"] = "OVER_WITHOUT_REAL_VOLUME"
                return item

        if over_candidate_level == "OVER_HIGH_OBSERVATION" and not item.get("can_publish"):
            item["should_observe"] = True
            item["master_status"] = "WAIT_CONFIRMATION"
            item["master_rank"] = "OBSERVE"
            item["elite_rank"] = "OBSERVE"
            item["ranker_guard"] = item.get("ranker_guard") or "OVER_HIGH_OBSERVATION_VISIBLE"

        if over_candidate_level == "OVER_STRONG_CANDIDATE" and not item.get("can_publish"):
            item["should_observe"] = True
            item["master_status"] = "WAIT_CONFIRMATION"
            item["master_rank"] = "OBSERVE"
            item["elite_rank"] = "OBSERVE"
            item["ranker_guard"] = item.get("ranker_guard") or "OVER_STRONG_CANDIDATE_VISIBLE"

        if master_status not in {"ENTER", "OPERABLE"}:
            item["can_publish"] = False

        if item.get("elite_rank") in {"BLOCKED", "NO_BET", "OBSERVE"}:
            item["can_publish"] = False

        return item

    def _apply_observation_priority(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(signal)

        over_candidate_level = str(item.get("over_candidate_level") or "").upper()
        candidate_level = str(item.get("candidate_level") or "").upper()

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            item["observation_priority"] = 92
            item["panel_section"] = "OVER_STRONG_CANDIDATE"
            item["alternative_market"] = "OVER"
            item["alternative_reading"] = item.get("why_over_candidate")
            return item

        if over_candidate_level == "OVER_HIGH_OBSERVATION":
            item["observation_priority"] = 84
            item["panel_section"] = "OVER_HIGH_OBSERVATION"
            item["alternative_market"] = "OVER"
            item["alternative_reading"] = item.get("why_over_candidate")
            return item

        if candidate_level == "STRONG_CANDIDATE":
            item["observation_priority"] = 78
            item["panel_section"] = "STRONG_CANDIDATE"
            return item

        if candidate_level == "HIGH_OBSERVATION":
            item["observation_priority"] = 70
            item["panel_section"] = "HIGH_OBSERVATION"
            return item

        item["observation_priority"] = safe_float(item.get("observation_priority"), 0.0)
        return item

    def _adjust_by_candidate_layers(
        self,
        elite_score: float,
        signal: Dict[str, Any],
    ) -> float:
        candidate_level = str(signal.get("candidate_level") or "").upper()
        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()

        if candidate_level == "STRONG_CANDIDATE":
            elite_score += 4
            signal["ranker_candidate_bonus"] = "STRONG_CANDIDATE_SUPPORT"

        elif candidate_level == "HIGH_OBSERVATION":
            elite_score += 2
            signal["ranker_candidate_bonus"] = "HIGH_OBSERVATION_SUPPORT"

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            elite_score += 5
            signal["ranker_over_candidate_bonus"] = "OVER_STRONG_CANDIDATE_VISIBLE"

        elif over_candidate_level == "OVER_HIGH_OBSERVATION":
            elite_score += 3
            signal["ranker_over_candidate_bonus"] = "OVER_HIGH_OBSERVATION_VISIBLE"

        return elite_score


    def _adjust_by_competition_context(
        self,
        elite_score: float,
        signal: Dict[str, Any],
        suggested_market: str,
        competition_tier: str,
        competition_weight: float,
        world_cup_flag: bool,
        national_team_flag: bool,
        major_tournament_flag: bool,
    ) -> float:
        """
        Ajuste liviano por tipo de competición.

        No decide solo y no rompe la lógica principal.
        Solo refuerza señales realmente limpias en torneos elite y exige
        confirmación extra para OVER tardío en Mundial/selecciones.
        """
        is_elite = (
            world_cup_flag
            or major_tournament_flag
            or competition_tier in {
                "WORLD_CUP_ELITE",
                "INTERNATIONAL_CLUB_ELITE",
                "NATIONAL_TEAM_ELITE",
                "ELITE",
            }
            or competition_weight >= 88
        )

        if not is_elite:
            return elite_score

        minute = safe_int(signal.get("api_minute") or signal.get("display_minute"), 0)
        offensive_depth_score = safe_float(signal.get("offensive_depth_score"), 0.0)
        recent_attack_proxy = safe_float(signal.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = safe_float(signal.get("false_pressure_risk"), 0.0)
        score_hold_probability = safe_float(signal.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(signal.get("under_transition_score"), 0.0)

        signal["ranker_competition_tier"] = competition_tier
        signal["ranker_competition_weight"] = competition_weight

        if suggested_market == "OVER":
            if minute >= 70 and (offensive_depth_score < 55 or recent_attack_proxy < 42):
                elite_score -= 8
                signal["ranker_competition_warning"] = "ELITE_LATE_OVER_REQUIRES_REAL_REACTIVATION"
            elif offensive_depth_score >= 62 and recent_attack_proxy >= 48 and false_pressure_risk < 65:
                elite_score += 3
                signal["ranker_competition_bonus"] = "ELITE_OVER_CONFIRMED_BY_DEPTH"

        elif suggested_market == "UNDER":
            if score_hold_probability >= 68 and under_transition_score >= 62:
                elite_score += 3
                signal["ranker_competition_bonus"] = "ELITE_UNDER_SUPPORTED_BY_SCORE_HOLD"

        if national_team_flag and minute <= 20:
            elite_score -= 2
            signal["ranker_competition_note"] = "NATIONAL_TEAM_EARLY_PHASE_MORE_CAUTION"

        return elite_score

    def _adjust_under_score(
        self,
        elite_score: float,
        signal: Dict[str, Any],
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        tactical_score: float,
        pressure_score: float,
    ) -> float:
        real_offensive_volume = self._has_real_offensive_volume(signal)
        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()

        if offensive_volume_score >= 60:
            elite_score -= 14
            signal["ranker_under_warning"] = "OFFENSIVE_VOLUME_TOO_HIGH_FOR_UNDER"

        if real_offensive_volume and over_candidate_level in {
            "OVER_HIGH_OBSERVATION",
            "OVER_STRONG_CANDIDATE",
        }:
            elite_score -= 10
            signal["ranker_under_over_warning"] = "OVER_GROWTH_AGAINST_UNDER"

        if tactical_score >= 75:
            elite_score -= 8
            signal["ranker_under_tactical_warning"] = "TACTICAL_ACTIVITY_TOO_HIGH_FOR_UNDER"

        if pressure_score >= 78:
            elite_score -= 7
            signal["ranker_under_pressure_warning"] = "PRESSURE_TOO_HIGH_FOR_UNDER"

        if under_score >= over_score + 14 and offensive_volume_score <= 45 and not real_offensive_volume:
            elite_score += 6
            signal["ranker_under_bonus"] = "CLEAR_UNDER_EDGE"

        elif under_score < over_score + 8:
            elite_score -= 10
            signal["ranker_under_warning"] = "UNDER_EDGE_NOT_CLEAR"

        return elite_score

    def _adjust_over_score(
        self,
        elite_score: float,
        signal: Dict[str, Any],
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        false_pressure_risk: float,
    ) -> float:
        real_offensive_volume = self._has_real_offensive_volume(signal)

        if (
            over_score >= under_score + 12
            and offensive_volume_score >= 55
            and offensive_depth_score >= 52
            and false_pressure_risk < 68
        ):
            elite_score += 7
            signal["ranker_over_bonus"] = "REAL_OVER_EDGE"

        elif (
            over_score >= under_score + 8
            and offensive_volume_score >= 45
            and false_pressure_risk < 72
        ):
            elite_score += 4
            signal["ranker_over_bonus"] = "MODERATE_OVER_EDGE"

        elif real_offensive_volume and over_score >= 45:
            elite_score += 3
            signal["ranker_over_bonus"] = "REAL_VOLUME_OVER_WATCH"

        if false_pressure_risk >= 75:
            elite_score -= 12
            signal["ranker_over_warning"] = "FALSE_PRESSURE_RISK_HIGH"

        if offensive_volume_score < 38 and not real_offensive_volume:
            elite_score -= 8
            signal["ranker_over_warning"] = "LOW_OFFENSIVE_VOLUME_FOR_OVER"

        return elite_score

    def _elite_rank(
        self,
        elite_score: float,
        can_publish: bool,
        has_primary_failure: bool,
        suggested_market: str,
        signal: Dict[str, Any],
    ) -> str:
        if has_primary_failure:
            return "OBSERVE"

        if not can_publish:
            if signal.get("should_observe"):
                return "OBSERVE"
            if signal.get("should_block"):
                return "BLOCKED"
            return "NO_BET"

        low_stats = self._has_low_stats_warning(signal)
        real_offensive_volume = self._has_real_offensive_volume(signal)

        if suggested_market == "UNDER":
            offensive_volume_score = safe_float(signal.get("offensive_volume_score"), 0.0)
            over_score = safe_float(signal.get("over_score"), 0.0)
            under_score = safe_float(signal.get("under_score"), 0.0)
            over_candidate_level = str(signal.get("over_candidate_level") or "").upper()

            if offensive_volume_score > 58:
                return "OBSERVE"

            if real_offensive_volume and over_candidate_level in {
                "OVER_HIGH_OBSERVATION",
                "OVER_STRONG_CANDIDATE",
            }:
                return "OBSERVE"

            if under_score < over_score + 9:
                return "OBSERVE"

        if suggested_market == "OVER":
            false_pressure_risk = safe_float(signal.get("false_pressure_risk"), 0.0)
            offensive_volume_score = safe_float(signal.get("offensive_volume_score"), 0.0)

            if false_pressure_risk >= 78:
                return "OBSERVE"

            if offensive_volume_score < 38 and not real_offensive_volume:
                return "OBSERVE"

        if low_stats and not real_offensive_volume and elite_score >= 88:
            return "FUERTE"

        if elite_score >= 88:
            return "PREMIUM"

        if elite_score >= 80:
            return "FUERTE"

        if elite_score >= 70:
            return "BUENA"

        if elite_score >= 60:
            return "OPERABLE"

        if signal.get("should_observe"):
            return "OBSERVE"

        if signal.get("should_block"):
            return "BLOCKED"

        return "NO_BET"

    def _extract_primary_failures(self, soft_warnings: List[Any]) -> List[str]:
        failures: List[str] = []

        for warning in soft_warnings or []:
            text = str(warning or "").upper()

            if text.startswith("FALTA_FILTRO_PRINCIPAL:"):
                failures.append(text.replace("FALTA_FILTRO_PRINCIPAL:", "").strip())

        return failures

    def _has_low_stats_warning(self, signal: Dict[str, Any]) -> bool:
        warnings = []
        warnings.extend(signal.get("risk_warnings", []) or [])
        warnings.extend(signal.get("soft_warnings", []) or [])
        warnings.extend(signal.get("logic_warnings", []) or [])

        data_quality = str(signal.get("data_quality") or "").upper()
        scan_phase = str(signal.get("scan_phase") or "").upper()

        warning_text = " ".join(str(x).upper() for x in warnings)

        return (
            "LOW_STATS_DATA" in warning_text
            or "NO_SHOTS_DATA" in warning_text
            or "NO_DANGEROUS_ATTACKS_DATA" in warning_text
            or data_quality == "LOW"
            or scan_phase == "WAITING_LIVE_STATS"
        )

    def _has_real_offensive_volume(self, signal: Dict[str, Any]) -> bool:
        shots = safe_float(signal.get("shots"), 0.0)
        shots_on_target = safe_float(signal.get("shots_on_target"), 0.0)
        corners = safe_float(signal.get("corners"), 0.0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0.0)
        dangerous_attacks = safe_float(signal.get("dangerous_attacks"), 0.0)

        over_volume_profile = signal.get("over_volume_profile")
        if isinstance(over_volume_profile, dict):
            if over_volume_profile.get("strong_volume") or over_volume_profile.get("medium_volume"):
                return True

        return (
            shots >= 10
            or shots_on_target >= 3
            or corners >= 5
            or xg >= 0.85
            or dangerous_attacks >= 15
        )

    def _attach_market_direction(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(signal)

        raw_market = (
            item.get("master_market")
            or item.get("market")
            or item.get("suggested_market")
            or item.get("market_category")
            or item.get("context_category")
            or ""
        )

        market_direction = normalize_market(raw_market)

        item["market_direction"] = market_direction

        if market_direction in {"OVER", "UNDER"}:
            item["market"] = market_direction
            item["suggested_market"] = market_direction
            item["master_market"] = market_direction

        return item


    def _is_elite_competition(self, signal: Dict[str, Any]) -> bool:
        tier = str(signal.get("competition_tier") or "").upper()
        weight = safe_float(signal.get("competition_weight"), 0.0)

        return (
            bool(signal.get("world_cup_flag"))
            or bool(signal.get("major_tournament_flag"))
            or tier in {
                "WORLD_CUP_ELITE",
                "INTERNATIONAL_CLUB_ELITE",
                "NATIONAL_TEAM_ELITE",
                "ELITE",
            }
            or weight >= 88
        )

    def _summary_by_competition_tier(
        self,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        summary: Dict[str, Dict[str, Any]] = {}

        for item in items or []:
            tier = str(item.get("competition_tier") or "UNKNOWN").upper()
            market = normalize_market(
                item.get("market_direction")
                or item.get("master_market")
                or item.get("market")
                or item.get("suggested_market")
            )

            bucket = summary.setdefault(
                tier,
                {
                    "total": 0,
                    "published": 0,
                    "observe": 0,
                    "blocked": 0,
                    "over": 0,
                    "under": 0,
                    "avg_elite_score": 0.0,
                },
            )

            bucket["total"] += 1

            if item.get("published"):
                bucket["published"] += 1

            if item.get("should_observe"):
                bucket["observe"] += 1

            if item.get("should_block"):
                bucket["blocked"] += 1

            if market == "OVER":
                bucket["over"] += 1
            elif market == "UNDER":
                bucket["under"] += 1

            current_avg = safe_float(bucket.get("avg_elite_score"), 0.0)
            elite_score = safe_float(item.get("elite_score"), 0.0)
            total = max(1, safe_int(bucket.get("total"), 1))
            bucket["avg_elite_score"] = round(
                ((current_avg * (total - 1)) + elite_score) / total,
                2,
            )

        return summary

    def _sort_key(self, item: Dict[str, Any]) -> Tuple[Any, ...]:
        rank = str(item.get("elite_rank") or item.get("master_rank") or "NO_BET").upper()
        rank_weight = RANK_WEIGHTS.get(rank, 0)

        market = normalize_market(
            item.get("market_direction")
            or item.get("master_market")
            or item.get("market")
            or item.get("suggested_market")
        )

        market_priority = 0
        if market == "OVER":
            market_priority = 2
        elif market == "UNDER":
            market_priority = 1

        return (
            rank_weight,
            safe_float(item.get("observation_priority"), 0.0),
            safe_float(item.get("elite_score"), 0.0),
            safe_float(item.get("master_confidence"), 0.0),
            safe_float(item.get("prediction_confidence"), 0.0),
            safe_float(item.get("market_confidence"), 0.0),
            safe_float(item.get("competition_weight"), 0.0),
            market_priority,
            safe_int(item.get("api_minute"), 0),
            -safe_float(item.get("risk_score"), 0.0),
        )
