from typing import Any, Dict


class MatchAnalystEngine:
    """
    Motor analista central.

    Objetivo:
    - interpretar el partido como una historia viva
    - distinguir presión real vs presión falsa
    - detectar intención competitiva
    - clasificar si el contexto favorece OVER, UNDER o espera
    """

    @staticmethod
    def analyze(match: Dict[str, Any], tactica: Dict[str, Any], predictor: Dict[str, Any]) -> Dict[str, Any]:
        minute = MatchAnalystEngine._to_int(match.get("minute", 0))
        score = str(match.get("score", "0-0") or "0-0")

        shots = MatchAnalystEngine._to_float(match.get("shots", 0))
        shots_on_target = MatchAnalystEngine._to_float(match.get("shots_on_target", 0))
        dangerous_attacks = MatchAnalystEngine._to_float(match.get("dangerous_attacks", 0))
        corners = MatchAnalystEngine._to_float(match.get("corners", 0))
        total_xg = MatchAnalystEngine._to_float(match.get("xG", 0))
        red_cards = MatchAnalystEngine._to_int(match.get("red_cards", 0))

        match_state = str(tactica.get("match_state", "CONTROLADO") or "CONTROLADO").upper()
        intensity_score = MatchAnalystEngine._to_float(tactica.get("intensity_score", 0))
        gol_inminente = bool(predictor.get("gol_inminente", False))
        confianza_ventana = MatchAnalystEngine._to_float(predictor.get("confianza_ventana", 0))
        ventana_minutos = MatchAnalystEngine._to_int(predictor.get("ventana_minutos", 0))

        total_goals = MatchAnalystEngine._parse_total_goals(score)

        tempo_state = MatchAnalystEngine._build_tempo_state(
            minute=minute,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            intensity_score=intensity_score,
        )

        pressure_truth = MatchAnalystEngine._build_pressure_truth(
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            total_xg=total_xg,
            corners=corners,
            gol_inminente=gol_inminente,
        )

        intent_state = MatchAnalystEngine._build_intent_state(
            minute=minute,
            score=score,
            total_goals=total_goals,
            match_state=match_state,
            dangerous_attacks=dangerous_attacks,
            shots_on_target=shots_on_target,
        )

        emotional_state = MatchAnalystEngine._build_emotional_state(
            minute=minute,
            total_goals=total_goals,
            red_cards=red_cards,
            match_state=match_state,
            gol_inminente=gol_inminente,
        )

        game_story = MatchAnalystEngine._build_game_story(
            minute=minute,
            total_goals=total_goals,
            match_state=match_state,
            pressure_truth=pressure_truth,
            tempo_state=tempo_state,
            shots_on_target=shots_on_target,
            total_xg=total_xg,
        )

        threat_state = MatchAnalystEngine._build_threat_state(
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            total_xg=total_xg,
            gol_inminente=gol_inminente,
            match_state=match_state,
        )

        analyst_state, analyst_confidence, analyst_reason = MatchAnalystEngine._build_master_read(
            minute=minute,
            total_goals=total_goals,
            score=score,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            total_xg=total_xg,
            match_state=match_state,
            tempo_state=tempo_state,
            pressure_truth=pressure_truth,
            intent_state=intent_state,
            emotional_state=emotional_state,
            game_story=game_story,
            threat_state=threat_state,
            gol_inminente=gol_inminente,
            confianza_ventana=confianza_ventana,
        )

        return {
            "analyst_state": analyst_state,
            "analyst_confidence": analyst_confidence,
            "analyst_reason": analyst_reason,
            "tempo_state": tempo_state,
            "pressure_truth": pressure_truth,
            "intent_state": intent_state,
            "emotional_state": emotional_state,
            "game_story": game_story,
            "threat_state": threat_state,
            "ventana_minutos": ventana_minutos,
            "gol_inminente": gol_inminente,
            "match_state": match_state,
            "intensity_score": round(intensity_score, 2),
        }

    # =========================================================
    # LECTURAS DEL ANALISTA
    # =========================================================

    @staticmethod
    def _build_tempo_state(
        minute: int,
        shots: float,
        shots_on_target: float,
        dangerous_attacks: float,
        corners: float,
        intensity_score: float,
    ) -> str:
        if minute <= 0:
            minute = 1

        shots_rate = shots / minute
        sot_rate = shots_on_target / minute
        danger_rate = dangerous_attacks / minute
        corner_rate = corners / minute

        tempo_score = 0.0
        tempo_score += shots_rate * 60
        tempo_score += sot_rate * 120
        tempo_score += danger_rate * 40
        tempo_score += corner_rate * 25
        tempo_score += intensity_score * 0.25

        if tempo_score >= 40:
            return "ALTISIMO"
        if tempo_score >= 28:
            return "ALTO"
        if tempo_score >= 16:
            return "MEDIO"
        if tempo_score >= 8:
            return "BAJO"
        return "MUY_BAJO"

    @staticmethod
    def _build_pressure_truth(
        shots_on_target: float,
        dangerous_attacks: float,
        total_xg: float,
        corners: float,
        gol_inminente: bool,
    ) -> str:
        if gol_inminente and (shots_on_target >= 2 or total_xg >= 0.7):
            return "ASFIXIANTE"

        if (
            shots_on_target >= 2
            and dangerous_attacks >= 12
            and total_xg >= 0.65
        ):
            return "REAL"

        if (
            dangerous_attacks >= 10
            and (shots_on_target >= 1 or corners >= 3 or total_xg >= 0.45)
        ):
            return "MODERADA"

        if dangerous_attacks >= 8 and shots_on_target == 0 and total_xg < 0.35:
            return "FALSA"

        if dangerous_attacks >= 5:
            return "LEVE"

        return "NULA"

    @staticmethod
    def _build_intent_state(
        minute: int,
        score: str,
        total_goals: int,
        match_state: str,
        dangerous_attacks: float,
        shots_on_target: float,
    ) -> str:
        home_goals, away_goals = MatchAnalystEngine._parse_score(score)
        diff = abs(home_goals - away_goals)

        if diff == 0 and minute >= 55 and (dangerous_attacks >= 10 or shots_on_target >= 2):
            return "AMBOS_BUSCAN"

        if diff == 1 and minute >= 65 and match_state in ["CONTROLADO", "MUERTO", "TIBIO"]:
            return "UNO_PROTEGE_RESULTADO"

        if total_goals == 0 and minute >= 25 and match_state in ["ACTIVO", "CALIENTE", "ABIERTO", "EXPLOSIVO"]:
            return "BUSQUEDA_DE_APERTURA"

        if total_goals >= 2 and match_state in ["EXPLOSIVO", "CALIENTE", "ABIERTO"]:
            return "INTERCAMBIO_ABIERTO"

        if match_state in ["CONTROLADO", "MUERTO"]:
            return "SIN_INTENCION_CLARA"

        return "LECTURA_NEUTRAL"

    @staticmethod
    def _build_emotional_state(
        minute: int,
        total_goals: int,
        red_cards: int,
        match_state: str,
        gol_inminente: bool,
    ) -> str:
        if red_cards >= 2:
            return "CAOS_DISTORSIONADO"

        if red_cards == 1:
            return "PARTIDO_ALTERADO"

        if gol_inminente and match_state in ["CALIENTE", "EXPLOSIVO"]:
            return "MAXIMA_TENSION"

        if total_goals >= 3 and minute >= 60:
            return "PARTIDO_ROTO"

        if match_state in ["MUERTO", "CONTROLADO"]:
            return "ESTABILIDAD"

        return "COMPETITIVO"

    @staticmethod
    def _build_game_story(
        minute: int,
        total_goals: int,
        match_state: str,
        pressure_truth: str,
        tempo_state: str,
        shots_on_target: float,
        total_xg: float,
    ) -> str:
        if match_state in ["EXPLOSIVO", "CALIENTE"] and pressure_truth in ["REAL", "ASFIXIANTE"]:
            return "PARTIDO_EN_ASCENSO"

        if match_state == "ABIERTO" and total_goals >= 1:
            return "PARTIDO_ABIERTO"

        if match_state in ["CONTROLADO", "MUERTO"] and minute >= 60:
            return "PARTIDO_CERRADO_MADURO"

        if tempo_state in ["BAJO", "MUY_BAJO"] and shots_on_target == 0 and total_xg < 0.35:
            return "PARTIDO_APAGADO"

        if minute < 20:
            return "PARTIDO_EN_LECTURA"

        return "PARTIDO_VARIABLE"

    @staticmethod
    def _build_threat_state(
        shots_on_target: float,
        dangerous_attacks: float,
        total_xg: float,
        gol_inminente: bool,
        match_state: str,
    ) -> str:
        if gol_inminente:
            return "CRITICA"

        if (
            match_state in ["EXPLOSIVO", "CALIENTE"]
            and shots_on_target >= 2
            and total_xg >= 0.65
        ):
            return "ALTA"

        if shots_on_target >= 1 and dangerous_attacks >= 8:
            return "MEDIA"

        if dangerous_attacks >= 5 or total_xg >= 0.25:
            return "BAJA"

        return "MINIMA"

    # =========================================================
    # DECISIÓN MAESTRA
    # =========================================================

    @staticmethod
    def _build_master_read(
        minute: int,
        total_goals: int,
        score: str,
        shots: float,
        shots_on_target: float,
        dangerous_attacks: float,
        corners: float,
        total_xg: float,
        match_state: str,
        tempo_state: str,
        pressure_truth: str,
        intent_state: str,
        emotional_state: str,
        game_story: str,
        threat_state: str,
        gol_inminente: bool,
        confianza_ventana: float,
    ) -> tuple[str, float, str]:
        # =========================
        # OVER FAVORABLE
        # =========================
        over_score = 0.0

        if match_state == "EXPLOSIVO":
            over_score += 18
        elif match_state == "CALIENTE":
            over_score += 14
        elif match_state == "ABIERTO":
            over_score += 10
        elif match_state == "ACTIVO":
            over_score += 7

        if tempo_state == "ALTISIMO":
            over_score += 14
        elif tempo_state == "ALTO":
            over_score += 10
        elif tempo_state == "MEDIO":
            over_score += 5

        if pressure_truth == "ASFIXIANTE":
            over_score += 16
        elif pressure_truth == "REAL":
            over_score += 12
        elif pressure_truth == "MODERADA":
            over_score += 6

        if threat_state == "CRITICA":
            over_score += 14
        elif threat_state == "ALTA":
            over_score += 10
        elif threat_state == "MEDIA":
            over_score += 5

        if gol_inminente:
            over_score += 16

        if confianza_ventana >= 70:
            over_score += 8
        elif confianza_ventana >= 55:
            over_score += 4

        if shots_on_target >= 3:
            over_score += 8
        elif shots_on_target >= 2:
            over_score += 5
        elif shots_on_target >= 1:
            over_score += 2

        if dangerous_attacks >= 15:
            over_score += 8
        elif dangerous_attacks >= 10:
            over_score += 5
        elif dangerous_attacks >= 6:
            over_score += 2

        if total_xg >= 1.2:
            over_score += 8
        elif total_xg >= 0.8:
            over_score += 5
        elif total_xg >= 0.45:
            over_score += 2

        if 25 <= minute <= 45:
            over_score += 5
        if 55 <= minute <= 75:
            over_score += 7
        if 76 <= minute <= 85:
            over_score += 3

        # =========================
        # UNDER FAVORABLE
        # =========================
        under_score = 0.0

        if match_state == "MUERTO":
            under_score += 20
        elif match_state == "CONTROLADO":
            under_score += 14
        elif match_state == "TIBIO":
            under_score += 8
        elif match_state in ["EXPLOSIVO", "CALIENTE", "ABIERTO"]:
            under_score -= 14

        if tempo_state == "MUY_BAJO":
            under_score += 14
        elif tempo_state == "BAJO":
            under_score += 10
        elif tempo_state == "MEDIO":
            under_score += 4
        elif tempo_state in ["ALTO", "ALTISIMO"]:
            under_score -= 8

        if pressure_truth == "NULA":
            under_score += 14
        elif pressure_truth == "LEVE":
            under_score += 8
        elif pressure_truth == "FALSA":
            under_score += 10
        elif pressure_truth in ["REAL", "ASFIXIANTE"]:
            under_score -= 12

        if threat_state == "MINIMA":
            under_score += 12
        elif threat_state == "BAJA":
            under_score += 6
        elif threat_state in ["ALTA", "CRITICA"]:
            under_score -= 12

        if not gol_inminente:
            under_score += 8
        else:
            under_score -= 14

        if shots_on_target == 0:
            under_score += 12
        elif shots_on_target <= 1:
            under_score += 6
        else:
            under_score -= 8

        if dangerous_attacks <= 6:
            under_score += 10
        elif dangerous_attacks <= 10:
            under_score += 5
        else:
            under_score -= 8

        if total_xg <= 0.35:
            under_score += 12
        elif total_xg <= 0.65:
            under_score += 6
        elif total_xg >= 1.0:
            under_score -= 10

        if corners <= 2:
            under_score += 4

        if minute >= 55:
            under_score += 8
        if minute >= 65:
            under_score += 6
        if minute >= 75:
            under_score += 4

        if total_goals >= 3:
            under_score -= 12

        # =========================
        # DECISIÓN FINAL
        # =========================
        over_score = round(max(min(over_score, 95), 0), 1)
        under_score = round(max(min(under_score, 95), 0), 1)

        if over_score >= 70 and over_score > under_score:
            reason = (
                f"Ritmo {tempo_state}, presión {pressure_truth}, amenaza {threat_state}, "
                f"estado {match_state}, contexto {game_story}"
            )
            return "OVER_FAVORABLE", over_score, reason

        if under_score >= 74 and under_score > over_score:
            reason = (
                f"Ritmo {tempo_state}, presión {pressure_truth}, amenaza {threat_state}, "
                f"estado {match_state}, contexto {game_story}"
            )
            return "UNDER_FAVORABLE", under_score, reason

        if max(over_score, under_score) >= 55:
            if over_score >= under_score:
                reason = (
                    f"Lectura parcial OVER | ritmo {tempo_state} | presión {pressure_truth} | "
                    f"estado {match_state}"
                )
                return "OBSERVE_OVER", over_score, reason

            reason = (
                f"Lectura parcial UNDER | ritmo {tempo_state} | presión {pressure_truth} | "
                f"estado {match_state}"
            )
            return "OBSERVE_UNDER", under_score, reason

        return (
            "NO_CLEAR_EDGE",
            round(max(over_score, under_score), 1),
            f"Sin ventaja clara | ritmo {tempo_state} | presión {pressure_truth} | estado {match_state}"
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _parse_score(score: str) -> tuple[int, int]:
        try:
            home, away = score.split("-", 1)
            return int(home.strip()), int(away.strip())
        except Exception:
            return 0, 0

    @staticmethod
    def _parse_total_goals(score: str) -> int:
        home, away = MatchAnalystEngine._parse_score(score)
        return home + away

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default
