from typing import Any, Dict


class PressureQualityAI:
    """
    V17_PRESSURE_QUALITY_AI

    Este módulo no decide apuestas.
    Su función es interpretar la calidad real de la presión del partido.

    Distingue:
    - presión real de gol
    - presión falsa (volumen sin peligro)
    - dominio territorial sin profundidad
    - partidos controlados
    - partidos abiertos
    - baja actividad ofensiva real

    Mejora V17.2:
    - Aprovecha los nuevos datos enriquecidos del live_match_fetcher.py.
    - Diferencia volumen ofensivo de evidencia real de gol.
    - Usa tiros dentro del área, tiros bloqueados, paradas del portero,
      tiros fuera, posesión y pases para leer mejor profundidad y amenaza.
    - Mantiene compatibilidad con los campos antiguos de V17.
    """

    VERSION = "V17_PRESSURE_QUALITY_AI_2"

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        shots = self._num(match.get("shots"))
        shots_on_target = self._num(match.get("shots_on_target"))
        shots_off_goal = self._num(match.get("shots_off_goal"))
        blocked_shots = self._num(match.get("blocked_shots"))
        shots_inside_box = self._num(match.get("shots_inside_box"))
        shots_outside_box = self._num(match.get("shots_outside_box"))
        goalkeeper_saves = self._num(match.get("goalkeeper_saves"))
        corners = self._num(match.get("corners"))
        xg = self._num(match.get("xg") if match.get("xg") is not None else match.get("xG"))
        xg_available = bool(match.get("xg_available"))
        dangerous_attacks = self._num(match.get("dangerous_attacks"))
        possession_home = self._num(match.get("possession_home") or match.get("home_possession"))
        possession_away = self._num(match.get("possession_away") or match.get("away_possession"))
        total_passes = self._num(match.get("total_passes"))
        passes_accurate = self._num(match.get("passes_accurate"))
        pass_accuracy = self._num(match.get("pass_accuracy"))
        red_cards = self._num(match.get("red_cards"))
        yellow_cards = self._num(match.get("yellow_cards"))

        home_score = self._num(match.get("home_score"))
        away_score = self._num(match.get("away_score"))
        minute = self._num(match.get("api_minute") or match.get("minute"))

        pressure_score = self._calculate_pressure_score(
            shots=shots,
            sot=shots_on_target,
            corners=corners,
            xg=xg,
            da=dangerous_attacks,
            shots_inside_box=shots_inside_box,
            blocked_shots=blocked_shots,
            goalkeeper_saves=goalkeeper_saves,
            shots_off_goal=shots_off_goal,
        )

        attack_quality_score = self._calculate_attack_quality_score(
            shots=shots,
            sot=shots_on_target,
            shots_inside_box=shots_inside_box,
            blocked_shots=blocked_shots,
            goalkeeper_saves=goalkeeper_saves,
            xg=xg,
            xg_available=xg_available,
            corners=corners,
        )

        box_pressure_score = self._calculate_box_pressure_score(
            shots_inside_box=shots_inside_box,
            blocked_shots=blocked_shots,
            goalkeeper_saves=goalkeeper_saves,
            sot=shots_on_target,
        )

        volume_score = self._calculate_volume_score(
            shots=shots,
            shots_off_goal=shots_off_goal,
            shots_outside_box=shots_outside_box,
            corners=corners,
        )

        transition_risk_score = self._calculate_transition_risk_score(
            match=match,
            shots_on_target=shots_on_target,
            shots_inside_box=shots_inside_box,
            goalkeeper_saves=goalkeeper_saves,
            possession_home=possession_home,
            possession_away=possession_away,
            home_score=home_score,
            away_score=away_score,
        )

        pressure_type = self._classify_pressure(
            shots=shots,
            sot=shots_on_target,
            corners=corners,
            xg=xg,
            da=dangerous_attacks,
            shots_inside_box=shots_inside_box,
            blocked_shots=blocked_shots,
            goalkeeper_saves=goalkeeper_saves,
            attack_quality_score=attack_quality_score,
            box_pressure_score=box_pressure_score,
            volume_score=volume_score,
        )

        game_state = self._classify_game_state(
            minute=minute,
            home=home_score,
            away=away_score,
            pressure_score=pressure_score,
            attack_quality_score=attack_quality_score,
            transition_risk_score=transition_risk_score,
        )

        dominant_team = self._detect_dominance(
            match=match,
            attack_quality_score=attack_quality_score,
            possession_home=possession_home,
            possession_away=possession_away,
        )

        real_goal_threat = self._goal_threat(
            sot=shots_on_target,
            xg=xg,
            da=dangerous_attacks,
            shots_inside_box=shots_inside_box,
            blocked_shots=blocked_shots,
            goalkeeper_saves=goalkeeper_saves,
            attack_quality_score=attack_quality_score,
        )

        false_pressure_risk = self._false_pressure_risk(
            shots=shots,
            sot=shots_on_target,
            da=dangerous_attacks,
            shots_inside_box=shots_inside_box,
            shots_outside_box=shots_outside_box,
            blocked_shots=blocked_shots,
            attack_quality_score=attack_quality_score,
            volume_score=volume_score,
        )

        return {
            "pressure_quality_version": self.VERSION,
            "pressure_type": pressure_type,
            "pressure_score": round(pressure_score, 2),
            "attack_quality_score": round(attack_quality_score, 2),
            "box_pressure_score": round(box_pressure_score, 2),
            "volume_score": round(volume_score, 2),
            "transition_risk_score": round(transition_risk_score, 2),
            "game_state": game_state,
            "dominant_team": dominant_team,
            "real_goal_threat": real_goal_threat,
            "false_pressure_risk": false_pressure_risk,
            "shots": shots,
            "shots_on_target": shots_on_target,
            "shots_off_goal": shots_off_goal,
            "blocked_shots": blocked_shots,
            "shots_inside_box": shots_inside_box,
            "shots_outside_box": shots_outside_box,
            "goalkeeper_saves": goalkeeper_saves,
            "corners": corners,
            "xg": xg,
            "xg_available": xg_available,
            "dangerous_attacks": dangerous_attacks,
            "possession_home": possession_home,
            "possession_away": possession_away,
            "total_passes": total_passes,
            "passes_accurate": passes_accurate,
            "pass_accuracy": pass_accuracy,
            "red_cards": red_cards,
            "yellow_cards": yellow_cards,
            "pressure_reading": self._final_reading(
                pressure_type=pressure_type,
                threat=real_goal_threat,
                false_risk=false_pressure_risk,
                transition_risk_score=transition_risk_score,
            ),
        }

    # -------------------------
    # CORE LOGIC
    # -------------------------

    def _calculate_pressure_score(
        self,
        shots,
        sot,
        corners,
        xg,
        da,
        shots_inside_box=0.0,
        blocked_shots=0.0,
        goalkeeper_saves=0.0,
        shots_off_goal=0.0,
    ):
        """
        Presión general del partido.
        Mantiene el concepto antiguo, pero ahora agrega evidencia de área.
        """
        return min(
            100.0,
            shots * 0.8
            + sot * 4.0
            + corners * 1.2
            + xg * 10.0
            + da * 1.5
            + shots_inside_box * 2.8
            + blocked_shots * 1.7
            + goalkeeper_saves * 2.5
            + shots_off_goal * 0.5,
        )

    def _calculate_attack_quality_score(
        self,
        shots,
        sot,
        shots_inside_box,
        blocked_shots,
        goalkeeper_saves,
        xg,
        xg_available,
        corners,
    ):
        """
        Evidencia real de gol.
        No premia demasiado el volumen vacío; premia área, arco y portero exigido.
        """
        xg_component = xg * 18.0 if xg_available else 0.0
        return min(
            100.0,
            sot * 14.0
            + shots_inside_box * 8.0
            + blocked_shots * 4.0
            + goalkeeper_saves * 7.0
            + corners * 1.5
            + xg_component,
        )

    def _calculate_box_pressure_score(self, shots_inside_box, blocked_shots, goalkeeper_saves, sot):
        return min(
            100.0,
            shots_inside_box * 12.0
            + blocked_shots * 6.0
            + goalkeeper_saves * 8.0
            + sot * 9.0,
        )

    def _calculate_volume_score(self, shots, shots_off_goal, shots_outside_box, corners):
        return min(
            100.0,
            shots * 4.5
            + shots_off_goal * 2.0
            + shots_outside_box * 1.8
            + corners * 2.5,
        )

    def _calculate_transition_risk_score(
        self,
        match,
        shots_on_target,
        shots_inside_box,
        goalkeeper_saves,
        possession_home,
        possession_away,
        home_score,
        away_score,
    ):
        """
        Riesgo de ruptura: equipo con menos posesión pero señales de daño real.
        Es una lectura conservadora para no inventar contraataques sin evidencia.
        """
        home_stats = match.get("home_stats") or {}
        away_stats = match.get("away_stats") or {}

        home_pos = self._num(home_stats.get("possession")) or possession_home
        away_pos = self._num(away_stats.get("possession")) or possession_away

        home_threat = (
            self._num(home_stats.get("shots_on_target")) * 10.0
            + self._num(home_stats.get("shots_inside_box")) * 7.0
            + self._num(home_stats.get("blocked_shots")) * 3.0
        )
        away_threat = (
            self._num(away_stats.get("shots_on_target")) * 10.0
            + self._num(away_stats.get("shots_inside_box")) * 7.0
            + self._num(away_stats.get("blocked_shots")) * 3.0
        )

        lower_pos_threat = 0.0
        if home_pos + 12 < away_pos and home_threat >= 10:
            lower_pos_threat = home_threat
        elif away_pos + 12 < home_pos and away_threat >= 10:
            lower_pos_threat = away_threat

        score_pressure_bonus = 8.0 if abs(home_score - away_score) <= 1 else 2.0
        keeper_activity_bonus = min(12.0, goalkeeper_saves * 3.0)
        direct_box_bonus = min(18.0, shots_inside_box * 3.0 + shots_on_target * 4.0)

        return min(
            100.0,
            lower_pos_threat + score_pressure_bonus + keeper_activity_bonus + direct_box_bonus,
        )

    def _classify_pressure(
        self,
        shots,
        sot,
        corners,
        xg,
        da,
        shots_inside_box=0.0,
        blocked_shots=0.0,
        goalkeeper_saves=0.0,
        attack_quality_score=0.0,
        box_pressure_score=0.0,
        volume_score=0.0,
    ):
        if attack_quality_score >= 58 or (sot >= 3 and shots_inside_box >= 3):
            return "REAL_PRESSURE"

        if box_pressure_score >= 45:
            return "HIGH_THREAT_PRESSURE"

        if volume_score >= 55 and attack_quality_score < 25:
            return "FALSE_PRESSURE"

        if shots >= 10 and sot == 0 and shots_inside_box <= 1:
            return "FALSE_PRESSURE"

        if shots >= 8 and da == 0 and shots_inside_box <= 2 and sot <= 1:
            return "LATERAL_PRESSURE"

        if corners >= 5 and sot <= 1 and shots_inside_box <= 2:
            return "DOMINANCE_WITHOUT_DEPTH"

        if xg >= 1.2 or attack_quality_score >= 42:
            return "HIGH_THREAT_PRESSURE"

        if attack_quality_score >= 25:
            return "MEDIUM_THREAT_PRESSURE"

        return "LOW_PRESSURE"

    def _classify_game_state(
        self,
        minute,
        home,
        away,
        pressure_score,
        attack_quality_score=0.0,
        transition_risk_score=0.0,
    ):
        if minute >= 75 and attack_quality_score < 25:
            return "CLOSING_GAME"

        if transition_risk_score >= 45:
            return "BREAK_RISK_GAME"

        if home != away and (pressure_score > 22 or attack_quality_score >= 35):
            return "BROKEN_GAME"

        if attack_quality_score >= 45 or pressure_score >= 28:
            return "OPEN_GAME"

        if pressure_score >= 12 or attack_quality_score >= 22:
            return "CONTROLLED_GAME"

        return "LOW_ACTIVITY_GAME"

    def _detect_dominance(self, match, attack_quality_score=0.0, possession_home=0.0, possession_away=0.0):
        home_stats = match.get("home_stats") or {}
        away_stats = match.get("away_stats") or {}

        home_pos = self._num(home_stats.get("possession")) or possession_home
        away_pos = self._num(away_stats.get("possession")) or possession_away

        home_threat = (
            self._num(home_stats.get("shots_on_target")) * 4.0
            + self._num(home_stats.get("shots_inside_box")) * 3.0
            + self._num(home_stats.get("blocked_shots")) * 1.5
            + self._num(home_stats.get("corners")) * 0.8
        )
        away_threat = (
            self._num(away_stats.get("shots_on_target")) * 4.0
            + self._num(away_stats.get("shots_inside_box")) * 3.0
            + self._num(away_stats.get("blocked_shots")) * 1.5
            + self._num(away_stats.get("corners")) * 0.8
        )

        if home_threat > away_threat + 6:
            return "HOME_THREAT_DOMINANT"

        if away_threat > home_threat + 6:
            return "AWAY_THREAT_DOMINANT"

        if home_pos > away_pos + 12 and home_threat >= away_threat:
            return "HOME_TERRITORIAL_DOMINANT"

        if away_pos > home_pos + 12 and away_threat >= home_threat:
            return "AWAY_TERRITORIAL_DOMINANT"

        return "BALANCED"

    def _goal_threat(
        self,
        sot,
        xg,
        da,
        shots_inside_box=0.0,
        blocked_shots=0.0,
        goalkeeper_saves=0.0,
        attack_quality_score=0.0,
    ):
        if attack_quality_score >= 58:
            return "HIGH"

        if sot >= 3 and (xg >= 0.8 or shots_inside_box >= 3):
            return "HIGH"

        if attack_quality_score >= 38 or (sot >= 2 and shots_inside_box >= 2):
            return "MEDIUM_HIGH"

        if sot >= 1 and (xg >= 0.45 or shots_inside_box >= 1 or goalkeeper_saves >= 1):
            return "MEDIUM"

        if da >= 5 or blocked_shots >= 3:
            return "MEDIUM_LOW"

        return "LOW"

    def _false_pressure_risk(
        self,
        shots,
        sot,
        da,
        shots_inside_box=0.0,
        shots_outside_box=0.0,
        blocked_shots=0.0,
        attack_quality_score=0.0,
        volume_score=0.0,
    ):
        if volume_score >= 55 and attack_quality_score < 25:
            return "HIGH"

        if shots >= 10 and sot == 0 and shots_inside_box <= 1:
            return "HIGH"

        if shots >= 8 and da == 0 and sot <= 1 and shots_inside_box <= 2:
            return "MEDIUM_HIGH"

        if shots_outside_box >= 5 and shots_inside_box <= 1 and sot <= 1:
            return "MEDIUM"

        return "LOW"

    def _final_reading(self, pressure_type, threat, false_risk, transition_risk_score=0.0):
        if transition_risk_score >= 50:
            return "RIESGO DE RUPTURA / TRANSICIÓN"

        if pressure_type == "REAL_PRESSURE" and threat in {"HIGH", "MEDIUM_HIGH"}:
            return "PRESIÓN REAL DE GOL"

        if pressure_type == "HIGH_THREAT_PRESSURE":
            return "AMENAZA OFENSIVA CON PROFUNDIDAD"

        if pressure_type == "MEDIUM_THREAT_PRESSURE":
            return "AMENAZA MEDIA EN VALIDACIÓN"

        if pressure_type == "FALSE_PRESSURE":
            return "PRESIÓN FALSA (SIN PELIGRO REAL)"

        if false_risk == "HIGH":
            return "DOMINIO SIN AMENAZA CLARA"

        if pressure_type == "LATERAL_PRESSURE":
            return "PRESIÓN LATERAL SIN PROFUNDIDAD"

        if pressure_type == "DOMINANCE_WITHOUT_DEPTH":
            return "DOMINIO TERRITORIAL SIN PROFUNDIDAD"

        return "PRESIÓN NEUTRAL"

    # -------------------------
    # UTILS
    # -------------------------

    def _num(self, value: Any) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(str(value).replace("%", "").strip())
        except Exception:
            return 0.0
