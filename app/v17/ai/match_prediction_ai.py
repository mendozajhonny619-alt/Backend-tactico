from typing import Any, Dict, List, Tuple


class MatchPredictionAI:
    """
    V17_MATCH_PREDICTION_AI

    Capa predictiva live para proyectar escenario del partido.

    No decide entrada.
    No reemplaza SignalActivationAI.
    No reemplaza SignalPromotionAI.
    """

    VERSION = "V17_MATCH_PREDICTION_AI_6_AUTONOMOUS_SCENARIOS"

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        minute = self._minute(signal)
        home_score = self._num(signal.get("home_score"))
        away_score = self._num(signal.get("away_score"))
        total_goals = home_score + away_score

        home_team = str(signal.get("home_team") or "Local")
        away_team = str(signal.get("away_team") or "Visitante")

        market = self._detect_market(signal)
        phase = self._detect_phase(minute)

        over_score = self._num(signal.get("over_score"))
        under_score = self._num(signal.get("under_score"))

        pressure = self._num(signal.get("pressure_score"))
        rhythm = self._num(signal.get("rhythm_score"))
        volume = self._num(
            signal.get("offensive_volume_score")
            or signal.get("match_maturity_live_volume_score")
        )
        risk = self._num(signal.get("risk_score"))
        maturity = self._num(signal.get("match_maturity_score"))

        activation_score = self._num(signal.get("activation_score"))
        promotion_score = self._num(signal.get("promotion_score"))

        confidence = self._num(
            signal.get("activation_score")
            or signal.get("promotion_score")
            or signal.get("master_confidence")
            or signal.get("football_confidence")
        )

        home_danger = self._num(
            signal.get("home_dangerous_attacks")
            or signal.get("dangerous_attacks_home")
            or signal.get("attacks_home")
        )
        away_danger = self._num(
            signal.get("away_dangerous_attacks")
            or signal.get("dangerous_attacks_away")
            or signal.get("attacks_away")
        )
        home_shots = self._num(signal.get("home_shots") or signal.get("shots_home"))
        away_shots = self._num(signal.get("away_shots") or signal.get("shots_away"))
        home_sot = self._num(signal.get("home_shots_on_target") or signal.get("sot_home"))
        away_sot = self._num(signal.get("away_shots_on_target") or signal.get("sot_away"))

        activation_level = self._txt(signal.get("activation_level"))
        activation_market = self._txt(signal.get("activation_market"))
        promotion_level = self._txt(signal.get("promotion_level"))
        promotion_market = self._txt(signal.get("promotion_market"))
        panel_section = self._txt(signal.get("panel_section"))
        football_reading = self._txt(signal.get("football_dominant_reading"))
        alternative_reading = self._txt(signal.get("football_alternative_reading"))

        # Competition intelligence propagated from LeagueFilter / SnapshotStore.
        # It does not decide entries by itself; it only calibrates live prediction
        # for elite international tournaments such as World Cup, Euro, Copa America, etc.
        competition_tier = self._txt(signal.get("competition_tier"))
        competition_weight = self._num(signal.get("competition_weight"))
        world_cup_flag = self._bool(signal.get("world_cup_flag"))
        national_team_flag = self._bool(signal.get("national_team_flag"))
        major_tournament_flag = self._bool(signal.get("major_tournament_flag"))

        # PressureQualityAI: lectura de presión real, falsa, lateral y dominio.
        # Mantiene compatibilidad si estos campos todavía no llegan al signal.
        pressure_type = self._txt(signal.get("pressure_type"))
        pressure_game_state = self._txt(signal.get("pressure_game_state") or signal.get("game_state"))
        pressure_real_goal_threat = self._txt(signal.get("real_goal_threat"))
        pressure_false_risk = self._txt(
            signal.get("pressure_false_pressure_risk")
            or signal.get("pressure_false_risk_level")
            or signal.get("false_pressure_risk_level")
        )
        pressure_attack_depth = self._txt(signal.get("attack_depth_level"))
        pressure_dominant_team = self._txt(signal.get("dominant_team"))
        pressure_reading = str(signal.get("pressure_reading") or "")

        over_watch = self._has_over_watch(signal, market)
        under_watch = self._has_under_watch(
            signal=signal,
            market=market,
            football_reading=football_reading,
        )

        attacking_team, attacking_side = self._detect_attacking_context(
            home_team=home_team,
            away_team=away_team,
            home_danger=home_danger,
            away_danger=away_danger,
            home_shots=home_shots,
            away_shots=away_shots,
            home_sot=home_sot,
            away_sot=away_sot,
            home_score=home_score,
            away_score=away_score,
        )

        scenario = self._detect_scenario(
            minute=minute,
            total_goals=total_goals,
            market=market,
            activation_market=activation_market,
            promotion_market=promotion_market,
            over_watch=over_watch,
            under_watch=under_watch,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            risk=risk,
            activation_level=activation_level,
            activation_score=activation_score,
            promotion_level=promotion_level,
            promotion_score=promotion_score,
            panel_section=panel_section,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        next_goal_probability = self._next_goal_probability(
            minute=minute,
            phase=phase,
            scenario=scenario,
            over_watch=over_watch,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            risk=risk,
            over_score=over_score,
            under_score=under_score,
            maturity=maturity,
            activation_level=activation_level,
            activation_score=activation_score,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        predicted_score = self._predict_score(
            home_score=home_score,
            away_score=away_score,
            attacking_side=attacking_side,
            next_goal_probability=next_goal_probability,
            scenario=scenario,
            minute=minute,
        )

        alternative_score = self._alternative_score(
            home_score=home_score,
            away_score=away_score,
            predicted_score=predicted_score,
            scenario=scenario,
            minute=minute,
        )

        projected_market = self._projected_market(
            scenario=scenario,
            next_goal_probability=next_goal_probability,
            over_watch=over_watch,
            under_watch=under_watch,
            market=market,
            activation_market=activation_market,
            promotion_market=promotion_market,
            over_score=over_score,
            under_score=under_score,
        )

        prediction_confidence = self._prediction_confidence(
            minute=minute,
            phase=phase,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            risk=risk,
            maturity=maturity,
            confidence=confidence,
            activation_level=activation_level,
            activation_score=activation_score,
            promotion_level=promotion_level,
            promotion_score=promotion_score,
            scenario=scenario,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        halftime_score = self._predict_halftime_score(
            minute=minute,
            home_score=home_score,
            away_score=away_score,
            predicted_score=predicted_score,
        )

        final_score = self._predict_final_score(
            minute=minute,
            home_score=home_score,
            away_score=away_score,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            scenario=scenario,
        )

        score_scenarios = self._score_scenarios(
            home_score=home_score,
            away_score=away_score,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            final_score=final_score,
            next_goal_probability=next_goal_probability,
            scenario=scenario,
        )

        market_alignment = self._market_alignment(
            projected_market=projected_market,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            final_score=final_score,
            current_total_goals=total_goals,
        )

        goal_probabilities = self._goal_count_probabilities(
            minute=minute,
            phase=phase,
            scenario=scenario,
            projected_market=projected_market,
            next_goal_probability=next_goal_probability,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            risk=risk,
            over_score=over_score,
            under_score=under_score,
            current_total_goals=total_goals,
        )

        goal_probabilities = self._apply_pressure_quality_to_goal_probabilities(
            goal_probabilities=goal_probabilities,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            attack_depth_level=pressure_attack_depth,
        )

        # V17.6: escenario autónomo controlado.
        # Este bloque no decide la señal; proyecta futuros posibles para que
        # RiskAI, ContradictionJudge y MasterDecisionAI tengan una lectura más
        # parecida a un analista profesional.
        team_goal_probabilities = self._team_goal_probabilities(
            home_score=home_score,
            away_score=away_score,
            home_danger=home_danger,
            away_danger=away_danger,
            home_shots=home_shots,
            away_shots=away_shots,
            home_sot=home_sot,
            away_sot=away_sot,
            attacking_side=attacking_side,
            dominant_team=pressure_dominant_team,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            next_goal_probability=next_goal_probability,
            minute=minute,
        )

        scoreline_distribution = self._scoreline_distribution(
            home_score=home_score,
            away_score=away_score,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            final_score=final_score,
            goal_probabilities=goal_probabilities,
            team_goal_probabilities=team_goal_probabilities,
            scenario=scenario,
            minute=minute,
        )

        scoreline_stability = self._scoreline_stability(
            scoreline_distribution=scoreline_distribution,
            goal_probabilities=goal_probabilities,
            pressure_game_state=pressure_game_state,
            false_pressure_risk=pressure_false_risk,
        )

        breakout_analysis = self._breakout_analysis(
            home_score=home_score,
            away_score=away_score,
            home_team=home_team,
            away_team=away_team,
            attacking_side=attacking_side,
            dominant_team=pressure_dominant_team,
            team_goal_probabilities=team_goal_probabilities,
            pressure_game_state=pressure_game_state,
            pressure_type=pressure_type,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            minute=minute,
        )

        conflict_level, conflict_reasons = self._prediction_conflict_level(
            projected_market=projected_market,
            market_alignment=market_alignment,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            final_score=final_score,
            current_total_goals=total_goals,
            next_goal_probability=next_goal_probability,
            goal_probabilities=goal_probabilities,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            over_score=over_score,
            under_score=under_score,
            over_watch=over_watch,
            under_watch=under_watch,
        )

        final_market_recommendation, final_prediction_reason = self._final_market_recommendation(
            projected_market=projected_market,
            market_alignment=market_alignment,
            conflict_level=conflict_level,
            conflict_reasons=conflict_reasons,
            goal_probabilities=goal_probabilities,
            over_score=over_score,
            under_score=under_score,
            next_goal_probability=next_goal_probability,
            scenario=scenario,
        )

        final_market_recommendation, final_prediction_reason, conflict_level, conflict_reasons = self._apply_pressure_quality_guard(
            projected_market=projected_market,
            final_market_recommendation=final_market_recommendation,
            final_prediction_reason=final_prediction_reason,
            conflict_level=conflict_level,
            conflict_reasons=conflict_reasons,
            goal_probabilities=goal_probabilities,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
        )

        final_market_recommendation, final_prediction_reason, conflict_level, conflict_reasons = self._apply_autonomous_scenario_guard(
            projected_market=projected_market,
            final_market_recommendation=final_market_recommendation,
            final_prediction_reason=final_prediction_reason,
            conflict_level=conflict_level,
            conflict_reasons=conflict_reasons,
            scoreline_distribution=scoreline_distribution,
            scoreline_stability=scoreline_stability,
            breakout_analysis=breakout_analysis,
            goal_probabilities=goal_probabilities,
        )

        prediction_confidence = self._apply_prediction_coherence_guard(
            prediction_confidence=prediction_confidence,
            projected_market=projected_market,
            final_market_recommendation=final_market_recommendation,
            market_alignment=market_alignment,
            conflict_level=conflict_level,
            goal_probabilities=goal_probabilities,
        )

        prediction_confidence = self._apply_pressure_quality_confidence(
            prediction_confidence=prediction_confidence,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            conflict_level=conflict_level,
        )

        prediction_mode = self._prediction_mode(
            minute=minute,
            activation_level=activation_level,
            promotion_level=promotion_level,
            panel_section=panel_section,
            prediction_confidence=prediction_confidence,
        )

        support_points = self._support_points(
            phase=phase,
            scenario=scenario,
            projected_market=projected_market,
            next_goal_probability=next_goal_probability,
            attacking_team=attacking_team,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            over_watch=over_watch,
            under_watch=under_watch,
            activation_level=activation_level,
            activation_score=activation_score,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        support_points = self._append_pressure_support_points(
            support_points=support_points,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            pressure_reading=pressure_reading,
        )

        support_points = self._append_autonomous_support_points(
            support_points=support_points,
            scoreline_distribution=scoreline_distribution,
            scoreline_stability=scoreline_stability,
            breakout_analysis=breakout_analysis,
            team_goal_probabilities=team_goal_probabilities,
        )

        caution_points = self._caution_points(
            minute=minute,
            risk=risk,
            scenario=scenario,
            prediction_confidence=prediction_confidence,
            over_watch=over_watch,
            under_watch=under_watch,
            alternative_reading=alternative_reading,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
            conflict_level=conflict_level,
            conflict_reasons=conflict_reasons,
        )

        caution_points = self._append_pressure_caution_points(
            caution_points=caution_points,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            pressure_reading=pressure_reading,
        )

        caution_points = self._append_autonomous_caution_points(
            caution_points=caution_points,
            scoreline_distribution=scoreline_distribution,
            scoreline_stability=scoreline_stability,
            breakout_analysis=breakout_analysis,
        )

        panel_message = self._panel_message(
            phase=phase,
            scenario=scenario,
            predicted_score=predicted_score,
            alternative_score=alternative_score,
            next_goal_probability=next_goal_probability,
            projected_market=projected_market,
            attacking_team=attacking_team,
            prediction_mode=prediction_mode,
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
            market_alignment=market_alignment,
            conflict_level=conflict_level,
            final_market_recommendation=final_market_recommendation,
            goal_probabilities=goal_probabilities,
        )

        panel_message = self._append_pressure_panel_message(
            panel_message=panel_message,
            pressure_type=pressure_type,
            pressure_game_state=pressure_game_state,
            real_goal_threat=pressure_real_goal_threat,
            false_pressure_risk=pressure_false_risk,
            pressure_reading=pressure_reading,
        )

        panel_message = self._append_autonomous_panel_message(
            panel_message=panel_message,
            scoreline_distribution=scoreline_distribution,
            scoreline_stability=scoreline_stability,
            breakout_analysis=breakout_analysis,
            team_goal_probabilities=team_goal_probabilities,
        )

        return {
            "match_prediction_version": self.VERSION,
            "prediction_competition_tier": competition_tier,
            "prediction_competition_weight": competition_weight,
            "prediction_world_cup_flag": world_cup_flag,
            "prediction_national_team_flag": national_team_flag,
            "prediction_major_tournament_flag": major_tournament_flag,
            "prediction_pressure_type": pressure_type,
            "prediction_pressure_game_state": pressure_game_state,
            "prediction_real_goal_threat": pressure_real_goal_threat,
            "prediction_false_pressure_risk": pressure_false_risk,
            "prediction_attack_depth_level": pressure_attack_depth,
            "prediction_pressure_dominant_team": pressure_dominant_team,
            "prediction_pressure_reading": pressure_reading,
            "prediction_phase": phase,
            "prediction_mode": prediction_mode,
            "prediction_scenario": scenario,
            "prediction_market": projected_market,
            "prediction_score": predicted_score,
            "prediction_alternative_score": alternative_score,
            "prediction_halftime_score": halftime_score,
            "prediction_final_score": final_score,
            "prediction_score_scenarios": score_scenarios,
            "prediction_market_alignment": market_alignment,
            "prediction_conflict_level": conflict_level,
            "prediction_conflict_reasons": conflict_reasons,
            "prediction_final_market_recommendation": final_market_recommendation,
            "prediction_final_reason": final_prediction_reason,
            "prediction_no_goal_probability": goal_probabilities.get("no_goal", 0),
            "prediction_one_goal_probability": goal_probabilities.get("one_goal", 0),
            "prediction_two_plus_goal_probability": goal_probabilities.get("two_plus_goals", 0),
            "prediction_goal_probabilities": goal_probabilities,
            "prediction_team_goal_probabilities": team_goal_probabilities,
            "prediction_home_goal_probability": team_goal_probabilities.get("home_goal", 0),
            "prediction_away_goal_probability": team_goal_probabilities.get("away_goal", 0),
            "prediction_no_team_goal_probability": team_goal_probabilities.get("no_team_goal", 0),
            "prediction_scoreline_distribution": scoreline_distribution,
            "prediction_scoreline_stability": scoreline_stability,
            "prediction_breakout_analysis": breakout_analysis,
            "prediction_breakout_risk": breakout_analysis.get("breakout_risk", "LOW"),
            "prediction_breakout_side": breakout_analysis.get("breakout_side", "NONE"),
            "prediction_next_goal_probability": next_goal_probability,
            "prediction_attacking_team": attacking_team,
            "prediction_attacking_side": attacking_side,
            "prediction_confidence": prediction_confidence,
            "prediction_panel_message": panel_message,
            "prediction_support_points": support_points,
            "prediction_caution_points": caution_points,
            "prediction_can_influence_signal": prediction_confidence >= 62,
            "prediction_is_operational": prediction_mode in {
                "OPERATIVE_PREDICTION",
                "STRONG_PREDICTION",
            },
        }


    def _team_goal_probabilities(
        self,
        home_score: float,
        away_score: float,
        home_danger: float,
        away_danger: float,
        home_shots: float,
        away_shots: float,
        home_sot: float,
        away_sot: float,
        attacking_side: str,
        dominant_team: str = "",
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        next_goal_probability: str = "",
        minute: int = 0,
    ) -> Dict[str, int]:
        """
        Estima quién tiene mayor probabilidad de anotar el próximo cambio real del partido.

        Autonomía controlada: no decide ENTER/NO_BET. Solo proyecta el reparto de amenaza
        entre local, visitante y conservación del marcador.
        """
        home_force = home_danger * 0.35 + home_shots * 1.5 + home_sot * 5.0
        away_force = away_danger * 0.35 + away_shots * 1.5 + away_sot * 5.0

        if attacking_side == "HOME":
            home_force += 10
        elif attacking_side == "AWAY":
            away_force += 10

        dominant = self._txt(dominant_team)
        if dominant in {"HOME", "LOCAL"}:
            home_force += 6
        elif dominant in {"AWAY", "VISITANTE"}:
            away_force += 6

        # Necesidad del marcador: el equipo que pierde debe tener más peso de ruptura,
        # incluso cuando no domina territorialmente.
        if home_score < away_score:
            home_force += 8
        elif away_score < home_score:
            away_force += 8

        if pressure_type in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"} or real_goal_threat == "HIGH":
            if attacking_side == "HOME":
                home_force += 8
            elif attacking_side == "AWAY":
                away_force += 8
            else:
                home_force += 3
                away_force += 3

        if pressure_type in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
            if attacking_side == "HOME":
                home_force -= 5
            elif attacking_side == "AWAY":
                away_force -= 5

        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"}:
            # La presión del dominador pierde peso y sube la conservación.
            if attacking_side == "HOME":
                home_force -= 4
            elif attacking_side == "AWAY":
                away_force -= 4

        if pressure_game_state in {"OPEN_GAME", "BROKEN_GAME", "PANIC_GAME"}:
            home_force += 4
            away_force += 4
        elif pressure_game_state in {"LOW_ACTIVITY_GAME", "CONTROLLED_GAME", "DEAD_GAME"}:
            home_force -= 3
            away_force -= 3

        # Probabilidad total de que exista próximo gol.
        goal_mass = {
            "HIGH": 76,
            "MEDIUM_HIGH": 64,
            "MEDIUM": 52,
            "LOW_MEDIUM": 40,
            "LOW": 28,
        }.get(self._txt(next_goal_probability), 45)

        if minute >= 82 and pressure_game_state not in {"BROKEN_GAME", "PANIC_GAME"}:
            goal_mass -= 8

        home_force = max(1.0, home_force)
        away_force = max(1.0, away_force)
        total_force = home_force + away_force

        home_goal = round(goal_mass * home_force / total_force)
        away_goal = round(goal_mass * away_force / total_force)
        no_team_goal = max(0, 100 - home_goal - away_goal)

        return {
            "home_goal": int(max(0, min(100, home_goal))),
            "away_goal": int(max(0, min(100, away_goal))),
            "no_team_goal": int(max(0, min(100, no_team_goal))),
            "home_force": int(round(home_force)),
            "away_force": int(round(away_force)),
        }

    def _scoreline_distribution(
        self,
        home_score: float,
        away_score: float,
        predicted_score: str,
        alternative_score: str,
        final_score: str,
        goal_probabilities: Dict[str, int],
        team_goal_probabilities: Dict[str, int],
        scenario: str,
        minute: int = 0,
    ) -> List[Dict[str, Any]]:
        """Construye top de marcadores probables con porcentajes normalizados."""
        candidates: Dict[str, float] = {}

        def add(score: str, weight: float, label: str) -> None:
            score = self._clean_score(score, int(home_score), int(away_score))
            candidates[score] = candidates.get(score, 0.0) + max(0.0, float(weight))

        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))
        home_goal = int(team_goal_probabilities.get("home_goal", 0))
        away_goal = int(team_goal_probabilities.get("away_goal", 0))

        current = f"{int(home_score)}-{int(away_score)}"
        home_plus = f"{int(home_score) + 1}-{int(away_score)}"
        away_plus = f"{int(home_score)}-{int(away_score) + 1}"

        add(current, no_goal * 1.15, "conservative")
        add(home_plus, max(1, one_goal) * max(0.25, home_goal / max(1, home_goal + away_goal)), "home_next")
        add(away_plus, max(1, one_goal) * max(0.25, away_goal / max(1, home_goal + away_goal)), "away_next")
        add(predicted_score, 28, "main")
        add(alternative_score, 20, "alternative")
        add(final_score, 16, "final")

        if two_plus >= 22:
            if home_goal >= away_goal:
                add(f"{int(home_score) + 2}-{int(away_score)}", two_plus * 0.55, "offensive")
                add(f"{int(home_score) + 1}-{int(away_score) + 1}", two_plus * 0.45, "rupture")
            else:
                add(f"{int(home_score)}-{int(away_score) + 2}", two_plus * 0.55, "offensive")
                add(f"{int(home_score) + 1}-{int(away_score) + 1}", two_plus * 0.45, "rupture")

        total = max(1.0, sum(candidates.values()))
        rows = []
        for score, weight in candidates.items():
            rows.append({"score": score, "probability": int(round(weight * 100 / total))})

        rows.sort(key=lambda x: x["probability"], reverse=True)
        top = rows[:5]
        # Ajuste para que el top no supere 100 por redondeos.
        total_top = sum(x["probability"] for x in top)
        if total_top > 100 and top:
            top[0]["probability"] -= total_top - 100
        return top

    def _scoreline_stability(
        self,
        scoreline_distribution: List[Dict[str, Any]],
        goal_probabilities: Dict[str, int],
        pressure_game_state: str = "",
        false_pressure_risk: str = "",
    ) -> str:
        if not scoreline_distribution:
            return "UNKNOWN"
        top = int(scoreline_distribution[0].get("probability", 0))
        second = int(scoreline_distribution[1].get("probability", 0)) if len(scoreline_distribution) > 1 else 0
        gap = top - second
        no_goal = int(goal_probabilities.get("no_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))

        if pressure_game_state in {"BROKEN_GAME", "PANIC_GAME"} or two_plus >= 32:
            return "HIGHLY_UNSTABLE"
        if gap <= 6:
            return "UNSTABLE"
        if no_goal >= 58 and top >= 34:
            return "STABLE"
        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"} and no_goal >= 48:
            return "MODERATELY_STABLE"
        if gap <= 14:
            return "MODERATELY_UNSTABLE"
        return "MODERATELY_STABLE"

    def _breakout_analysis(
        self,
        home_score: float,
        away_score: float,
        home_team: str,
        away_team: str,
        attacking_side: str,
        dominant_team: str,
        team_goal_probabilities: Dict[str, int],
        pressure_game_state: str = "",
        pressure_type: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        minute: int = 0,
    ) -> Dict[str, Any]:
        home_goal = int(team_goal_probabilities.get("home_goal", 0))
        away_goal = int(team_goal_probabilities.get("away_goal", 0))
        dominant = self._txt(dominant_team)

        breakout_side = "NONE"
        breakout_team = "Sin ruptura clara"
        risk_points = 0
        reasons: List[str] = []

        # Rival que pierde pero tiene probabilidad relevante de gol.
        if home_score > away_score and away_goal >= 26:
            breakout_side = "AWAY"
            breakout_team = away_team
            risk_points += 28
            reasons.append("El visitante puede romper el dominio con empate o transición.")
        elif away_score > home_score and home_goal >= 26:
            breakout_side = "HOME"
            breakout_team = home_team
            risk_points += 28
            reasons.append("El local puede romper el dominio con empate o transición.")

        # Dominio del equipo A, pero amenaza del otro lado.
        if dominant in {"HOME", "LOCAL"} and away_goal >= home_goal - 5 and away_goal >= 24:
            breakout_side = "AWAY"
            breakout_team = away_team
            risk_points += 20
            reasons.append("El rival del dominador mantiene probabilidad de gol competitiva.")
        elif dominant in {"AWAY", "VISITANTE"} and home_goal >= away_goal - 5 and home_goal >= 24:
            breakout_side = "HOME"
            breakout_team = home_team
            risk_points += 20
            reasons.append("El rival del dominador mantiene probabilidad de gol competitiva.")

        if pressure_game_state in {"BROKEN_GAME", "PANIC_GAME", "OPEN_GAME"}:
            risk_points += 18
            reasons.append("El estado del partido favorece ruptura o cambio de escenario.")

        if pressure_type in {"FALSE_PRESSURE", "DOMINANCE_WITHOUT_DEPTH", "LATERAL_PRESSURE"} and false_pressure_risk in {"HIGH", "MEDIUM_HIGH"}:
            risk_points += 12
            reasons.append("La presión del dominador puede ser falsa y dejar transición al rival.")

        if real_goal_threat == "HIGH":
            risk_points += 8

        if minute >= 75 and abs(home_score - away_score) <= 1:
            risk_points += 8
            reasons.append("Tramo final con diferencia corta: aumenta riesgo de episodio decisivo.")

        if risk_points >= 55:
            risk = "HIGH"
        elif risk_points >= 35:
            risk = "MEDIUM_HIGH"
        elif risk_points >= 20:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "breakout_risk": risk,
            "breakout_score": int(min(100, risk_points)),
            "breakout_side": breakout_side,
            "breakout_team": breakout_team,
            "breakout_reasons": reasons[:5],
        }

    def _apply_autonomous_scenario_guard(
        self,
        projected_market: str,
        final_market_recommendation: str,
        final_prediction_reason: str,
        conflict_level: str,
        conflict_reasons: List[str],
        scoreline_distribution: List[Dict[str, Any]],
        scoreline_stability: str,
        breakout_analysis: Dict[str, Any],
        goal_probabilities: Dict[str, int],
    ) -> Tuple[str, str, str, List[str]]:
        recommendation = final_market_recommendation
        reason = final_prediction_reason
        conflict = conflict_level
        reasons = list(conflict_reasons or [])

        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))
        goal_risk = one_goal + two_plus
        breakout_risk = str((breakout_analysis or {}).get("breakout_risk") or "LOW")

        if projected_market == "UNDER" and scoreline_stability in {"UNSTABLE", "HIGHLY_UNSTABLE"} and goal_risk >= 48:
            reasons.append("UNDER contradice una distribución de marcador inestable.")
            recommendation = "OBSERVE_OVER_RISK"
            reason = "UNDER queda en observación: los escenarios alternativos muestran riesgo real de ruptura."
            conflict = self._raise_conflict(conflict, "MEDIUM_CONFLICT")

        if projected_market == "OVER" and no_goal >= 55 and scoreline_stability in {"STABLE", "MODERATELY_STABLE"}:
            reasons.append("OVER contradice una distribución estable de conservación del marcador.")
            recommendation = "OBSERVE_UNDER_RISK"
            reason = "OVER queda en observación: el escenario conservador domina por encima de la ruptura."
            conflict = self._raise_conflict(conflict, "MEDIUM_CONFLICT")

        if breakout_risk in {"HIGH", "MEDIUM_HIGH"}:
            reasons.append("Existe escenario alternativo de ruptura por el rival o por transición.")
            if projected_market == "UNDER":
                recommendation = "OBSERVE_OVER_RISK"
                reason = "UNDER requiere confirmación: el rival puede romper la conservación del marcador."
                conflict = self._raise_conflict(conflict, "HIGH_CONFLICT" if breakout_risk == "HIGH" else "MEDIUM_CONFLICT")
            else:
                conflict = self._raise_conflict(conflict, "LOW_CONFLICT")

        return recommendation, reason, conflict, reasons[:8]

    def _append_autonomous_support_points(
        self,
        support_points: List[str],
        scoreline_distribution: List[Dict[str, Any]],
        scoreline_stability: str,
        breakout_analysis: Dict[str, Any],
        team_goal_probabilities: Dict[str, int],
    ) -> List[str]:
        points = list(support_points or [])
        if scoreline_distribution:
            top = scoreline_distribution[0]
            points.append(f"Escenario principal: {top.get('score')} ({top.get('probability')}%).")
        points.append(f"Estabilidad del marcador: {scoreline_stability}.")
        points.append(
            f"Prob. gol local/visitante: {team_goal_probabilities.get('home_goal', 0)}% / {team_goal_probabilities.get('away_goal', 0)}%."
        )
        if breakout_analysis.get("breakout_risk") in {"MEDIUM_HIGH", "HIGH"}:
            points.append(f"Ruptura posible por {breakout_analysis.get('breakout_team')}." )
        return points[:8]

    def _append_autonomous_caution_points(
        self,
        caution_points: List[str],
        scoreline_distribution: List[Dict[str, Any]],
        scoreline_stability: str,
        breakout_analysis: Dict[str, Any],
    ) -> List[str]:
        cautions = list(caution_points or [])
        if len(scoreline_distribution) >= 2:
            top = int(scoreline_distribution[0].get("probability", 0))
            second = int(scoreline_distribution[1].get("probability", 0))
            if abs(top - second) <= 8:
                cautions.append("El escenario alternativo está demasiado cerca del principal; no elevar confianza sin confirmación.")
        if scoreline_stability in {"UNSTABLE", "HIGHLY_UNSTABLE"}:
            cautions.append("Marcador inestable: existe riesgo de que el partido cambie de lectura rápidamente.")
        for reason in (breakout_analysis or {}).get("breakout_reasons", [])[:2]:
            cautions.append(str(reason))
        return cautions[:8]

    def _append_autonomous_panel_message(
        self,
        panel_message: str,
        scoreline_distribution: List[Dict[str, Any]],
        scoreline_stability: str,
        breakout_analysis: Dict[str, Any],
        team_goal_probabilities: Dict[str, int],
    ) -> str:
        if not scoreline_distribution:
            return panel_message
        top_items = ", ".join(f"{x.get('score')} {x.get('probability')}%" for x in scoreline_distribution[:3])
        suffix = (
            f" Escenarios autónomos: {top_items}. "
            f"Estabilidad: {scoreline_stability}. "
            f"Gol local/visitante: {team_goal_probabilities.get('home_goal', 0)}%/{team_goal_probabilities.get('away_goal', 0)}%."
        )
        if breakout_analysis.get("breakout_risk") in {"MEDIUM_HIGH", "HIGH"}:
            suffix += f" Ruptura posible: {breakout_analysis.get('breakout_team')} ({breakout_analysis.get('breakout_risk')})."
        return f"{panel_message}{suffix}"

    def _clean_score(self, score: str, home_score: int, away_score: int) -> str:
        try:
            left, right = str(score or "").split("-")[:2]
            h = max(home_score, int(float(left)))
            a = max(away_score, int(float(right)))
            return f"{h}-{a}"
        except Exception:
            return f"{home_score}-{away_score}"

    def _apply_pressure_quality_to_goal_probabilities(
        self,
        goal_probabilities: Dict[str, int],
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        attack_depth_level: str = "",
    ) -> Dict[str, int]:
        """
        Ajusta escenarios de goles usando PressureQualityAI.

        Objetivo: no confundir actividad ofensiva con peligro real.
        Ejemplo: 8 remates, 0 al arco, 5 corners y 0 ataques peligrosos
        puede ser presión lateral, no necesariamente OVER fuerte.
        """
        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))

        if pressure_type in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"} or real_goal_threat == "HIGH":
            no_goal -= 10
            one_goal += 6
            two_plus += 4

        elif pressure_type in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
            if real_goal_threat in {"LOW", "MEDIUM_LOW", ""}:
                no_goal += 12
                one_goal -= 6
                two_plus -= 6

        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"}:
            no_goal += 8
            two_plus -= 5

        if pressure_game_state in {"OPEN_GAME", "BROKEN_GAME", "PANIC_GAME"}:
            no_goal -= 5
            one_goal += 3
            two_plus += 2

        if pressure_game_state in {"LOW_ACTIVITY_GAME", "CONTROLLED_GAME", "DEAD_GAME"}:
            no_goal += 6
            two_plus -= 4

        if attack_depth_level in {"HIGH", "VERY_HIGH"}:
            no_goal -= 5
            one_goal += 3
            two_plus += 2
        elif attack_depth_level in {"LOW", "NONE"}:
            no_goal += 4
            two_plus -= 2

        values = [max(1, no_goal), max(1, one_goal), max(1, two_plus)]
        total = max(1, sum(values))

        new_no_goal = round(values[0] * 100 / total)
        new_one_goal = round(values[1] * 100 / total)
        new_two_plus = max(0, 100 - new_no_goal - new_one_goal)

        return {
            "no_goal": int(new_no_goal),
            "one_goal": int(new_one_goal),
            "two_plus_goals": int(new_two_plus),
        }

    def _apply_pressure_quality_guard(
        self,
        projected_market: str,
        final_market_recommendation: str,
        final_prediction_reason: str,
        conflict_level: str,
        conflict_reasons: List[str],
        goal_probabilities: Dict[str, int],
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
    ) -> Tuple[str, str, str, List[str]]:
        reasons = list(conflict_reasons or [])
        recommendation = final_market_recommendation
        reason = final_prediction_reason
        conflict = conflict_level

        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))
        goal_risk = one_goal + two_plus

        false_or_lateral = pressure_type in {
            "FALSE_PRESSURE",
            "LATERAL_PRESSURE",
            "DOMINANCE_WITHOUT_DEPTH",
        }
        real_pressure = pressure_type in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"} or real_goal_threat == "HIGH"

        if projected_market == "OVER" and false_or_lateral and real_goal_threat in {"LOW", "MEDIUM_LOW", ""}:
            reasons.append("OVER basado en presión lateral o falsa: falta profundidad real de gol.")
            if no_goal >= 42 or two_plus <= 24:
                recommendation = "OBSERVE_OVER_RISK"
                reason = (
                    "OVER queda en observación: hay actividad ofensiva, pero la calidad de presión "
                    "no confirma peligro real suficiente."
                )
                conflict = self._raise_conflict(conflict, "MEDIUM_CONFLICT")

        if projected_market == "UNDER" and real_pressure:
            reasons.append("UNDER contradice presión real o amenaza alta de gol.")
            if goal_risk >= 48:
                recommendation = "OBSERVE_OVER_RISK"
                reason = "UNDER queda en observación porque la presión real mantiene riesgo de gol."
                conflict = self._raise_conflict(conflict, "MEDIUM_CONFLICT")

        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"} and projected_market == "OVER":
            reasons.append("Riesgo de presión falsa contra lectura OVER.")
            conflict = self._raise_conflict(conflict, "LOW_CONFLICT")

        return recommendation, reason, conflict, reasons[:6]

    def _apply_pressure_quality_confidence(
        self,
        prediction_confidence: int,
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        conflict_level: str = "",
    ) -> int:
        confidence = int(prediction_confidence)

        if pressure_type == "REAL_PRESSURE" or real_goal_threat == "HIGH":
            confidence += 7
        elif pressure_type == "HIGH_THREAT_PRESSURE":
            confidence += 5
        elif pressure_type in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
            if real_goal_threat in {"LOW", "MEDIUM_LOW", ""}:
                confidence -= 8

        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"}:
            confidence -= 5

        if pressure_game_state in {"OPEN_GAME", "BROKEN_GAME", "PANIC_GAME"}:
            confidence += 4
        elif pressure_game_state in {"LOW_ACTIVITY_GAME", "CONTROLLED_GAME", "DEAD_GAME"}:
            confidence -= 2

        if conflict_level in {"HIGH_CONFLICT", "CRITICAL_CONFLICT"}:
            confidence -= 6

        return max(0, min(100, int(confidence)))

    def _append_pressure_support_points(
        self,
        support_points: List[str],
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        pressure_reading: str = "",
    ) -> List[str]:
        points = list(support_points or [])

        if pressure_type:
            points.append(f"Calidad de presión: {pressure_type}.")
        if pressure_game_state:
            points.append(f"Estado del partido por presión: {pressure_game_state}.")
        if real_goal_threat:
            points.append(f"Amenaza real de gol: {real_goal_threat}.")
        if pressure_reading:
            points.append(str(pressure_reading))

        return points[:8]

    def _append_pressure_caution_points(
        self,
        caution_points: List[str],
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        pressure_reading: str = "",
    ) -> List[str]:
        cautions = list(caution_points or [])

        if pressure_type in {"FALSE_PRESSURE", "LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}:
            cautions.append("La presión puede ser territorial o lateral; no confirma peligro real por sí sola.")
        if false_pressure_risk in {"HIGH", "MEDIUM_HIGH"}:
            cautions.append("Riesgo de presión falsa: no elevar OVER sin tiros al arco o ataques peligrosos.")
        if pressure_reading:
            cautions.append(str(pressure_reading))

        return cautions[:8]

    def _append_pressure_panel_message(
        self,
        panel_message: str,
        pressure_type: str = "",
        pressure_game_state: str = "",
        real_goal_threat: str = "",
        false_pressure_risk: str = "",
        pressure_reading: str = "",
    ) -> str:
        extras = []

        if pressure_type:
            extras.append(f"Presión: {pressure_type}")
        if real_goal_threat:
            extras.append(f"amenaza real: {real_goal_threat}")
        if false_pressure_risk:
            extras.append(f"riesgo de presión falsa: {false_pressure_risk}")
        if pressure_game_state:
            extras.append(f"estado: {pressure_game_state}")

        if not extras:
            return panel_message

        suffix = " Lectura de presión: " + "; ".join(extras) + "."
        if pressure_reading:
            suffix += f" {pressure_reading}"

        return f"{panel_message}{suffix}"

    def _raise_conflict(self, current: str, target: str) -> str:
        order = {
            "NO_CONFLICT": 0,
            "LOW_CONFLICT": 1,
            "MEDIUM_CONFLICT": 2,
            "HIGH_CONFLICT": 3,
            "CRITICAL_CONFLICT": 4,
        }
        current_level = order.get(str(current or "NO_CONFLICT"), 0)
        target_level = order.get(str(target or "NO_CONFLICT"), 0)
        reverse = {value: key for key, value in order.items()}
        return reverse.get(max(current_level, target_level), "NO_CONFLICT")

    def _detect_phase(self, minute: int) -> str:
        if minute <= 10:
            return "INITIAL_READING"
        if minute <= 25:
            return "EARLY_FIRST_HALF"
        if minute <= 40:
            return "FIRST_HALF_PREDICTION_ZONE"
        if minute <= 45:
            return "FIRST_HALF_CLOSING"
        if minute <= 60:
            return "SECOND_HALF_READING"
        if minute <= 75:
            return "STRONG_LIVE_PREDICTION_ZONE"
        if minute <= 86:
            return "LATE_GOAL_OPPORTUNITY_ZONE"
        return "HIGH_RISK_FINAL_ZONE"

    def _detect_scenario(
        self,
        minute: int,
        total_goals: float,
        market: str,
        activation_market: str,
        promotion_market: str,
        over_watch: bool,
        under_watch: bool,
        pressure: float,
        rhythm: float,
        volume: float,
        risk: float,
        activation_level: str,
        activation_score: float,
        promotion_level: str,
        promotion_score: float,
        panel_section: str,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
    ) -> str:
        live_force = max(pressure, rhythm, volume)
        elite_international = self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        )

        if activation_level == "BLOCKED" or "BLOCKED" in promotion_level:
            return "BLOCKED_SCENARIO"

        strong_over_activation = (
            activation_level in {
                "EARLY_OVER_CANDIDATE",
                "STRONG_CANDIDATE",
                "MAIN_SIGNAL",
                "TOP_SIGNAL",
            }
            and activation_market == "OVER"
            and activation_score >= 74
        )

        early_over_panel = (
            "OVER_EARLY" in panel_section
            or "OVER_HIGH" in panel_section
            or panel_section == "OVER_HIGH_OBSERVATION"
        )

        if strong_over_activation and risk < 80:
            if live_force >= 55:
                return "GOAL_RISK_ALIVE"
            return "OVER_WATCH_RISK"

        if over_watch and activation_score >= 82 and risk < 80:
            if live_force >= 50:
                return "GOAL_RISK_ALIVE"
            return "OVER_WATCH_RISK"

        if early_over_panel and over_watch and risk < 80:
            if live_force >= 55:
                return "GOAL_RISK_ALIVE"
            return "BALANCED_OVER_WATCH"

        if over_watch and live_force >= 68 and risk <= 72:
            if minute >= 70:
                if elite_international and live_force < 76:
                    return "ELITE_LATE_OVER_REQUIRES_CONFIRMATION"
                return "LATE_GOAL_POSSIBLE"
            return "OPEN_BREAKING_SCENARIO"

        if over_watch and live_force >= 55 and risk <= 75:
            return "GOAL_RISK_ALIVE"

        if market == "OVER" and live_force >= 55:
            return "OPEN_MATCH"

        if under_watch and over_watch:
            if live_force >= 45 or activation_market == "OVER":
                return "UNDER_WITH_RUPTURE_RISK"
            return "BALANCED_OBSERVATION"

        if under_watch and live_force < 48 and total_goals <= 2:
            return "UNDER_CONSERVATION"

        if live_force >= 75 and risk >= 70:
            return "CHAOTIC_MATCH"

        if minute >= 75 and live_force < 45:
            return "LATE_CONTROLLED_CLOSING"

        return "BALANCED_OBSERVATION"

    def _next_goal_probability(
        self,
        minute: int,
        phase: str,
        scenario: str,
        over_watch: bool,
        pressure: float,
        rhythm: float,
        volume: float,
        risk: float,
        over_score: float,
        under_score: float,
        maturity: float,
        activation_level: str,
        activation_score: float,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
    ) -> str:
        live_force = max(pressure, rhythm, volume)
        score = 30

        if over_watch:
            score += 14
        if activation_level == "EARLY_OVER_CANDIDATE":
            score += 12
        if activation_level in {"STRONG_CANDIDATE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
            score += 10
        if activation_score >= 75:
            score += 6
        if activation_score >= 88:
            score += 6

        if live_force >= 55:
            score += 12
        if live_force >= 65:
            score += 10
        if live_force >= 75:
            score += 7

        if over_score >= 45:
            score += 5
        if over_score >= 55:
            score += 8
        if over_score >= 65:
            score += 8

        if maturity >= 60:
            score += 5
        if maturity >= 72:
            score += 6

        if phase in {"FIRST_HALF_PREDICTION_ZONE", "STRONG_LIVE_PREDICTION_ZONE"}:
            score += 8
        if phase == "LATE_GOAL_OPPORTUNITY_ZONE":
            score += 5
        if phase == "HIGH_RISK_FINAL_ZONE":
            score -= 12

        if risk >= 78:
            score -= 12

        if scenario in {"OPEN_BREAKING_SCENARIO", "LATE_GOAL_POSSIBLE", "GOAL_RISK_ALIVE"}:
            score += 10

        if scenario == "ELITE_LATE_OVER_REQUIRES_CONFIRMATION":
            score += 3

        if scenario in {"OVER_WATCH_RISK", "BALANCED_OVER_WATCH", "UNDER_WITH_RUPTURE_RISK"}:
            score += 6

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            score -= 15

        if under_score >= 70 and not over_watch:
            score -= 10

        # Elite national-team tournaments are less tolerant of late false OVERs.
        # Do not block prediction, only calibrate it down unless live force is truly strong.
        if self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        ):
            if minute >= 70 and live_force < 72 and scenario not in {"LATE_GOAL_POSSIBLE", "OPEN_BREAKING_SCENARIO"}:
                score -= 8
            elif minute >= 70 and live_force >= 78:
                score += 3

        score = max(0, min(100, int(score)))

        if score >= 76:
            return "HIGH"
        if score >= 62:
            return "MEDIUM_HIGH"
        if score >= 48:
            return "MEDIUM"
        if score >= 35:
            return "LOW_MEDIUM"
        return "LOW"

    def _detect_attacking_context(
        self,
        home_team: str,
        away_team: str,
        home_danger: float,
        away_danger: float,
        home_shots: float,
        away_shots: float,
        home_sot: float,
        away_sot: float,
        home_score: float,
        away_score: float,
    ) -> Tuple[str, str]:
        home_force = home_danger * 0.45 + home_shots * 1.2 + home_sot * 2.2
        away_force = away_danger * 0.45 + away_shots * 1.2 + away_sot * 2.2

        if home_score < away_score:
            home_force += 6
        if away_score < home_score:
            away_force += 6

        if home_force > away_force + 5:
            return home_team, "HOME"
        if away_force > home_force + 5:
            return away_team, "AWAY"

        return "Sin amenaza clara", "NONE"

    def _predict_score(
        self,
        home_score: float,
        away_score: float,
        attacking_side: str,
        next_goal_probability: str,
        scenario: str,
        minute: int,
    ) -> str:
        h = int(home_score)
        a = int(away_score)

        goal_likely = next_goal_probability in {"HIGH", "MEDIUM_HIGH"}

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return f"{h}-{a}"

        if not goal_likely:
            return f"{h}-{a}"

        if attacking_side == "HOME":
            return f"{h + 1}-{a}"
        if attacking_side == "AWAY":
            return f"{h}-{a + 1}"

        if h < a:
            return f"{h + 1}-{a}"
        if a < h:
            return f"{h}-{a + 1}"

        return f"{h + 1}-{a}"

    def _alternative_score(
        self,
        home_score: float,
        away_score: float,
        predicted_score: str,
        scenario: str,
        minute: int,
    ) -> str:
        h = int(home_score)
        a = int(away_score)

        if scenario in {"OPEN_BREAKING_SCENARIO", "CHAOTIC_MATCH"}:
            return f"{h + 1}-{a + 1}"

        if scenario == "LATE_GOAL_POSSIBLE":
            return f"{h + 1}-{a}" if h <= a else f"{h}-{a + 1}"

        if scenario in {
            "OVER_WATCH_RISK",
            "BALANCED_OVER_WATCH",
            "UNDER_WITH_RUPTURE_RISK",
            "GOAL_RISK_ALIVE",
        }:
            return f"{h + 1}-{a}" if h <= a else f"{h}-{a + 1}"

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return f"{h}-{a}"

        return predicted_score

    def _predict_halftime_score(
        self,
        minute: int,
        home_score: float,
        away_score: float,
        predicted_score: str,
    ) -> str:
        if minute <= 45:
            return predicted_score

        return f"{int(home_score)}-{int(away_score)}"

    def _predict_final_score(
        self,
        minute: int,
        home_score: float,
        away_score: float,
        predicted_score: str,
        alternative_score: str,
        scenario: str,
    ) -> str:
        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return f"{int(home_score)}-{int(away_score)}"

        if minute >= 86:
            return predicted_score

        if scenario in {
            "OPEN_BREAKING_SCENARIO",
            "LATE_GOAL_POSSIBLE",
            "GOAL_RISK_ALIVE",
            "OVER_WATCH_RISK",
            "BALANCED_OVER_WATCH",
            "UNDER_WITH_RUPTURE_RISK",
            "ELITE_LATE_OVER_REQUIRES_CONFIRMATION",
        }:
            return alternative_score

        return predicted_score

    def _score_scenarios(
        self,
        home_score: float,
        away_score: float,
        predicted_score: str,
        alternative_score: str,
        final_score: str,
        next_goal_probability: str,
        scenario: str,
    ) -> List[Dict[str, Any]]:
        current_score = f"{int(home_score)}-{int(away_score)}"

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return [
                {"score": current_score, "weight": 55, "label": "SCORE_HOLD"},
                {"score": predicted_score, "weight": 30, "label": "CONTROLLED_VARIANT"},
                {"score": alternative_score, "weight": 15, "label": "LOW_RUPTURE"},
            ]

        if next_goal_probability in {"HIGH", "MEDIUM_HIGH"}:
            return [
                {"score": final_score, "weight": 45, "label": "MAIN_LIVE_SCENARIO"},
                {"score": alternative_score, "weight": 32, "label": "OFFENSIVE_VARIANT"},
                {"score": current_score, "weight": 23, "label": "SCORE_HOLD_RISK"},
            ]

        return [
            {"score": current_score, "weight": 42, "label": "CURRENT_HOLD"},
            {"score": predicted_score, "weight": 35, "label": "SINGLE_GOAL_VARIANT"},
            {"score": alternative_score, "weight": 23, "label": "ALTERNATIVE_VARIANT"},
        ]

    def _market_alignment(
        self,
        projected_market: str,
        predicted_score: str,
        alternative_score: str,
        final_score: str,
        current_total_goals: float,
    ) -> str:
        final_goals = self._score_total(final_score)
        predicted_goals = self._score_total(predicted_score)
        alternative_goals = self._score_total(alternative_score)

        if projected_market == "OVER":
            if max(final_goals, predicted_goals, alternative_goals) > current_total_goals:
                return "ALIGNED_WITH_OVER"
            return "OVER_NEEDS_REACTIVATION"

        if projected_market == "UNDER":
            if final_goals <= current_total_goals + 1:
                return "ALIGNED_WITH_UNDER"
            return "UNDER_HAS_RUPTURE_RISK"

        return "NEUTRAL_ALIGNMENT"

    def _score_total(self, score: str) -> int:
        try:
            left, right = str(score or "0-0").split("-")[:2]
            return int(left) + int(right)
        except Exception:
            return 0

    def _goal_count_probabilities(
        self,
        minute: int,
        phase: str,
        scenario: str,
        projected_market: str,
        next_goal_probability: str,
        pressure: float,
        rhythm: float,
        volume: float,
        risk: float,
        over_score: float,
        under_score: float,
        current_total_goals: float,
    ) -> Dict[str, int]:
        """
        Simula escenarios simples de goles restantes.

        Esta capa no intenta adivinar con exactitud matemática. Su objetivo es
        evitar incoherencias: si el sistema dice UNDER, la probabilidad de no gol
        debe dominar; si dice OVER, debe existir soporte real para 1 o 2+ goles.
        """
        live_force = max(pressure, rhythm, volume)

        base_no_goal = 40
        base_one_goal = 38
        base_two_plus = 22

        if next_goal_probability == "HIGH":
            base_no_goal -= 20
            base_one_goal += 12
            base_two_plus += 8
        elif next_goal_probability == "MEDIUM_HIGH":
            base_no_goal -= 12
            base_one_goal += 8
            base_two_plus += 4
        elif next_goal_probability == "MEDIUM":
            base_no_goal -= 5
            base_one_goal += 4
            base_two_plus += 1
        elif next_goal_probability == "LOW":
            base_no_goal += 18
            base_one_goal -= 10
            base_two_plus -= 8

        if live_force >= 75:
            base_no_goal -= 12
            base_one_goal += 6
            base_two_plus += 6
        elif live_force >= 62:
            base_no_goal -= 7
            base_one_goal += 5
            base_two_plus += 2
        elif live_force <= 35:
            base_no_goal += 10
            base_one_goal -= 5
            base_two_plus -= 5

        if scenario in {
            "OPEN_BREAKING_SCENARIO",
            "LATE_GOAL_POSSIBLE",
            "GOAL_RISK_ALIVE",
            "UNDER_WITH_RUPTURE_RISK",
            "OVER_WATCH_RISK",
        }:
            base_no_goal -= 10
            base_one_goal += 6
            base_two_plus += 4

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            base_no_goal += 18
            base_one_goal -= 10
            base_two_plus -= 8

        if projected_market == "UNDER":
            base_no_goal += 8
            base_two_plus -= 6
        elif projected_market == "OVER":
            base_no_goal -= 8
            base_one_goal += 4
            base_two_plus += 4

        if under_score >= over_score + 18:
            base_no_goal += 10
            base_two_plus -= 6
        elif over_score >= under_score + 12:
            base_no_goal -= 10
            base_one_goal += 5
            base_two_plus += 5

        if risk >= 78:
            base_no_goal += 4
            base_two_plus -= 4

        # Late game naturally compresses 2+ goal probability unless match is truly open.
        if minute >= 80 and live_force < 70:
            base_two_plus -= 8
            base_no_goal += 5
            base_one_goal += 3

        values = [max(1, base_no_goal), max(1, base_one_goal), max(1, base_two_plus)]
        total = max(1, sum(values))

        no_goal = round(values[0] * 100 / total)
        one_goal = round(values[1] * 100 / total)
        two_plus = max(0, 100 - no_goal - one_goal)

        return {
            "no_goal": int(no_goal),
            "one_goal": int(one_goal),
            "two_plus_goals": int(two_plus),
        }

    def _prediction_conflict_level(
        self,
        projected_market: str,
        market_alignment: str,
        predicted_score: str,
        alternative_score: str,
        final_score: str,
        current_total_goals: float,
        next_goal_probability: str,
        goal_probabilities: Dict[str, int],
        pressure: float,
        rhythm: float,
        volume: float,
        over_score: float,
        under_score: float,
        over_watch: bool,
        under_watch: bool,
    ) -> Tuple[str, List[str]]:
        reasons: List[str] = []
        live_force = max(pressure, rhythm, volume)
        final_goals = self._score_total(final_score)
        predicted_goals = self._score_total(predicted_score)
        alternative_goals = self._score_total(alternative_score)
        max_projected_goals = max(final_goals, predicted_goals, alternative_goals)

        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))
        goal_risk = one_goal + two_plus

        if projected_market == "UNDER":
            if next_goal_probability in {"HIGH", "MEDIUM_HIGH"}:
                reasons.append("UNDER contradice una probabilidad alta de próximo gol.")
            if max_projected_goals > current_total_goals:
                reasons.append("UNDER contradice un marcador proyectado con más goles.")
            if goal_risk >= 58:
                reasons.append("UNDER contradice escenarios futuros con alto riesgo de gol.")
            if live_force >= 65:
                reasons.append("UNDER contradice presión, ritmo o volumen ofensivo relevante.")
            if over_watch and over_score >= under_score - 10:
                reasons.append("UNDER convive con OVER WATCH competitivo.")

        elif projected_market == "OVER":
            if next_goal_probability in {"LOW", "LOW_MEDIUM"} and no_goal >= 52:
                reasons.append("OVER contradice una probabilidad alta de conservación del marcador.")
            if max_projected_goals <= current_total_goals and no_goal >= 50:
                reasons.append("OVER contradice marcador probable sin goles adicionales.")
            if live_force <= 35 and two_plus <= 18:
                reasons.append("OVER contradice bajo volumen ofensivo real.")
            if under_watch and under_score >= over_score + 15:
                reasons.append("OVER contradice ventaja clara de UNDER.")

        if market_alignment in {"UNDER_HAS_RUPTURE_RISK", "OVER_NEEDS_REACTIVATION"}:
            reasons.append(f"Alineación de mercado advierte {market_alignment}.")

        if len(reasons) >= 4:
            return "CRITICAL_CONFLICT", reasons
        if len(reasons) >= 3:
            return "HIGH_CONFLICT", reasons
        if len(reasons) >= 2:
            return "MEDIUM_CONFLICT", reasons
        if len(reasons) == 1:
            return "LOW_CONFLICT", reasons
        return "NO_CONFLICT", reasons

    def _final_market_recommendation(
        self,
        projected_market: str,
        market_alignment: str,
        conflict_level: str,
        conflict_reasons: List[str],
        goal_probabilities: Dict[str, int],
        over_score: float,
        under_score: float,
        next_goal_probability: str,
        scenario: str,
    ) -> Tuple[str, str]:
        no_goal = int(goal_probabilities.get("no_goal", 0))
        one_goal = int(goal_probabilities.get("one_goal", 0))
        two_plus = int(goal_probabilities.get("two_plus_goals", 0))
        goal_risk = one_goal + two_plus

        if conflict_level in {"HIGH_CONFLICT", "CRITICAL_CONFLICT"}:
            if projected_market == "UNDER" and goal_risk >= 58:
                return (
                    "OBSERVE_OVER_RISK",
                    "La lectura UNDER queda en observación porque los escenarios futuros muestran riesgo real de otro gol.",
                )
            if projected_market == "OVER" and no_goal >= 52:
                return (
                    "OBSERVE_UNDER_RISK",
                    "La lectura OVER queda en observación porque el escenario de conservación del marcador domina.",
                )
            return (
                "OBSERVE_CONFLICT",
                "La predicción detecta conflicto interno entre mercado, marcador probable y próximos goles.",
            )

        if projected_market == "UNDER":
            if no_goal >= 54 and next_goal_probability in {"LOW", "LOW_MEDIUM", "MEDIUM"}:
                return (
                    "UNDER",
                    "UNDER se sostiene porque domina el escenario de conservación y no hay ruptura ofensiva fuerte.",
                )
            if goal_risk >= 55:
                return (
                    "OBSERVE_OVER_RISK",
                    "UNDER no se promueve porque el riesgo de un gol adicional sigue vivo.",
                )

        if projected_market == "OVER":
            if goal_risk >= 56 and next_goal_probability in {"MEDIUM", "MEDIUM_HIGH", "HIGH"}:
                return (
                    "OVER",
                    "OVER se sostiene porque los escenarios futuros favorecen al menos un gol adicional.",
                )
            if no_goal >= 55:
                return (
                    "OBSERVE_UNDER_RISK",
                    "OVER no se promueve porque el marcador tiene probabilidad relevante de conservarse.",
                )

        if market_alignment in {"ALIGNED_WITH_OVER", "ALIGNED_WITH_UNDER"}:
            return projected_market, "Mercado y predicción están alineados sin conflicto crítico."

        return "OBSERVE", "No existe alineación suficiente para emitir una lectura operativa limpia."

    def _apply_prediction_coherence_guard(
        self,
        prediction_confidence: int,
        projected_market: str,
        final_market_recommendation: str,
        market_alignment: str,
        conflict_level: str,
        goal_probabilities: Dict[str, int],
    ) -> int:
        confidence = int(prediction_confidence)

        if conflict_level == "LOW_CONFLICT":
            confidence -= 5
        elif conflict_level == "MEDIUM_CONFLICT":
            confidence -= 12
        elif conflict_level == "HIGH_CONFLICT":
            confidence -= 22
        elif conflict_level == "CRITICAL_CONFLICT":
            confidence -= 32

        if final_market_recommendation.startswith("OBSERVE"):
            confidence -= 8

        if market_alignment in {"ALIGNED_WITH_OVER", "ALIGNED_WITH_UNDER"} and conflict_level == "NO_CONFLICT":
            confidence += 5

        # If future scenarios are clear, give a small confidence reward.
        no_goal = int(goal_probabilities.get("no_goal", 0))
        goal_risk = int(goal_probabilities.get("one_goal", 0)) + int(goal_probabilities.get("two_plus_goals", 0))
        if projected_market == "UNDER" and no_goal >= 60 and conflict_level == "NO_CONFLICT":
            confidence += 4
        if projected_market == "OVER" and goal_risk >= 62 and conflict_level == "NO_CONFLICT":
            confidence += 4

        return max(0, min(100, int(confidence)))

    def _projected_market(
        self,
        scenario: str,
        next_goal_probability: str,
        over_watch: bool,
        under_watch: bool,
        market: str,
        activation_market: str,
        promotion_market: str,
        over_score: float,
        under_score: float,
    ) -> str:
        if scenario in {
            "OPEN_BREAKING_SCENARIO",
            "LATE_GOAL_POSSIBLE",
            "GOAL_RISK_ALIVE",
            "OVER_WATCH_RISK",
            "BALANCED_OVER_WATCH",
            "UNDER_WITH_RUPTURE_RISK",
            "ELITE_LATE_OVER_REQUIRES_CONFIRMATION",
        }:
            return "OVER"

        if next_goal_probability in {"HIGH", "MEDIUM_HIGH"} and over_watch:
            return "OVER"

        if activation_market == "OVER" and over_watch:
            return "OVER"

        if promotion_market == "OVER" and over_watch:
            return "OVER"

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return "UNDER"

        if under_score > over_score + 15 and not over_watch:
            return "UNDER"

        if market in {"OVER", "UNDER"}:
            return market

        return "OBSERVE"

    def _prediction_confidence(
        self,
        minute: int,
        phase: str,
        pressure: float,
        rhythm: float,
        volume: float,
        risk: float,
        maturity: float,
        confidence: float,
        activation_level: str,
        activation_score: float,
        promotion_level: str,
        promotion_score: float,
        scenario: str,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
    ) -> int:
        score = 35

        if phase in {"FIRST_HALF_PREDICTION_ZONE", "STRONG_LIVE_PREDICTION_ZONE"}:
            score += 12

        if phase == "LATE_GOAL_OPPORTUNITY_ZONE":
            score += 7

        if phase in {"INITIAL_READING", "HIGH_RISK_FINAL_ZONE"}:
            score -= 8

        live_force = max(pressure, rhythm, volume)

        if live_force >= 55:
            score += 8
        if live_force >= 65:
            score += 8
        if live_force >= 75:
            score += 5

        if maturity >= 60:
            score += 6

        if confidence >= 60:
            score += 5

        if activation_level in {
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            score += 10

        if activation_score >= 80:
            score += 6

        if promotion_level in {"STRONG_CANDIDATE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
            score += 7

        if promotion_score >= 75:
            score += 4

        if scenario in {
            "OPEN_BREAKING_SCENARIO",
            "UNDER_CONSERVATION",
            "LATE_GOAL_POSSIBLE",
            "OVER_WATCH_RISK",
            "GOAL_RISK_ALIVE",
        }:
            score += 7

        if scenario == "ELITE_LATE_OVER_REQUIRES_CONFIRMATION":
            score -= 5

        if self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        ):
            # Elite competitions add credibility when data is strong, but reduce
            # confidence in late weak-pressure readings.
            if max(pressure, rhythm, volume) >= 72 and risk < 72:
                score += 4
            if minute >= 75 and max(pressure, rhythm, volume) < 62:
                score -= 7

        if risk >= 78:
            score -= 14

        return max(0, min(100, int(score)))

    def _prediction_mode(
        self,
        minute: int,
        activation_level: str,
        promotion_level: str,
        panel_section: str,
        prediction_confidence: int,
    ) -> str:
        if prediction_confidence >= 78:
            return "STRONG_PREDICTION"

        if activation_level in {
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            return "OPERATIVE_PREDICTION"

        if promotion_level in {"STRONG_CANDIDATE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
            return "OPERATIVE_PREDICTION"

        if panel_section in {
            "HIGH_OBSERVATION",
            "OVER_EARLY_CANDIDATE",
            "OVER_HIGH_OBSERVATION",
        }:
            return "PANORAMIC_PREDICTION"

        if minute <= 10:
            return "INITIAL_PANORAMA"

        return "PANORAMIC_PREDICTION"

    def _support_points(
        self,
        phase: str,
        scenario: str,
        projected_market: str,
        next_goal_probability: str,
        attacking_team: str,
        pressure: float,
        rhythm: float,
        volume: float,
        over_watch: bool,
        under_watch: bool,
        activation_level: str,
        activation_score: float,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
    ) -> List[str]:
        points = []

        points.append(f"Fase predictiva: {phase}.")
        points.append(f"Escenario live detectado: {scenario}.")
        points.append(f"Mercado proyectado: {projected_market}.")
        points.append(f"Probabilidad de próximo gol: {next_goal_probability}.")

        if self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        ):
            points.append(f"Contexto competitivo elite: {competition_tier or 'INTERNATIONAL'}.")

        if attacking_team != "Sin amenaza clara":
            points.append(f"Mayor amenaza ofensiva: {attacking_team}.")

        if over_watch:
            points.append("Existe lectura OVER WATCH o riesgo de ruptura.")

        if under_watch:
            points.append("Existe lectura UNDER o tendencia de conservación.")

        if activation_level == "EARLY_OVER_CANDIDATE":
            points.append(f"SignalActivationAI elevó OVER temprano con puntaje {int(activation_score)}.")

        if max(pressure, rhythm, volume) >= 65:
            points.append("La presión, ritmo o volumen ofensivo sostienen la predicción.")

        return points[:8]

    def _caution_points(
        self,
        minute: int,
        risk: float,
        scenario: str,
        prediction_confidence: int,
        over_watch: bool,
        under_watch: bool,
        alternative_reading: str,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
        conflict_level: str = "",
        conflict_reasons: List[str] | None = None,
    ) -> List[str]:
        cautions = []
        conflict_reasons = conflict_reasons or []

        if minute <= 10:
            cautions.append("Minuto temprano. La predicción todavía es panorámica.")

        if minute >= 87:
            cautions.append("Minuto final. Alto riesgo de predicción tardía.")

        if risk >= 72:
            cautions.append("Riesgo operativo elevado. No aumentar confianza sin soporte adicional.")

        if prediction_confidence < 55:
            cautions.append("Confianza predictiva moderada o baja.")

        if under_watch and over_watch:
            cautions.append("Hay tensión entre conservación UNDER y ruptura OVER.")

        if alternative_reading:
            cautions.append(f"Lectura alternativa activa: {alternative_reading}.")

        if scenario == "CHAOTIC_MATCH":
            cautions.append("Partido caótico. Puede favorecer gol, pero aumenta incertidumbre.")

        if scenario == "ELITE_LATE_OVER_REQUIRES_CONFIRMATION":
            cautions.append("Torneo elite en tramo tardío: OVER requiere confirmación real adicional.")

        if self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        ) and minute >= 70:
            cautions.append("Competición internacional elite: evitar entrada tardía sin presión profunda.")

        if conflict_level in {"MEDIUM_CONFLICT", "HIGH_CONFLICT", "CRITICAL_CONFLICT"}:
            cautions.append(f"Conflicto predictivo detectado: {conflict_level}.")
            for reason in conflict_reasons[:2]:
                cautions.append(str(reason))

        return cautions[:8]

    def _panel_message(
        self,
        phase: str,
        scenario: str,
        predicted_score: str,
        alternative_score: str,
        next_goal_probability: str,
        projected_market: str,
        attacking_team: str,
        prediction_mode: str,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
        market_alignment: str = "",
        conflict_level: str = "",
        final_market_recommendation: str = "",
        goal_probabilities: Dict[str, int] | None = None,
    ) -> str:
        competition_note = ""
        goal_probabilities = goal_probabilities or {}
        if self._is_elite_international(
            competition_tier=competition_tier,
            competition_weight=competition_weight,
            world_cup_flag=world_cup_flag,
            national_team_flag=national_team_flag,
            major_tournament_flag=major_tournament_flag,
        ):
            competition_note = f" Contexto elite: {competition_tier or 'INTERNATIONAL'}."

        return (
            f"Predicción {prediction_mode}: escenario {scenario}. "
            f"Resultado probable {predicted_score}; alternativa {alternative_score}. "
            f"Próximo gol: {next_goal_probability}. "
            f"Mercado proyectado: {projected_market}. "
            f"Recomendación final: {final_market_recommendation or projected_market}. "
            f"Probabilidades: sin gol {goal_probabilities.get('no_goal', 0)}%, "
            f"un gol {goal_probabilities.get('one_goal', 0)}%, "
            f"dos o más goles {goal_probabilities.get('two_plus_goals', 0)}%. "
            f"Alineación: {market_alignment or 'NEUTRAL_ALIGNMENT'}. "
            f"Conflicto: {conflict_level or 'NO_CONFLICT'}. "
            f"Amenaza principal: {attacking_team}. "
            f"Fase: {phase}."
            f"{competition_note}"
        )

    def _detect_market(self, signal: Dict[str, Any]) -> str:
        values = [
            signal.get("activation_market"),
            signal.get("promotion_market"),
            signal.get("panel_market"),
            signal.get("master_market"),
            signal.get("market"),
            signal.get("suggested_market"),
            signal.get("football_dominant_reading"),
            signal.get("narrative_reading_name"),
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

    def _has_over_watch(self, signal: Dict[str, Any], market: str) -> bool:
        if market == "OVER":
            return True

        values = [
            signal.get("over_candidate_level"),
            signal.get("panel_signal_type"),
            signal.get("football_dominant_reading"),
            signal.get("football_alternative_reading"),
            signal.get("panel_narrative_alternative"),
            signal.get("narrative_alternative_message"),
            signal.get("activation_label"),
            signal.get("panel_activation_label"),
            signal.get("activation_market"),
            signal.get("promotion_market"),
            signal.get("master_action"),
            signal.get("master_reason"),
        ]

        return any("OVER" in self._txt(value) for value in values)

    def _has_under_watch(
        self,
        signal: Dict[str, Any],
        market: str,
        football_reading: str,
    ) -> bool:
        if market == "UNDER":
            return True

        values = [
            football_reading,
            signal.get("activation_market"),
            signal.get("promotion_market"),
            signal.get("panel_signal_type"),
            signal.get("panel_promotion_label"),
            signal.get("panel_activation_label"),
            signal.get("master_reason"),
            signal.get("recommended_panel_message"),
        ]

        return any("UNDER" in self._txt(value) for value in values)

    def _is_elite_international(
        self,
        competition_tier: str = "",
        competition_weight: float = 0.0,
        world_cup_flag: bool = False,
        national_team_flag: bool = False,
        major_tournament_flag: bool = False,
    ) -> bool:
        tier = self._txt(competition_tier)
        return (
            world_cup_flag
            or major_tournament_flag
            or competition_weight >= 88
            or tier in {
                "WORLD_CUP_ELITE",
                "NATIONAL_TEAM_ELITE",
                "INTERNATIONAL_CLUB_ELITE",
                "ELITE",
            }
            or (national_team_flag and competition_weight >= 75)
        )

    def _bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        text = self._txt(value)

        if text in {"1", "TRUE", "YES", "SI", "SÍ", "Y"}:
            return True

        if text in {"0", "FALSE", "NO", "N"}:
            return False

        try:
            return float(value) > 0
        except Exception:
            return False

    def _minute(self, signal: Dict[str, Any]) -> int:
        for key in ["display_minute", "api_minute", "estimated_minute", "minute"]:
            value = signal.get(key)
            n = self._num(value)
            if n > 0:
                return int(n)
        return 0

    def _num(self, value: Any) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _txt(self, value: Any) -> str:
        return str(value or "").strip().upper()
