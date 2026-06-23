from __future__ import annotations 

from typing import Any, Dict, List, Optional


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class SignalNarrativeAI:
    """
    Narrativa final V17.

    Este módulo NO decide la señal.
    Este módulo NO cambia el mercado.
    Este módulo SOLO redacta la explicación final coherente para el panel.

    Objetivo:
    - Evitar frases fijas contradictorias.
    - Explicar según estado real del partido.
    - Respetar MatchMaturityAI, PanelDecisionAI, prepartido y lectura live.
    - Separar lectura principal, riesgo alternativo y acción operativa.
    """

    VERSION = "V17_SIGNAL_NARRATIVE_AI_4_DYNAMIC_COMMENTATOR"

    def build(
        self,
        signal: Dict[str, Any],
        match_reader: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_reader = match_reader or {}

        minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("estimated_minute"),
            0,
        )

        scoreline = str(
            signal.get("scoreline")
            or signal.get("current_score")
            or f"{safe_int(signal.get('home_score'), 0)}-{safe_int(signal.get('away_score'), 0)}"
        )

        official_market = str(
            signal.get("official_market")
            or signal.get("master_market")
            or signal.get("market")
            or "NO_BET"
        ).upper()

        official_status = str(
            signal.get("official_status")
            or signal.get("master_status")
            or "NO_BET"
        ).upper()

        official_confidence = safe_float(
            signal.get("official_confidence")
            if signal.get("official_confidence") is not None
            else signal.get("master_confidence"),
            0,
        )

        official_probable_score = str(
            signal.get("official_probable_score")
            or signal.get("prediction_final_score")
            or signal.get("prediction_score")
            or scoreline
        )

        official_reason = str(
            signal.get("official_reason")
            or signal.get("master_reason")
            or ""
        )

        official_can_publish = bool(signal.get("official_can_publish"))
        raw_official_risks = signal.get("official_risks") or []
        if isinstance(raw_official_risks, list):
            official_risks = [str(item) for item in raw_official_risks if item]
        elif raw_official_risks:
            official_risks = [str(raw_official_risks)]
        else:
            official_risks = []

        market = official_market

        dominant = str(
            signal.get("football_dominant_reading")
            or match_reader.get("football_dominant_reading")
            or market
            or "SIN_LECTURA"
        ).upper()

        alternative = str(
            signal.get("football_alternative_reading")
            or signal.get("alternative_label")
            or match_reader.get("football_alternative_reading")
            or ""
        ).upper()

        master_status = official_status
        master_action = str(signal.get("master_action") or "").upper()
        panel_status = str(signal.get("panel_status") or signal.get("panel_label") or "").upper()

        maturity_permission = str(signal.get("match_maturity_entry_permission") or "").upper()
        maturity_label = str(
            signal.get("panel_maturity_label")
            or signal.get("match_maturity_panel_label")
            or ""
        ).upper()
        maturity_note = str(signal.get("match_maturity_panel_note") or "")

        over_score = safe_float(
            signal.get("over_score")
            or signal.get("result_over")
            or signal.get("over_probability")
            or 0,
            0,
        )
        under_score = safe_float(
            signal.get("under_score")
            or signal.get("result_under")
            or signal.get("under_probability")
            or 0,
            0,
        )

        confidence = official_confidence

        data_quality = str(signal.get("data_quality") or "").upper()
        risk_status = str(signal.get("risk_status") or signal.get("risk") or "").upper()
        context_category = str(signal.get("context_category") or "").upper()

        league_goal_profile = str(signal.get("league_goal_profile") or "UNKNOWN_LEAGUE").upper()
        team_goal_profile = str(signal.get("team_goal_profile") or "UNKNOWN_TEAMS").upper()
        first_half_goal_risk = str(signal.get("first_half_goal_risk") or "").upper()
        second_half_goal_risk = str(signal.get("second_half_goal_risk") or "").upper()
        under_early_risk = str(signal.get("under_early_risk") or "").upper()
        pre_match_note = str(signal.get("pre_match_panel_note") or "")

        live_volume_score = safe_float(signal.get("match_maturity_live_volume_score"), 0)
        pressure = safe_float(
            signal.get("pressure")
            or signal.get("pressure_score")
            or signal.get("football_pressure")
            or 0,
            0,
        )

        shots = safe_int(signal.get("shots"), 0)
        shots_on_target = safe_int(signal.get("shots_on_target"), 0)
        dangerous_attacks = safe_int(signal.get("dangerous_attacks"), 0)
        corners = safe_int(signal.get("corners"), 0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0)

        # Lectura de calidad de presión generada por PressureQualityAI.
        # Este bloque permite narrar como analista: dominio, amenaza real, presión falsa
        # y estado del partido, sin convertir este módulo en un motor de decisión.
        pressure_quality = str(
            signal.get("pressure_quality")
            or signal.get("pressure_quality_label")
            or signal.get("pressure_type")
            or signal.get("pressure_state")
            or ""
        ).upper()
        real_goal_threat = safe_float(
            signal.get("real_goal_threat")
            or signal.get("real_threat_score")
            or signal.get("goal_threat_real")
            or 0,
            0,
        )
        false_pressure_risk = safe_float(
            signal.get("false_pressure_risk")
            or signal.get("false_pressure_score")
            or 0,
            0,
        )
        game_state = str(signal.get("game_state") or signal.get("pressure_game_state") or "").upper()
        dominant_team = str(
            signal.get("dominant_team")
            or signal.get("pressure_dominant_team")
            or signal.get("team_in_control")
            or ""
        )
        threat_team = str(
            signal.get("threat_team")
            or signal.get("team_with_real_threat")
            or signal.get("danger_team")
            or ""
        )

        # Inteligencia predictiva ya calculada por MatchPredictionAI / ActivationAI / PromotionAI.
        prediction_market = str(signal.get("prediction_market") or "").upper()
        final_market_recommendation = official_market
        prediction_market_alignment = str(signal.get("prediction_market_alignment") or "").upper()
        prediction_conflict_level = str(signal.get("prediction_conflict_level") or "").upper()
        prediction_next_goal_probability = str(signal.get("prediction_next_goal_probability") or "").upper()

        prediction_no_goal_probability = self._probability_value(
            signal,
            [
                "prediction_no_goal_probability",
                "no_goal_probability",
                "prediction_no_goal_pct",
            ],
            default=None,
        )
        prediction_one_goal_probability = self._probability_value(
            signal,
            [
                "prediction_one_goal_probability",
                "one_goal_probability",
                "prediction_one_goal_pct",
            ],
            default=None,
        )
        prediction_two_plus_goal_probability = self._probability_value(
            signal,
            [
                "prediction_two_plus_goal_probability",
                "two_plus_goal_probability",
                "prediction_two_plus_goal_pct",
            ],
            default=None,
        )

        prediction_score = official_probable_score
        prediction_alternative_score = str(signal.get("prediction_alternative_score") or "")
        prediction_confidence = safe_float(signal.get("prediction_confidence"), 0)
        activation_level = str(signal.get("activation_level") or "").upper()
        activation_reason = str(signal.get("activation_reason") or "")
        activation_score = safe_float(signal.get("activation_score"), 0)
        promotion_level = str(signal.get("promotion_level") or "").upper()
        promotion_reason = str(signal.get("promotion_reason") or "")
        promotion_score = safe_float(signal.get("promotion_score"), 0)

        support_points = self._collect_points(
            signal.get("match_maturity_support_points"),
            signal.get("football_support_points"),
            signal.get("pre_match_support_points"),
            signal.get("support_points"),
        )

        caution_points = self._collect_points(
            signal.get("match_maturity_warnings"),
            signal.get("football_caution_points"),
            signal.get("pre_match_caution_points"),
            signal.get("missing_points"),
            signal.get("logic_warnings"),
            signal.get("soft_warnings"),
        )

        operative_state = self._operative_state(
            master_status=master_status,
            master_action=master_action,
            maturity_permission=maturity_permission,
            panel_status=panel_status,
        )

        reading_name = self._reading_name(
            market=market,
            dominant=dominant,
        )

        final_title = self._final_title(
            operative_state=operative_state,
            reading_name=reading_name,
            maturity_label=maturity_label,
            market=market,
            dominant=dominant,
            alternative=alternative,
        )

        main_reason = self._main_reason(
            operative_state=operative_state,
            reading_name=reading_name,
            minute=minute,
            scoreline=scoreline,
            market=market,
            dominant=dominant,
            alternative=alternative,
            over_score=over_score,
            under_score=under_score,
            confidence=confidence,
            data_quality=data_quality,
            risk_status=risk_status,
            context_category=context_category,
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            pre_match_note=pre_match_note,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
            maturity_note=maturity_note,
        )

        short_panel_message = self._short_panel_message(
            operative_state=operative_state,
            reading_name=reading_name,
            alternative=alternative,
            caution_points=caution_points,
            maturity_note=maturity_note,
        )

        action_message = self._action_message(
            operative_state=operative_state,
            maturity_permission=maturity_permission,
        )

        alternative_message = self._alternative_message(
            dominant=dominant,
            alternative=alternative,
            over_score=over_score,
            under_score=under_score,
            live_volume_score=live_volume_score,
        )

        professional_data = self._professional_match_analysis(
            signal=signal,
            minute=minute,
            scoreline=scoreline,
            market=market,
            reading_name=reading_name,
            operative_state=operative_state,
            final_market_recommendation=final_market_recommendation,
            prediction_market=prediction_market,
            prediction_market_alignment=prediction_market_alignment,
            prediction_conflict_level=prediction_conflict_level,
            prediction_next_goal_probability=prediction_next_goal_probability,
            prediction_no_goal_probability=prediction_no_goal_probability,
            prediction_one_goal_probability=prediction_one_goal_probability,
            prediction_two_plus_goal_probability=prediction_two_plus_goal_probability,
            prediction_score=prediction_score,
            prediction_alternative_score=prediction_alternative_score,
            prediction_confidence=prediction_confidence,
            activation_level=activation_level,
            activation_reason=activation_reason,
            activation_score=activation_score,
            promotion_level=promotion_level,
            promotion_reason=promotion_reason,
            promotion_score=promotion_score,
            over_score=over_score,
            under_score=under_score,
            confidence=confidence,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
            pressure_quality=pressure_quality,
            real_goal_threat=real_goal_threat,
            false_pressure_risk=false_pressure_risk,
            game_state=game_state,
            dominant_team=dominant_team,
            threat_team=threat_team,
            risk_status=risk_status,
            data_quality=data_quality,
            official_status=official_status,
            official_market=official_market,
            official_can_publish=official_can_publish,
            official_reason=official_reason,
            official_risks=official_risks,
            support_points=support_points,
            caution_points=caution_points,
        )

        return {
            "signal_narrative_version": self.VERSION,
            "narrative_title": professional_data["title"] or final_title,
            "narrative_main_reason": professional_data["professional_match_reading"],
            "narrative_short_panel_message": professional_data["short_decision"],
            "narrative_action_message": professional_data["action"],
            "narrative_alternative_message": professional_data["risk"],
            "narrative_operative_state": operative_state,
            "narrative_reading_name": official_market,
            "narrative_support_points": professional_data["support_points"],
            "narrative_caution_points": professional_data["caution_points"],
            "narrative_predicted_outcome": professional_data["score_prediction"],
            "narrative_safe_market_advice": professional_data["market_advice"],

            # Campos nuevos para panel profesional
            "professional_match_reading": professional_data["professional_match_reading"],
            # Alias legacy derivados exclusivamente de official_*.
            "final_narrative_decision": official_status,
            "final_narrative_market": official_market,
            "final_narrative_confidence": official_confidence,
            "final_narrative_confidence_label": professional_data["confidence_label"],
            "final_narrative_score_prediction": official_probable_score,
            "final_narrative_reason": official_reason,
            "final_narrative_risk": professional_data["risk"],
            "final_narrative_action": professional_data["action"],
            "final_narrative_scenario_summary": professional_data["scenario_summary"],
            "final_narrative_conflict_detected": professional_data["conflict_detected"],

            # Campos que puede usar el panel directamente
            "main_reading": professional_data["professional_match_reading"],
            "recommended_panel_message": professional_data["short_decision"],
            "panel_narrative_title": professional_data["title"] or final_title,
            "panel_narrative_reason": professional_data["professional_match_reading"],
            "panel_narrative_action": professional_data["action"],
            "panel_narrative_alternative": professional_data["risk"],
            "panel_prediction_text": professional_data["prediction_text"],
        }


    def _probability_value(
        self,
        signal: Dict[str, Any],
        keys: List[str],
        default: Optional[float] = None,
    ) -> Optional[float]:
        for key in keys:
            if key not in signal:
                continue
            value = signal.get(key)
            if value is None or value == "":
                continue
            number = safe_float(value, -1)
            if number < 0:
                continue
            if number <= 1:
                number *= 100
            return max(0.0, min(100.0, number))
        return default

    def _professional_match_analysis(
        self,
        signal: Dict[str, Any],
        minute: int,
        scoreline: str,
        market: str,
        reading_name: str,
        operative_state: str,
        final_market_recommendation: str,
        prediction_market: str,
        prediction_market_alignment: str,
        prediction_conflict_level: str,
        prediction_next_goal_probability: str,
        prediction_no_goal_probability: Optional[float],
        prediction_one_goal_probability: Optional[float],
        prediction_two_plus_goal_probability: Optional[float],
        prediction_score: str,
        prediction_alternative_score: str,
        prediction_confidence: float,
        activation_level: str,
        activation_reason: str,
        activation_score: float,
        promotion_level: str,
        promotion_reason: str,
        promotion_score: float,
        over_score: float,
        under_score: float,
        confidence: float,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
        pressure_quality: str,
        real_goal_threat: float,
        false_pressure_risk: float,
        game_state: str,
        dominant_team: str,
        threat_team: str,
        risk_status: str,
        data_quality: str,
        official_status: str,
        official_market: str,
        official_can_publish: bool,
        official_reason: str,
        official_risks: List[str],
        support_points: List[str],
        caution_points: List[str],
    ) -> Dict[str, Any]:
        # V17 AUDIT FIX:
        # NarrativeAI no redefine el mercado oficial.
        final_market = market

        no_goal, one_goal, two_plus = self._resolve_goal_scenarios(
            no_goal=prediction_no_goal_probability,
            one_goal=prediction_one_goal_probability,
            two_plus=prediction_two_plus_goal_probability,
            next_goal_probability=prediction_next_goal_probability,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots_on_target=shots_on_target,
            xg=xg,
            market=final_market,
        )

        conflict_detected = self._narrative_conflict_detected(
            market=market,
            final_market=final_market,
            alignment=prediction_market_alignment,
            conflict_level=prediction_conflict_level,
            next_goal_probability=prediction_next_goal_probability,
            no_goal=no_goal,
            two_plus=two_plus,
        )

        # V17 AUDIT FIX:
        # Se utiliza la confianza oficial calculada por MasterDecisionAI.
        confidence_value = confidence
        confidence_label = self._confidence_label(confidence_value)

        # V17 AUDIT FIX:
        # Narrativa descriptiva, no decisión alternativa.
        decision = operative_state

        score_prediction, alternative_score = self._clean_score_prediction(
            prediction_score=prediction_score,
            prediction_alternative_score=prediction_alternative_score,
            scoreline=scoreline,
            final_market=final_market,
        )

        scenario_ladder = self._scenario_ladder(
            score_prediction=score_prediction,
            alternative_score=alternative_score,
            signal=signal,
            no_goal=no_goal,
            one_goal=one_goal,
            two_plus=two_plus,
        )
        scenario_summary = scenario_ladder["summary"]

        story_type = self._classify_match_story(
            official_status=official_status,
            scoreline=scoreline,
            minute=minute,
            market=final_market,
            over_score=over_score,
            under_score=under_score,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            risk_status=risk_status,
            data_quality=data_quality,
            false_pressure_risk=false_pressure_risk,
            dominant_team=dominant_team,
            threat_team=threat_team,
            game_state=game_state,
            prediction_next_goal_probability=prediction_next_goal_probability,
            no_goal=no_goal,
            one_goal=one_goal,
            two_plus=two_plus,
        )

        dominance_reading = self._dominance_reading(
            dominant_team=dominant_team,
            threat_team=threat_team,
            game_state=game_state,
            market=final_market,
            scoreline=scoreline,
        )

        pressure_reading = self._pressure_quality_reading(
            pressure_quality=pressure_quality,
            real_goal_threat=real_goal_threat,
            false_pressure_risk=false_pressure_risk,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
        )

        rhythm_reading = self._rhythm_reading(
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
        )

        story_sentence = self._story_style_sentence(
            story_type=story_type,
            minute=minute,
            scoreline=scoreline,
            final_market=final_market,
            score_prediction=score_prediction,
            alternative_score=alternative_score,
            no_goal=no_goal,
            one_goal=one_goal,
            two_plus=two_plus,
            dominant_team=dominant_team,
            threat_team=threat_team,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            official_can_publish=official_can_publish,
        )

        reason = self._professional_reason(
            final_market=final_market,
            conflict_detected=conflict_detected,
            no_goal=no_goal,
            one_goal=one_goal,
            two_plus=two_plus,
            next_goal_probability=prediction_next_goal_probability,
            activation_reason=activation_reason,
            promotion_reason=promotion_reason,
            support_points=support_points,
            caution_points=caution_points,
        )

        risk = self._professional_risk(
            final_market=final_market,
            conflict_detected=conflict_detected,
            next_goal_probability=prediction_next_goal_probability,
            risk_status=risk_status,
            caution_points=caution_points,
            no_goal=no_goal,
            two_plus=two_plus,
        )

        action = self._official_action_sentence(
            official_status=official_status,
            official_can_publish=official_can_publish,
            official_reason=official_reason,
            official_risks=official_risks,
        )

        title = self._professional_title(
            official_status=official_status,
            official_can_publish=official_can_publish,
            story_type=story_type,
            conflict_detected=conflict_detected,
        )

        prediction_text = scenario_ladder["text"]
        short_decision = self._short_live_commentary(
            story_type=story_type,
            minute=minute,
            scoreline=scoreline,
            score_prediction=score_prediction,
            confidence_label=confidence_label,
            official_status=official_status,
            official_can_publish=official_can_publish,
        )

        professional_match_reading = self._compose_live_commentary(
            minute=minute,
            scoreline=scoreline,
            story_sentence=story_sentence,
            scenario_ladder=scenario_ladder,
            dominance_reading=dominance_reading,
            pressure_reading=pressure_reading,
            rhythm_reading=rhythm_reading,
            reason=reason,
            risk=risk,
            action=action,
            official_status=official_status,
            official_can_publish=official_can_publish,
            confidence_value=confidence_value,
            confidence_label=confidence_label,
        )

        return {
            "title": title,
            "professional_match_reading": professional_match_reading,
            "decision": decision,
            "final_market": final_market,
            "confidence": round(confidence_value, 2),
            "confidence_label": confidence_label,
            "score_prediction": score_prediction,
            "scenario_summary": scenario_summary,
            "dominance_reading": dominance_reading,
            "pressure_quality_reading": pressure_reading,
            "reason": reason,
            "risk": risk,
            "action": action,
            "short_decision": short_decision,
            "prediction_text": prediction_text,
            "market_advice": action,
            "conflict_detected": conflict_detected,
            "support_points": self._narrative_points(reason, support_points, limit=6),
            "caution_points": self._narrative_points(risk, caution_points, limit=6),
        }

    def _classify_match_story(
        self,
        official_status: str,
        scoreline: str,
        minute: int,
        market: str,
        over_score: float,
        under_score: float,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        xg: float,
        risk_status: str,
        data_quality: str,
        false_pressure_risk: float,
        dominant_team: str,
        threat_team: str,
        game_state: str,
        prediction_next_goal_probability: str,
        no_goal: float,
        one_goal: float,
        two_plus: float,
    ) -> str:
        status = str(official_status or "").upper()
        risk = str(risk_status or "").upper()
        quality = str(data_quality or "").upper()
        next_goal = str(prediction_next_goal_probability or "").upper()
        state = str(game_state or "").upper()

        home_goals, away_goals = self._score_parts(scoreline)
        margin = abs(home_goals - away_goals)
        total_goals = home_goals + away_goals
        force = max(live_volume_score, pressure)
        has_threat_team = bool(str(threat_team or "").strip())
        has_dominant_team = bool(str(dominant_team or "").strip())

        if status in {"BLOCKED", "NO_REENTRY", "BLOQUEADO"} or risk in {"EXTREME_RISK", "CRITICAL", "ALTO_EXTREMO"}:
            return "PARTIDO_BLOQUEADO"

        if margin >= 3 and has_dominant_team and false_pressure_risk < 55:
            return "DOMINIO_ABSOLUTO"

        if margin >= 2 and has_threat_team and threat_team and dominant_team and str(threat_team).strip() != str(dominant_team).strip() and force >= 55:
            return "REMONTADA_POSIBLE"

        if force >= 75 and shots_on_target >= 4 and two_plus >= 30:
            return "CAOS_OFENSIVO"

        if false_pressure_risk >= 65 or "FALSE" in state or "DOMINANCE_WITHOUT_DEPTH" in state:
            return "FAVORITO_EN_RIESGO"

        if next_goal in {"HIGH", "VERY_HIGH", "MEDIUM_HIGH"} or one_goal + two_plus >= 55 or total_goals >= 3:
            return "PARTIDO_ABIERTO"

        if no_goal >= 62 or (str(market).upper() == "UNDER" and force <= 45):
            return "CONTROL_DEFENSIVO"

        scenario_gap = max(no_goal, one_goal, two_plus) - sorted([no_goal, one_goal, two_plus])[-2]
        if scenario_gap <= 12 or abs(over_score - under_score) <= 12:
            return "PARTIDO_EQUILIBRADO"

        if quality in {"LOW", "BAD", "INVALID", "STALE", "OLD"}:
            return "PARTIDO_EQUILIBRADO"

        return "PARTIDO_ABIERTO" if force >= 45 else "PARTIDO_EQUILIBRADO"

    def _story_style_sentence(
        self,
        story_type: str,
        minute: int,
        scoreline: str,
        final_market: str,
        score_prediction: str,
        alternative_score: str,
        no_goal: float,
        one_goal: float,
        two_plus: float,
        dominant_team: str,
        threat_team: str,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        corners: int,
        xg: float,
        official_can_publish: bool,
    ) -> str:
        dominant = str(dominant_team or "").strip()
        threat = str(threat_team or "").strip()
        opener = f"Minuto {minute}. Con el marcador {scoreline}, "

        if story_type == "PARTIDO_BLOQUEADO":
            return (
                opener
                + "la lectura pasa a modo auditoría. Aunque existan datos futbolísticos para interpretar, "
                "hay una condición crítica que impide transformar el análisis en una acción operativa."
            )

        if story_type == "DOMINIO_ABSOLUTO":
            team_text = f"{dominant} tiene el control del encuentro" if dominant else "un equipo maneja el encuentro con claridad"
            return (
                opener
                + f"{team_text}. La sensación del partido es de superioridad sostenida: el rival responde poco "
                "y la principal incógnita ya no es el dominio, sino si ese control volverá a mover el marcador."
            )

        if story_type == "CAOS_OFENSIVO":
            return (
                opener
                + "el partido entró en una fase de ida y vuelta. Las transiciones aparecen con frecuencia, "
                f"el volumen ofensivo es alto y los {shots_on_target} tiros al arco mantienen viva la sensación de otro gol."
            )

        if story_type == "PARTIDO_ABIERTO":
            return (
                opener
                + "el encuentro sigue abierto. Hay ritmo, espacios y señales suficientes para pensar que el marcador "
                "todavía puede cambiar si la intensidad actual se sostiene."
            )

        if story_type == "CONTROL_DEFENSIVO":
            return (
                opener
                + "el partido empieza a cerrarse. La lectura favorece la conservación del marcador porque el ritmo "
                f"no empuja con claridad hacia una ruptura y el escenario sin más goles pesa {no_goal:.0f}%."
            )

        if story_type == "REMONTADA_POSIBLE":
            team_text = f"{threat} empieza a empujar" if threat else "el equipo que va abajo empieza a empujar"
            return (
                opener
                + f"{team_text}. La ventaja del marcador todavía existe, pero el trámite ya no transmite control absoluto; "
                "la presión del perseguidor mantiene viva la posibilidad de un giro en el partido."
            )

        if story_type == "FAVORITO_EN_RIESGO":
            team_text = f"{dominant} tiene presencia territorial" if dominant else "hay dominio territorial visible"
            return (
                opener
                + f"{team_text}, pero no toda esa presencia se convierte en peligro real. El sistema detecta una posible "
                "distancia entre dominio y amenaza, por eso la lectura exige prudencia."
            )

        return (
            opener
            + "el partido se mantiene equilibrado. Ningún escenario se impone con autoridad absoluta y la lectura "
            "depende de detalles: una pelota parada, una pérdida o una aceleración pueden cambiar el panorama."
        )

    def _scenario_ladder(
        self,
        score_prediction: str,
        alternative_score: str,
        signal: Dict[str, Any],
        no_goal: float,
        one_goal: float,
        two_plus: float,
    ) -> Dict[str, str]:
        main = str(score_prediction or signal.get("official_probable_score") or signal.get("prediction_final_score") or "Marcador en evaluación").strip()
        candidates: List[str] = []
        for key in (
            "prediction_alternative_score",
            "prediction_offensive_score",
            "prediction_break_score",
            "prediction_conservative_score",
            "prediction_main_score",
        ):
            value = str(signal.get(key) or "").strip()
            if value and value not in candidates and value != main:
                candidates.append(value)

        if alternative_score and alternative_score not in candidates and alternative_score != main:
            candidates.insert(0, alternative_score)

        alt1 = candidates[0] if candidates else "sin ruta alternativa clara"
        alt2 = candidates[1] if len(candidates) > 1 else "no aparece una segunda ruta suficientemente clara"

        summary = (
            f"Escenario principal: {main}. Alternativa principal: {alt1}. "
            f"Segunda alternativa: {alt2}. Probabilidades: sin más goles {no_goal:.0f}%, "
            f"un gol adicional {one_goal:.0f}%, dos o más goles {two_plus:.0f}%."
        )
        text = (
            f"Resultado más probable: {main}. "
            f"Alternativas: {alt1}; {alt2}. "
            f"Probabilidades: sin más goles {no_goal:.0f}%, un gol adicional {one_goal:.0f}%, "
            f"dos o más goles {two_plus:.0f}%."
        )
        return {
            "main": main,
            "alternative_1": alt1,
            "alternative_2": alt2,
            "summary": summary,
            "text": text,
        }

    def _official_action_sentence(
        self,
        official_status: str,
        official_can_publish: bool,
        official_reason: str,
        official_risks: List[str],
    ) -> str:
        status = str(official_status or "NO_BET").upper()
        reason = str(official_reason or "").strip()
        first_risk = str((official_risks or [""])[0] or "").strip()
        detail = reason or first_risk

        if status in {"BLOCKED", "NO_REENTRY", "BLOQUEADO"}:
            return "Acción oficial: no operar." + (f" Motivo oficial: {detail}." if detail else "")

        if status in {"NO_BET", "NO BET"}:
            return "Acción oficial: no operar; el sistema no encuentra una ventaja suficiente."

        if not official_can_publish or status in {"WAIT_CONFIRMATION", "OBSERVE", "REVALIDATION", "WAIT_REVALIDATION", "OBSERVATION"}:
            if status in {"WAIT_CONFIRMATION", "REVALIDATION", "WAIT_REVALIDATION"}:
                return "Acción oficial: esperar confirmación; todavía no hay señal autorizada."
            return "Acción oficial: observar; todavía no hay señal autorizada."

        if status in {"ENTER", "OPERABLE"} and official_can_publish:
            return "Acción oficial: señal operable según MasterDecisionAI, siempre con gestión de riesgo."

        return "Acción oficial: mantener seguimiento sin adelantar una entrada."

    def _short_live_commentary(
        self,
        story_type: str,
        minute: int,
        scoreline: str,
        score_prediction: str,
        confidence_label: str,
        official_status: str,
        official_can_publish: bool,
    ) -> str:
        status = str(official_status or "").upper()
        if status in {"BLOCKED", "NO_REENTRY", "BLOQUEADO"}:
            return f"Minuto {minute}: lectura bloqueada. Resultado más probable: {score_prediction}. No operar."
        if official_can_publish and status in {"ENTER", "OPERABLE"}:
            return f"Minuto {minute}: señal operable. Marcador {scoreline}; resultado más probable {score_prediction}."
        return (
            f"Minuto {minute}: {story_type.replace('_', ' ').lower()}. "
            f"Resultado más probable: {score_prediction}. Sin señal autorizada todavía."
        )

    def _compose_live_commentary(
        self,
        minute: int,
        scoreline: str,
        story_sentence: str,
        scenario_ladder: Dict[str, str],
        dominance_reading: str,
        pressure_reading: str,
        rhythm_reading: str,
        reason: str,
        risk: str,
        action: str,
        official_status: str,
        official_can_publish: bool,
        confidence_value: float,
        confidence_label: str,
    ) -> str:
        status = str(official_status or "NO_BET").upper()
        if status in {"BLOCKED", "NO_REENTRY", "BLOQUEADO"}:
            closing = "La lectura queda protegida por el bloqueo oficial; no debe tratarse como oportunidad operativa."
        elif official_can_publish and status in {"ENTER", "OPERABLE"}:
            closing = "La lectura está autorizada, pero mantiene gestión de riesgo como cualquier señal live."
        else:
            closing = "La lectura puede ser útil para seguimiento, pero no debe tratarse como entrada hasta nueva confirmación."

        return (
            f"{story_sentence} "
            f"El resultado más probable ahora es {scenario_ladder['main']}. "
            f"Como alternativas aparecen {scenario_ladder['alternative_1']} y {scenario_ladder['alternative_2']}. "
            f"En probabilidades de desarrollo: sin más goles {self._extract_pct(scenario_ladder['summary'], 'sin más goles')}%, "
            f"un gol adicional {self._extract_pct(scenario_ladder['summary'], 'un gol adicional')}% y "
            f"dos o más goles {self._extract_pct(scenario_ladder['summary'], 'dos o más goles')}%. "
            f"{dominance_reading} {pressure_reading} {rhythm_reading} "
            f"{reason} {risk} Estado oficial: {status}. "
            f"Confianza oficial {confidence_value:.0f}% ({confidence_label}). {action} {closing}"
        ).strip()

    def _extract_pct(self, text: str, label: str) -> str:
        marker = f"{label} "
        try:
            tail = text.split(marker, 1)[1]
            return tail.split("%", 1)[0].strip()
        except Exception:
            return "0"

    def _score_parts(self, scoreline: str) -> tuple[int, int]:
        try:
            raw_home, raw_away = str(scoreline or "0-0").split("-", 1)
            return safe_int(raw_home, 0), safe_int(raw_away, 0)
        except Exception:
            return 0, 0

    def _clean_score_prediction(
        self,
        prediction_score: str,
        prediction_alternative_score: str,
        scoreline: str,
        final_market: str,
    ) -> tuple[str, str]:
        main = str(prediction_score or "").strip()
        alt = str(prediction_alternative_score or "").strip()

        if not main:
            main = scoreline or "Marcador en evaluación"

        # Evita el problema detectado: Resultado probable = 1-1 y alternativa = 1-1.
        if alt == main:
            alt = ""

        # Si no existe alternativa real, no inventa un marcador exacto. Solo describe escenario.
        if not alt and final_market == "OVER":
            alt = "escenario ofensivo con un gol adicional"
        elif not alt and final_market == "UNDER":
            alt = "escenario conservador sin ruptura inmediata"

        return main, alt

    def _dominance_reading(
        self,
        dominant_team: str,
        threat_team: str,
        game_state: str,
        market: str,
        scoreline: str,
    ) -> str:
        dominant = str(dominant_team or "").strip()
        threat = str(threat_team or "").strip()
        state = str(game_state or "").replace("_", " ").lower()

        if dominant and threat and dominant != threat:
            return (
                f"El dominio territorial favorece a {dominant}, pero la amenaza más clara aparece en {threat}; "
                "por eso la lectura separa posesión de peligro real."
            )
        if dominant:
            return f"El equipo con mayor control del partido es {dominant}; la lectura evalúa si ese control se traduce en amenaza real."
        if threat:
            return f"La amenaza ofensiva más visible pertenece a {threat}, aunque el dominio territorial todavía requiere confirmación."
        if state:
            return f"El estado del partido se interpreta como {state}; la narrativa prioriza contexto antes que volumen estadístico."
        return "El dominio todavía no es totalmente claro; el sistema mantiene lectura contextual del marcador y del ritmo."

    def _pressure_quality_reading(
        self,
        pressure_quality: str,
        real_goal_threat: float,
        false_pressure_risk: float,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
    ) -> str:
        quality = str(pressure_quality or "").upper()
        threat = max(real_goal_threat, 0.0)
        false_risk = max(false_pressure_risk, 0.0)

        if quality in {"HIGH_THREAT_PRESSURE", "REAL_PRESSURE"} or threat >= 70:
            return (
                "La presión se considera real porque existe profundidad ofensiva y amenaza de gol; "
                f"amenaza real {threat:.0f}/100, tiros al arco {shots_on_target}, ataques peligrosos {dangerous_attacks}."
            )
        if quality in {"FALSE_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"} or (shots >= 8 and shots_on_target == 0):
            return (
                "El sistema detecta presión falsa o dominio sin profundidad: hay actividad ofensiva, "
                f"pero no suficiente amenaza clara de gol; riesgo de presión falsa {false_risk:.0f}/100."
            )
        if quality == "LATERAL_PRESSURE":
            return (
                "La presión es principalmente lateral: el equipo progresa territorialmente, "
                "pero aún no rompe líneas con claridad."
            )
        if quality == "LOW_PRESSURE" or (live_volume_score <= 30 and pressure <= 35):
            return (
                "La presión real es baja; el partido no muestra señales suficientes de ruptura inmediata."
            )
        return (
            f"La presión queda en evaluación: {shots} remates, {shots_on_target} al arco, "
            f"{corners} córners, xG {xg:.2f} y presión estimada {pressure:.0f}/100."
        )

    def _final_market_from_prediction(
        self,
        final_market_recommendation: str,
        prediction_market: str,
        market: str,
        reading_name: str,
    ) -> str:
        values = [final_market_recommendation, prediction_market, market, reading_name]
        for value in values:
            text = str(value or "").upper()
            if "OBSERVE_CONFLICT" in text:
                return "OBSERVE_CONFLICT"
            if "OBSERVE_OVER_RISK" in text:
                return "OBSERVE_OVER_RISK"
            if "OBSERVE_UNDER_RISK" in text:
                return "OBSERVE_UNDER_RISK"
            if "OVER" in text:
                return "OVER"
            if "UNDER" in text or "BAJO" in text:
                return "UNDER"
        return "OBSERVE"

    def _resolve_goal_scenarios(
        self,
        no_goal: Optional[float],
        one_goal: Optional[float],
        two_plus: Optional[float],
        next_goal_probability: str,
        live_volume_score: float,
        pressure: float,
        shots_on_target: int,
        xg: float,
        market: str,
    ) -> tuple[float, float, float]:
        if no_goal is not None and one_goal is not None and two_plus is not None:
            total = max(1.0, no_goal + one_goal + two_plus)
            return (no_goal / total) * 100, (one_goal / total) * 100, (two_plus / total) * 100

        force = max(live_volume_score, pressure)
        if next_goal_probability in {"VERY_HIGH", "HIGH"}:
            base_no, base_one, base_two = 18, 46, 36
        elif next_goal_probability == "MEDIUM_HIGH":
            base_no, base_one, base_two = 28, 45, 27
        elif next_goal_probability == "MEDIUM":
            base_no, base_one, base_two = 40, 42, 18
        elif next_goal_probability == "LOW_MEDIUM":
            base_no, base_one, base_two = 52, 35, 13
        elif next_goal_probability == "LOW":
            base_no, base_one, base_two = 65, 27, 8
        else:
            base_no, base_one, base_two = 45, 38, 17

        if force >= 70 or shots_on_target >= 3 or xg >= 1.0:
            base_no -= 8
            base_one += 3
            base_two += 5
        elif force <= 30 and shots_on_target == 0 and xg <= 0.35:
            base_no += 8
            base_one -= 4
            base_two -= 4

        if market == "UNDER":
            base_no += 3
            base_two -= 3
        elif market == "OVER":
            base_no -= 3
            base_two += 3

        total = max(1.0, base_no + base_one + base_two)
        return max(0, base_no / total * 100), max(0, base_one / total * 100), max(0, base_two / total * 100)

    def _narrative_conflict_detected(
        self,
        market: str,
        final_market: str,
        alignment: str,
        conflict_level: str,
        next_goal_probability: str,
        no_goal: float,
        two_plus: float,
    ) -> bool:
        if conflict_level in {"HIGH", "CRITICAL"}:
            return True
        if alignment in {"CONFLICT", "STRONG_CONFLICT", "MISALIGNED"}:
            return True
        if market == "UNDER" and next_goal_probability in {"HIGH", "VERY_HIGH"}:
            return True
        if market == "UNDER" and two_plus >= 32:
            return True
        if market == "OVER" and no_goal >= 60:
            return True
        if final_market.startswith("OBSERVE_CONFLICT"):
            return True
        return False

    def _narrative_confidence(
        self,
        prediction_confidence: float,
        activation_score: float,
        promotion_score: float,
        master_confidence: float,
        conflict_detected: bool,
        risk_status: str,
        data_quality: str,
        final_market: str,
        no_goal: float,
        one_goal: float,
        two_plus: float,
    ) -> float:
        values = [x for x in [prediction_confidence, activation_score, promotion_score, master_confidence] if x > 0]
        confidence = sum(values) / len(values) if values else 45.0

        scenario_edge = max(no_goal, one_goal, two_plus) - sorted([no_goal, one_goal, two_plus])[-2]
        if scenario_edge >= 20:
            confidence += 8
        elif scenario_edge >= 12:
            confidence += 4

        if final_market in {"OBSERVE", "OBSERVE_CONFLICT", "OBSERVE_OVER_RISK", "OBSERVE_UNDER_RISK"}:
            confidence -= 8
        if conflict_detected:
            confidence -= 18
        if risk_status in {"HIGH_RISK", "EXTREME_RISK", "ALTO", "EXTREMO"}:
            confidence -= 10
        if data_quality in {"LOW", "BAD", "INVALID", "STALE", "OLD"}:
            confidence -= 8

        return max(0.0, min(100.0, confidence))

    def _confidence_label(self, confidence: float) -> str:
        if confidence >= 82:
            return "alta"
        if confidence >= 68:
            return "media-alta"
        if confidence >= 52:
            return "media"
        if confidence >= 38:
            return "baja-media"
        return "baja"

    def _professional_decision(
        self,
        operative_state: str,
        final_market: str,
        conflict_detected: bool,
        confidence: float,
    ) -> str:
        if conflict_detected:
            return "OBSERVAR POR CONFLICTO"
        if operative_state == "BLOCKED":
            return "NO OPERAR"
        if final_market.startswith("OBSERVE"):
            return "OBSERVAR"
        if confidence >= 78 and operative_state in {"OPERABLE", "CANDIDATE"}:
            return "SEÑAL FUERTE"
        if confidence >= 62:
            return "CANDIDATO EN SEGUIMIENTO"
        return "OBSERVAR"

    def _rhythm_reading(
        self,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        corners: int,
        xg: float,
        dangerous_attacks: int,
    ) -> str:
        if live_volume_score >= 65 or pressure >= 70 or shots_on_target >= 3:
            return (
                f"El partido muestra ritmo ofensivo alto: {shots} remates, {shots_on_target} al arco, "
                f"{corners} córners, xG {xg:.2f} y presión {pressure:.0f}/100."
            )
        if live_volume_score >= 35 or shots >= 6 or corners >= 3:
            return (
                f"El partido muestra ritmo medio: {shots} remates, {shots_on_target} al arco, "
                f"{corners} córners, {dangerous_attacks} ataques peligrosos y xG {xg:.2f}."
            )
        return (
            f"El partido muestra ritmo bajo: {shots} remates, {shots_on_target} al arco, "
            f"{corners} córners, {dangerous_attacks} ataques peligrosos y xG {xg:.2f}."
        )

    def _professional_reason(
        self,
        final_market: str,
        conflict_detected: bool,
        no_goal: float,
        one_goal: float,
        two_plus: float,
        next_goal_probability: str,
        activation_reason: str,
        promotion_reason: str,
        support_points: List[str],
        caution_points: List[str],
    ) -> str:
        if conflict_detected:
            return (
                "Motivo: la lectura no es limpia porque mercado, predicción de marcador y riesgo de próximo gol "
                "no están totalmente alineados."
            )

        if final_market == "UNDER":
            return (
                f"Motivo: el escenario de conservación pesa más que la ruptura; sin más goles {no_goal:.0f}% "
                f"y solo un gol adicional {one_goal:.0f}%."
            )
        if final_market == "OVER":
            return (
                f"Motivo: el escenario de gol mantiene ventaja; un gol adicional {one_goal:.0f}% "
                f"y dos o más goles {two_plus:.0f}%. Próximo gol: {next_goal_probability or 'en evaluación'}."
            )

        selected = activation_reason or promotion_reason or (support_points[0] if support_points else "la lectura necesita más confirmación live")
        return f"Motivo: {selected}"

    def _professional_risk(
        self,
        final_market: str,
        conflict_detected: bool,
        next_goal_probability: str,
        risk_status: str,
        caution_points: List[str],
        no_goal: float,
        two_plus: float,
    ) -> str:
        if conflict_detected:
            return "Riesgo: conflicto predictivo activo; no conviene convertir esta lectura en señal limpia."
        if final_market == "UNDER" and next_goal_probability in {"HIGH", "VERY_HIGH", "MEDIUM_HIGH"}:
            return "Riesgo: aunque el mercado favorece UNDER, existe amenaza de gol adicional."
        if final_market == "OVER" and no_goal >= 55:
            return "Riesgo: el partido todavía puede conservar el marcador si baja el ritmo ofensivo."
        if risk_status in {"HIGH_RISK", "EXTREME_RISK", "ALTO", "EXTREMO"}:
            return "Riesgo: el riesgo operativo es elevado y exige prudencia."
        if caution_points:
            return f"Riesgo: {str(caution_points[0])}"
        return "Riesgo: no se detecta contradicción crítica, pero se mantiene gestión de riesgo."

    def _professional_action(
        self,
        decision: str,
        conflict_detected: bool,
        confidence: float,
        operative_state: str,
    ) -> str:
        if decision == "NO OPERAR":
            return "Acción: no operar."
        if conflict_detected:
            return "Acción: observar y esperar revalidación; no tomar como señal principal."
        if decision == "SEÑAL FUERTE":
            return "Acción: señal fuerte según el sistema, siempre con control de riesgo."
        if decision == "CANDIDATO EN SEGUIMIENTO":
            return "Acción: mantener en seguimiento; puede subir si el escenario se confirma."
        if operative_state in {"REVALIDATION", "WAIT_CONFIRMATION"}:
            return "Acción: esperar confirmación adicional antes de operar."
        return "Acción: observar, sin entrada todavía."

    def _professional_title(
        self,
        official_status: str,
        official_can_publish: bool,
        story_type: str,
        conflict_detected: bool,
    ) -> str:
        label = str(story_type or "PARTIDO_EN_LECTURA").replace("_", " ")
        status = str(official_status or "").upper()

        if status in {"BLOCKED", "NO_REENTRY", "BLOQUEADO"}:
            return "PARTIDO BLOQUEADO - NO OPERAR"
        if conflict_detected:
            return f"{label} - CONFLICTO PREDICTIVO"
        if official_can_publish and status in {"ENTER", "OPERABLE"}:
            return f"{label} - SEÑAL OPERABLE"
        if status in {"WAIT_CONFIRMATION", "REVALIDATION", "WAIT_REVALIDATION"}:
            return f"{label} - ESPERANDO CONFIRMACIÓN"
        return f"{label} - SIN SEÑAL AUTORIZADA"

    def _narrative_points(self, first_point: str, original: List[str], limit: int = 6) -> List[str]:
        points = [first_point] if first_point else []
        points.extend(original or [])
        cleaned: List[str] = []
        seen = set()
        for point in points:
            text = str(point or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned[:limit]

    def _predict_outcome(self, scoreline: str, market: str, live_volume_score: float, minute: int) -> Dict[str, str]:
        parts = scoreline.split('-')
        h = safe_int(parts[0]) if len(parts) > 0 else 0
        a = safe_int(parts[1]) if len(parts) > 1 else 0
        total = h + a

        outcome = "Marcador final en evaluación"
        advice = "Mercado recomendado: Esperar confirmación"

        if market == "UNDER":
            if live_volume_score < 30:
                outcome = f"Proyección: El partido tiende a finalizar {h}-{a} o {h+1 if h==a else h}-{a+1 if a==h else a}"
                advice = f"Mercado sugerido: Menos de {total + 1.5} (Under seguro)"
            else:
                outcome = f"Proyección: Marcador ajustado, máximo 1 gol adicional"
                advice = f"Mercado sugerido: Menos de {total + 2.5}"
        
        elif market == "OVER":
            if live_volume_score > 60:
                outcome = f"Proyección: Alta probabilidad de al menos 1 o 2 goles más"
                advice = f"Mercado sugerido: Más de {total + 0.5} (Entrada inmediata)"
            else:
                outcome = f"Proyección: Búsqueda de 1 gol por asedio"
                advice = f"Mercado sugerido: Over {total + 0.5} con revalidación"

        if minute < 25:
            outcome = "Panorama temprano: Estableciendo tendencia de marcador"

        return {"outcome": outcome, "advice": advice}

    def _operative_state(
        self,
        master_status: str,
        master_action: str,
        maturity_permission: str,
        panel_status: str,
    ) -> str:
        text = f"{master_status} {master_action} {maturity_permission} {panel_status}"

        if "BLOCK" in text or "NO_OPERAR" in text:
            return "BLOCKED"

        if "WAIT_REVALIDATION" in text or "ESPERAR_REVALIDACION" in text:
            return "REVALIDATION"

        if "WAIT_CONFIRMATION" in text or "ESPERAR_CONFIRMACION" in text:
            return "WAIT_CONFIRMATION"

        if "PANORAMA_ONLY" in text or "SOLO_PANORAMA" in text:
            return "PANORAMA"

        if "OBSERVE" in text or "OBSERVAR" in text or "OBSERVADOR" in text:
            return "OBSERVATION"

        if "ALLOW_STRONG_SIGNAL" in text or "OPERABLE" in text or "PUBLICAR" in text:
            return "OPERABLE"

        if "ALLOW_CANDIDATE" in text or "CANDIDATE" in text or "CANDIDATO" in text:
            return "CANDIDATE"

        return "OBSERVATION"

    def _reading_name(self, market: str, dominant: str) -> str:
        text = f"{market} {dominant}".upper()

        if "OVER" in text or "ALTO" in text:
            return "OVER"

        if "UNDER" in text or "BAJO" in text:
            return "UNDER"

        if "NO_BET" in text:
            return "NO_BET"

        return "LECTURA MIXTA"

    def _final_title(
        self,
        operative_state: str,
        reading_name: str,
        maturity_label: str,
        market: str,
        dominant: str,
        alternative: str,
    ) -> str:
        if maturity_label:
            return maturity_label.replace("_", " ")

        if operative_state == "BLOCKED":
            return "ENTRADA BLOQUEADA"

        if operative_state == "REVALIDATION":
            return f"{reading_name} EN REVALIDACIÓN"

        if operative_state == "WAIT_CONFIRMATION":
            return f"{reading_name} EN CONFIRMACIÓN"

        if operative_state == "PANORAMA":
            return f"PANORAMA {reading_name}"

        if operative_state == "OBSERVATION":
            if "OVER" in alternative and reading_name == "UNDER":
                return "UNDER EN OBSERVACIÓN CON RIESGO OVER"
            return f"{reading_name} EN OBSERVACIÓN"

        if operative_state == "OPERABLE":
            return f"{reading_name} OPERABLE"

        if operative_state == "CANDIDATE":
            return f"{reading_name} CANDIDATO"

        return "PARTIDO EN LECTURA"

    def _main_reason(
        self,
        operative_state: str,
        reading_name: str,
        minute: int,
        scoreline: str,
        market: str,
        dominant: str,
        alternative: str,
        over_score: float,
        under_score: float,
        confidence: float,
        data_quality: str,
        risk_status: str,
        context_category: str,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        pre_match_note: str,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
        maturity_note: str,
    ) -> str:
        base = self._base_reading_sentence(
            reading_name=reading_name,
            minute=minute,
            scoreline=scoreline,
            over_score=over_score,
            under_score=under_score,
            confidence=confidence,
        )

        live = self._live_sentence(
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
        )

        pre = self._pre_match_sentence(
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            pre_match_note=pre_match_note,
        )

        decision = self._decision_sentence(
            operative_state=operative_state,
            reading_name=reading_name,
            alternative=alternative,
            data_quality=data_quality,
            risk_status=risk_status,
            context_category=context_category,
            maturity_note=maturity_note,
        )

        return f"{base} {live} {pre} {decision}".strip()

    def _base_reading_sentence(
        self,
        reading_name: str,
        minute: int,
        scoreline: str,
        over_score: float,
        under_score: float,
        confidence: float,
    ) -> str:
        if reading_name == "UNDER":
            return (
                f"La lectura principal se inclina hacia UNDER en el minuto {minute}, "
                f"con marcador {scoreline}. El soporte UNDER aparece en {under_score:.0f}% "
                f"frente a OVER {over_score:.0f}%."
            )

        if reading_name == "OVER":
            return (
                f"La lectura principal se inclina hacia OVER en el minuto {minute}, "
                f"con marcador {scoreline}. El soporte OVER aparece en {over_score:.0f}% "
                f"frente a UNDER {under_score:.0f}%."
            )

        return (
            f"El partido está en lectura mixta en el minuto {minute}, "
            f"con marcador {scoreline}. No existe una lectura única suficientemente limpia."
        )

    def _live_sentence(
        self,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
    ) -> str:
        if live_volume_score >= 65:
            return (
                f"El volumen ofensivo live es alto, con {shots} remates, "
                f"{shots_on_target} al arco, {corners} córners y presión estimada de {pressure:.0f}%."
            )

        if live_volume_score >= 35:
            return (
                f"El volumen ofensivo live es medio, con {shots} remates, "
                f"{shots_on_target} al arco y {corners} córners, por lo que la lectura requiere confirmación."
            )

        return (
            f"El volumen ofensivo live es bajo, con {shots} remates, "
            f"{shots_on_target} al arco, {dangerous_attacks} ataques peligrosos y xG {xg:.2f}."
        )

    def _pre_match_sentence(
        self,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        pre_match_note: str,
    ) -> str:
        parts: List[str] = []

        if league_goal_profile and league_goal_profile != "UNKNOWN_LEAGUE":
            parts.append(f"La memoria previa clasifica la liga como {league_goal_profile}.")

        if team_goal_profile and team_goal_profile != "UNKNOWN_TEAMS":
            parts.append(f"El perfil previo de los equipos es {team_goal_profile}.")

        if first_half_goal_risk and "HIGH" in first_half_goal_risk:
            parts.append("Existe advertencia previa de gol en primer tiempo.")

        if second_half_goal_risk and "HIGH" in second_half_goal_risk:
            parts.append("Existe advertencia previa de gol en segundo tiempo.")

        if under_early_risk and "HIGH" in under_early_risk:
            parts.append("El sistema marca riesgo alto para UNDER temprano.")

        if pre_match_note:
            parts.append(pre_match_note)

        if not parts:
            return "La memoria previa no agrega una advertencia fuerte y deja mayor peso a la lectura live."

        return " ".join(parts[:3])

    def _decision_sentence(
        self,
        operative_state: str,
        reading_name: str,
        alternative: str,
        data_quality: str,
        risk_status: str,
        context_category: str,
        maturity_note: str,
    ) -> str:
        reasons: List[str] = []

        if data_quality in {"LOW", "BAD", "INVALID"}:
            reasons.append("la calidad de datos no permite elevar la señal solo por marcador")

        if risk_status in {"HIGH_RISK", "EXTREME_RISK", "ALTO", "EXTREMO"}:
            reasons.append("el riesgo operativo exige cautela")

        if "OVER" in alternative and reading_name == "UNDER":
            reasons.append("existe una alternativa OVER WATCH que advierte posible ruptura")

        if "UNDER" in alternative and reading_name == "OVER":
            reasons.append("existe una alternativa UNDER que advierte posible cierre")

        if context_category in {"MUERTO", "CERRADO", "CONTROL"} and reading_name == "OVER":
            reasons.append("el contexto del partido todavía no confirma apertura total")

        if maturity_note:
            reasons.append(maturity_note)

        if operative_state == "OPERABLE":
            return "La señal queda operable porque la lectura principal, el contexto live y la madurez coinciden."

        if operative_state == "CANDIDATE":
            return "La señal queda como candidata porque existe soporte suficiente, aunque todavía requiere seguimiento."

        if operative_state == "REVALIDATION":
            detail = ", ".join(reasons[:3]) if reasons else "todavía falta confirmación live"
            return f"Por eso el sistema no autoriza entrada directa y envía la lectura a revalidación, porque {detail}."

        if operative_state == "WAIT_CONFIRMATION":
            detail = ", ".join(reasons[:3]) if reasons else "todavía faltan filtros de confirmación"
            return f"Por eso el sistema mantiene espera de confirmación, porque {detail}."

        if operative_state == "PANORAMA":
            return "El sistema ya tiene panorama futbolístico, pero todavía no autoriza una entrada."

        if operative_state == "OBSERVATION":
            detail = ", ".join(reasons[:3]) if reasons else "la señal no tiene madurez suficiente"
            return f"Por eso la lectura queda en observación, porque {detail}."

        if operative_state == "BLOCKED":
            detail = ", ".join(reasons[:3]) if reasons else "hay condición crítica activa"
            return f"La entrada queda bloqueada porque {detail}."

        return "El sistema mantiene lectura preventiva sin autorización operativa."

    def _short_panel_message(
        self,
        operative_state: str,
        reading_name: str,
        alternative: str,
        caution_points: List[str],
        maturity_note: str,
    ) -> str:
        if operative_state == "OPERABLE":
            return f"{reading_name} operable. Lectura principal y contexto alineados."

        if operative_state == "CANDIDATE":
            return f"{reading_name} candidato. Requiere seguimiento antes de confirmar."

        if operative_state == "REVALIDATION":
            return maturity_note or f"{reading_name} en revalidación. Falta confirmación."

        if operative_state == "WAIT_CONFIRMATION":
            return maturity_note or f"{reading_name} espera confirmación."

        if operative_state == "PANORAMA":
            return f"Panorama {reading_name}. Sin entrada autorizada todavía."

        if operative_state == "OBSERVATION":
            if "OVER" in alternative and reading_name == "UNDER":
                return "UNDER en observación con riesgo alternativo OVER WATCH."
            if caution_points:
                return f"Observación. {str(caution_points[0])}"
            return f"{reading_name} en observación."

        if operative_state == "BLOCKED":
            if caution_points:
                return f"Bloqueado. {str(caution_points[0])}"
            return "Entrada bloqueada por condición crítica."

        return "Partido en lectura."

    def _action_message(
        self,
        operative_state: str,
        maturity_permission: str,
    ) -> str:
        if operative_state == "OPERABLE":
            return "Acción sugerida del sistema: señal operable, siempre con gestión de riesgo."

        if operative_state == "CANDIDATE":
            return "Acción sugerida del sistema: candidato en seguimiento, no tratar como entrada automática."

        if operative_state == "REVALIDATION":
            return "Acción sugerida del sistema: esperar revalidación antes de considerar entrada."

        if operative_state == "WAIT_CONFIRMATION":
            return "Acción sugerida del sistema: esperar confirmación de filtros."

        if operative_state == "PANORAMA":
            return "Acción sugerida del sistema: solo lectura de panorama, sin entrada."

        if operative_state == "OBSERVATION":
            return "Acción sugerida del sistema: observar, no entrar todavía."

        if operative_state == "BLOCKED":
            return "Acción sugerida del sistema: no operar."

        return "Acción sugerida del sistema: mantener observación."

    def _alternative_message(
        self,
        dominant: str,
        alternative: str,
        over_score: float,
        under_score: float,
        live_volume_score: float,
    ) -> str:
        if not alternative or alternative in {"NONE", "SIN ALTERNATIVA", "N/A"}:
            return "No existe alternativa fuerte visible."

        if "OVER" in alternative:
            return (
                f"Alternativa activa: OVER WATCH. No reemplaza automáticamente la lectura principal, "
                f"pero advierte riesgo de ruptura. OVER {over_score:.0f}%, UNDER {under_score:.0f}%, "
                f"volumen live {live_volume_score:.0f}/100."
            )

        if "UNDER" in alternative or "BAJO" in alternative:
            return (
                f"Alternativa activa: UNDER. No reemplaza automáticamente la lectura principal, "
                f"pero advierte posible cierre del partido. UNDER {under_score:.0f}%, OVER {over_score:.0f}%."
            )

        return f"Alternativa activa: {alternative}."

    def _collect_points(self, *groups: Any) -> List[str]:
        points: List[str] = []

        for group in groups:
            if not group:
                continue

            if isinstance(group, str):
                points.append(group)
                continue

            if isinstance(group, list):
                for item in group:
                    if item is None:
                        continue
                    points.append(str(item))

        cleaned: List[str] = []
        seen = set()

        for point in points:
            text = point.strip()
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            cleaned.append(text)

        return cleaned
