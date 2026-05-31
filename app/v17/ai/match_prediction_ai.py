from typing import Any, Dict, List


class MatchPredictionAI:
    """
    V17_MATCH_PREDICTION_AI

    Capa predictiva live para proyectar escenario del partido.

    No decide entrada.
    No reemplaza SignalActivationAI.
    No reemplaza SignalPromotionAI.

    Su función es responder:
    - Qué escenario parece más probable.
    - Si hay riesgo de próximo gol.
    - Qué equipo amenaza más.
    - Qué resultado probable se proyecta.
    - Qué mercado se beneficia.
    - Qué tan confiable es la predicción.
    """

    VERSION = "V17_MATCH_PREDICTION_AI_1"

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
        confidence = self._num(
            signal.get("activation_score")
            or signal.get("promotion_score")
            or signal.get("master_confidence")
            or signal.get("football_confidence")
        )

        home_danger = self._num(signal.get("home_dangerous_attacks"))
        away_danger = self._num(signal.get("away_dangerous_attacks"))
        home_shots = self._num(signal.get("home_shots"))
        away_shots = self._num(signal.get("away_shots"))
        home_sot = self._num(signal.get("home_shots_on_target"))
        away_sot = self._num(signal.get("away_shots_on_target"))

        activation_level = self._txt(signal.get("activation_level"))
        promotion_level = self._txt(signal.get("promotion_level"))
        panel_section = self._txt(signal.get("panel_section"))
        football_reading = self._txt(signal.get("football_dominant_reading"))
        alternative_reading = self._txt(signal.get("football_alternative_reading"))

        over_watch = self._has_over_watch(signal, market)
        under_watch = market == "UNDER" or "UNDER" in football_reading

        attacking_team = self._detect_attacking_team(
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
            over_watch=over_watch,
            under_watch=under_watch,
            pressure=pressure,
            rhythm=rhythm,
            volume=volume,
            risk=risk,
            activation_level=activation_level,
            promotion_level=promotion_level,
            panel_section=panel_section,
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
        )

        predicted_score = self._predict_score(
            home_score=home_score,
            away_score=away_score,
            attacking_team=attacking_team,
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
            promotion_level=promotion_level,
            scenario=scenario,
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
        )

        caution_points = self._caution_points(
            minute=minute,
            risk=risk,
            scenario=scenario,
            prediction_confidence=prediction_confidence,
            over_watch=over_watch,
            under_watch=under_watch,
            alternative_reading=alternative_reading,
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
        )

        return {
            "match_prediction_version": self.VERSION,
            "prediction_phase": phase,
            "prediction_mode": prediction_mode,
            "prediction_scenario": scenario,
            "prediction_market": projected_market,
            "prediction_score": predicted_score,
            "prediction_alternative_score": alternative_score,
            "prediction_next_goal_probability": next_goal_probability,
            "prediction_attacking_team": attacking_team,
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
        over_watch: bool,
        under_watch: bool,
        pressure: float,
        rhythm: float,
        volume: float,
        risk: float,
        activation_level: str,
        promotion_level: str,
        panel_section: str,
    ) -> str:
        live_force = max(pressure, rhythm, volume)

        if activation_level == "BLOCKED" or "BLOCKED" in promotion_level:
            return "BLOCKED_SCENARIO"

        if over_watch and live_force >= 68 and risk <= 72:
            if minute >= 70:
                return "LATE_GOAL_POSSIBLE"
            return "OPEN_BREAKING_SCENARIO"

        if over_watch and live_force >= 55 and risk <= 75:
            return "GOAL_RISK_ALIVE"

        if market == "OVER" and live_force >= 55:
            return "OPEN_MATCH"

        if under_watch and live_force < 48 and total_goals <= 2:
            return "UNDER_CONSERVATION"

        if under_watch and over_watch:
            return "UNDER_WITH_RUPTURE_RISK"

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
    ) -> str:
        live_force = max(pressure, rhythm, volume)

        score = 30

        if over_watch:
            score += 14

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

        if scenario in {"OPEN_BREAKING_SCENARIO", "LATE_GOAL_POSSIBLE"}:
            score += 10

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            score -= 15

        if under_score >= 70 and not over_watch:
            score -= 10

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

    def _detect_attacking_team(
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
    ) -> str:
        home_force = home_danger * 0.45 + home_shots * 1.2 + home_sot * 2.2
        away_force = away_danger * 0.45 + away_shots * 1.2 + away_sot * 2.2

        if home_score < away_score:
            home_force += 6

        if away_score < home_score:
            away_force += 6

        if home_force > away_force + 5:
            return home_team

        if away_force > home_force + 5:
            return away_team

        return "Sin amenaza clara"

    def _predict_score(
        self,
        home_score: float,
        away_score: float,
        attacking_team: str,
        next_goal_probability: str,
        scenario: str,
        minute: int,
    ) -> str:
        h = int(home_score)
        a = int(away_score)

        goal_likely = next_goal_probability in {"HIGH", "MEDIUM_HIGH"}

        if not goal_likely:
            return f"{h}-{a}"

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return f"{h}-{a}"

        if attacking_team == "Local":
            return f"{h + 1}-{a}"

        if attacking_team == "Visitante":
            return f"{h}-{a + 1}"

        if attacking_team not in {"Sin amenaza clara", ""}:
            return f"{h + 1}-{a}" if h <= a else f"{h}-{a + 1}"

        if h < a:
            return f"{h + 1}-{a}"

        if a < h:
            return f"{h}-{a + 1}"

        if minute >= 70:
            return f"{h + 1}-{a}"

        return f"{h}-{a}"

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

        if scenario in {"UNDER_CONSERVATION", "LATE_CONTROLLED_CLOSING"}:
            return f"{h}-{a}"

        return predicted_score

    def _projected_market(
        self,
        scenario: str,
        next_goal_probability: str,
        over_watch: bool,
        under_watch: bool,
        market: str,
        over_score: float,
        under_score: float,
    ) -> str:
        if scenario in {"OPEN_BREAKING_SCENARIO", "LATE_GOAL_POSSIBLE", "GOAL_RISK_ALIVE"}:
            return "OVER"

        if next_goal_probability in {"HIGH", "MEDIUM_HIGH"} and over_watch:
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
        promotion_level: str,
        scenario: str,
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

        if promotion_level in {"STRONG_CANDIDATE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
            score += 7

        if scenario in {"OPEN_BREAKING_SCENARIO", "UNDER_CONSERVATION", "LATE_GOAL_POSSIBLE"}:
            score += 7

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

        if panel_section in {"HIGH_OBSERVATION", "OVER_EARLY_CANDIDATE"}:
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
    ) -> List[str]:
        points = []

        points.append(f"Fase predictiva: {phase}.")
        points.append(f"Escenario live detectado: {scenario}.")
        points.append(f"Mercado proyectado: {projected_market}.")
        points.append(f"Probabilidad de próximo gol: {next_goal_probability}.")

        if attacking_team != "Sin amenaza clara":
            points.append(f"Mayor amenaza ofensiva: {attacking_team}.")

        if over_watch:
            points.append("Existe lectura OVER WATCH o riesgo de ruptura.")

        if under_watch:
            points.append("Existe lectura UNDER o tendencia de conservación.")

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
    ) -> List[str]:
        cautions = []

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
    ) -> str:
        return (
            f"Predicción {prediction_mode}: escenario {scenario}. "
            f"Resultado probable {predicted_score}, alternativa {alternative_score}. "
            f"Próximo gol: {next_goal_probability}. "
            f"Mercado proyectado: {projected_market}. "
            f"Amenaza principal: {attacking_team}. "
            f"Fase: {phase}."
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
        ]

        return any("OVER" in self._txt(value) for value in values)

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
