from __future__ import annotations

from typing import Any, Dict, List
from copy import deepcopy


class MatchScanEnhancer:
    """
    Ayudante liviano para ScanService.

    No bloquea.
    No publica señales.
    No cambia mercados.
    Solo agrega lectura extra al partido para que el sistema escanee mejor.
    """

    def enhance(self, match: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(match or {})

        minute = self._minute(data)
        score = self._score_text(data)
        total_goals = self._total_goals(score)
        goal_diff = self._goal_diff(score)

        shots = self._num(data.get("shots"))
        shots_on_target = self._num(data.get("shots_on_target"))
        corners = self._num(data.get("corners"))
        dangerous_attacks = self._num(data.get("dangerous_attacks"))
        xg = self._num(data.get("xg") or data.get("xG"))
        red_cards = self._num(data.get("red_cards"))

        is_late_game = bool(data.get("is_late_game")) or minute >= 75
        is_added_time = bool(data.get("is_added_time")) or minute >= 90
        elapsed_plus = self._num(data.get("elapsed_plus") or data.get("added_time"))
        tracking_only = bool(data.get("tracking_only", False))

        warnings: List[str] = []
        positives: List[str] = []

        over_boost = 0.0
        under_boost = 0.0
        scan_score = 50.0

        # Calidad de datos
        data_points = sum(
            1 for v in [shots, shots_on_target, corners, dangerous_attacks, xg]
            if v > 0
        )

        if data_points >= 3:
            scan_score += 8
            positives.append("Datos suficientes para lectura")
            data["scan_data_profile"] = "OK"
        elif data_points >= 1:
            scan_score += 2
            warnings.append("Datos parciales")
            data["scan_data_profile"] = "PARTIAL"
        else:
            scan_score -= 12
            warnings.append("Datos bajos o incompletos")
            data["scan_data_profile"] = "LOW_DATA"

        # Lectura OVER
        if shots_on_target >= 3:
            over_boost += 10
            scan_score += 6
            positives.append("Buen volumen de tiros al arco")

        if shots >= 8:
            over_boost += 5
            scan_score += 3
            positives.append("Volumen de tiros alto")

        if corners >= 4:
            over_boost += 4
            scan_score += 2
            positives.append("Corners favorables")

        if dangerous_attacks >= 25:
            over_boost += 8
            scan_score += 4
            positives.append("Ataques peligrosos altos")

        if xg >= 1.2:
            over_boost += 8
            scan_score += 5
            positives.append("xG competitivo")

        # Presión falsa
        fake_pressure_detected = False
        pressure_without_depth = False

        if shots >= 8 and shots_on_target <= 1:
            fake_pressure_detected = True
            scan_score -= 8
            warnings.append("Posible presión falsa: muchos tiros sin precisión")

        if dangerous_attacks >= 25 and shots_on_target <= 1:
            pressure_without_depth = True
            scan_score -= 8
            warnings.append("Ataques peligrosos sin finalización clara")

        # Partido muerto / goleada
        if goal_diff >= 3 and minute >= 60:
            scan_score -= 18
            over_boost -= 12
            under_boost += 8
            warnings.append("Partido posiblemente resuelto por diferencia amplia")

        # Timing: ya no castiga automático el 80+; ahora exige lectura viva
        late_reactivation = self._late_reactivation(
            minute=minute,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            red_cards=red_cards,
        )

        chaos_mode = self._chaos_mode(
            minute=minute,
            total_goals=total_goals,
            goal_diff=goal_diff,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            red_cards=red_cards,
        )

        retention_shape = self._retention_shape(
            minute=minute,
            total_goals=total_goals,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            goal_diff=goal_diff,
        )

        if 20 <= minute <= 70:
            scan_score += 5
            positives.append("Ventana temporal útil")

        elif 71 <= minute <= 84:
            if late_reactivation or chaos_mode:
                scan_score += 4
                over_boost += 5
                positives.append("Tramo final con señales de reactivación")
            elif retention_shape:
                under_boost += 7
                warnings.append("Tramo final con posible retención de marcador")
            else:
                scan_score -= 3
                warnings.append("Tramo final: requiere confirmación")

        elif minute >= 85:
            if late_reactivation or chaos_mode:
                scan_score += 3
                over_boost += 6
                positives.append("Minuto avanzado con actividad ofensiva viva")
            elif retention_shape:
                scan_score -= 4
                under_boost += 10
                warnings.append("Minuto avanzado con perfil de retención")
            else:
                scan_score -= 7
                over_boost -= 4
                warnings.append("Minuto avanzado sin confirmación ofensiva clara")

        if is_added_time:
            if late_reactivation or chaos_mode:
                scan_score += 2
                positives.append("Añadido con señales de peligro")
            else:
                scan_score -= 4
                warnings.append("Añadido sin presión suficiente")

        if tracking_only:
            warnings.append("Partido en modo seguimiento; no debe apagarse la lectura")

        # Perfil UNDER
        if minute >= 55:
            if shots_on_target <= 1 and xg <= 0.7 and dangerous_attacks <= 14:
                under_boost += 14
                scan_score += 5
                positives.append("Perfil frío/controlado favorable para UNDER")

            if total_goals <= 1 and shots_on_target <= 2 and corners <= 3:
                under_boost += 8
                positives.append("Partido bajo en producción ofensiva")

        if shots_on_target >= 5 or xg >= 1.6 or dangerous_attacks >= 35:
            under_boost -= 12
            warnings.append("Amenaza ofensiva alta contra UNDER")

        if red_cards > 0:
            scan_score -= 5
            warnings.append("Tarjeta roja detectada: dinámica inestable")

        field_vision = self._field_vision(
            minute=minute,
            scan_score=scan_score,
            over_boost=over_boost,
            under_boost=under_boost,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            goal_diff=goal_diff,
            total_goals=total_goals,
            is_late_game=is_late_game,
            is_added_time=is_added_time,
            elapsed_plus=elapsed_plus,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
        )

        scan_score = round(max(0.0, min(scan_score, 100.0)), 2)

        data["scan_enhanced"] = True
        data["scan_score"] = scan_score
        data["scan_profile"] = self._profile(
            minute=minute,
            scan_score=scan_score,
            over_boost=over_boost,
            under_boost=under_boost,
            goal_diff=goal_diff,
            warnings=warnings,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            retention_shape=retention_shape,
        )
        data["scan_recommendation"] = self._recommendation(
            scan_score=scan_score,
            warnings=warnings,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            retention_shape=retention_shape,
        )
        data["scan_positive_factors"] = positives
        data["scan_warnings"] = warnings
        data["scan_over_boost"] = round(over_boost, 2)
        data["scan_under_boost"] = round(under_boost, 2)
        data["scan_total_goals"] = total_goals
        data["scan_goal_diff"] = goal_diff

        data["late_reactivation"] = late_reactivation
        data["chaos_mode"] = chaos_mode
        data["fake_pressure_detected"] = fake_pressure_detected
        data["pressure_without_depth"] = pressure_without_depth
        data["retention_shape"] = retention_shape

        data.update(field_vision)

        return data

    def _field_vision(
        self,
        minute: int,
        scan_score: float,
        over_boost: float,
        under_boost: float,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        goal_diff: int,
        total_goals: int,
        is_late_game: bool,
        is_added_time: bool,
        elapsed_plus: float,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
    ) -> Dict[str, Any]:
        vision_score = 50.0
        phase = "NORMAL"
        status = "NEUTRAL"
        summary = "Lectura de campo estable sin señal fuerte."

        if minute < 15:
            phase = "EARLY"
            vision_score -= 8
        elif minute <= 45:
            phase = "FIRST_HALF"
        elif minute <= 60:
            phase = "RESTART_PHASE"
        elif minute <= 74:
            phase = "TACTICAL_PHASE"
        elif minute <= 89:
            phase = "LATE_GAME"
        else:
            phase = "ADDED_TIME"

        if is_late_game:
            vision_score -= 3

        if is_added_time:
            vision_score -= 5

        if late_reactivation:
            vision_score += 18
            status = "REACTIVATION"
            summary = "El partido muestra reactivación ofensiva; no asumir que está muerto."

        if chaos_mode:
            vision_score += 20
            status = "CHAOS"
            summary = "Partido en modo caos: alta volatilidad y posible ruptura del marcador."

        if fake_pressure_detected:
            vision_score -= 12
            status = "FAKE_PRESSURE"
            summary = "Hay volumen ofensivo, pero la presión parece poco profunda o imprecisa."

        if pressure_without_depth:
            vision_score -= 10
            if status == "NEUTRAL":
                status = "PRESSURE_WITHOUT_DEPTH"
                summary = "Hay ataques o acercamientos, pero falta finalización real."

        if retention_shape:
            vision_score -= 6
            if status in {"NEUTRAL", "FAKE_PRESSURE", "PRESSURE_WITHOUT_DEPTH"}:
                status = "RETENTION"
                summary = "El partido muestra forma de retención o marcador congelado."

        if shots_on_target >= 4:
            vision_score += 8

        if dangerous_attacks >= 28 and shots_on_target >= 2:
            vision_score += 7

        if xg >= 1.25:
            vision_score += 7

        if corners >= 5 and shots_on_target >= 2:
            vision_score += 4

        if goal_diff >= 3 and minute >= 60:
            vision_score -= 18
            status = "RESOLVED_RISK"
            summary = "El marcador amplio puede reducir intención ofensiva real."

        if total_goals >= 4 and minute >= 65:
            vision_score -= 6

        if over_boost >= 14 and over_boost > under_boost and status == "NEUTRAL":
            status = "OVER_PRESSURE"
            summary = "La lectura de campo favorece presión ofensiva para posible gol."

        if under_boost >= 12 and under_boost > over_boost and status == "NEUTRAL":
            status = "UNDER_CONTROL"
            summary = "La lectura de campo favorece control y posible retención."

        vision_score = round(max(0.0, min(vision_score, 100.0)), 2)

        return {
            "field_vision_status": status,
            "field_vision_score": vision_score,
            "field_vision_phase": phase,
            "field_vision_summary": summary,
            "field_vision_is_late_game": is_late_game,
            "field_vision_is_added_time": is_added_time,
            "field_vision_added_minutes": elapsed_plus,
        }

    def _late_reactivation(
        self,
        minute: int,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        red_cards: float,
    ) -> bool:
        if minute < 70:
            return False

        return bool(
            shots_on_target >= 3
            or xg >= 1.2
            or (dangerous_attacks >= 24 and corners >= 4)
            or (red_cards > 0 and dangerous_attacks >= 18)
        )

    def _chaos_mode(
        self,
        minute: int,
        total_goals: int,
        goal_diff: int,
        shots_on_target: float,
        dangerous_attacks: float,
        corners: float,
        red_cards: float,
    ) -> bool:
        if minute < 55:
            return False

        if red_cards > 0 and dangerous_attacks >= 18:
            return True

        if total_goals >= 3 and goal_diff <= 1 and shots_on_target >= 3:
            return True

        if minute >= 75 and shots_on_target >= 4 and dangerous_attacks >= 24:
            return True

        if minute >= 75 and corners >= 6 and dangerous_attacks >= 28:
            return True

        return False

    def _retention_shape(
        self,
        minute: int,
        total_goals: int,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        goal_diff: int,
    ) -> bool:
        if minute < 55:
            return False

        if shots_on_target <= 1 and corners <= 3 and dangerous_attacks <= 14 and xg <= 0.7:
            return True

        if minute >= 70 and goal_diff >= 1 and shots_on_target <= 2 and dangerous_attacks <= 18:
            return True

        if minute >= 75 and total_goals <= 1 and shots_on_target <= 2 and xg <= 0.9:
            return True

        return False

    def _profile(
        self,
        minute: int,
        scan_score: float,
        over_boost: float,
        under_boost: float,
        goal_diff: int,
        warnings: List[str],
        late_reactivation: bool,
        chaos_mode: bool,
        retention_shape: bool,
    ) -> str:
        warning_text = " ".join(str(w) for w in warnings if w).upper()

        if chaos_mode:
            return "CHAOS_GAME"

        if late_reactivation:
            return "LATE_REACTIVATION"

        if retention_shape and under_boost >= over_boost:
            return "RETENTION_SHAPE"

        if goal_diff >= 3 and minute >= 60:
            return "DEAD_GAME_RISK"

        if "PRESIÓN FALSA" in warning_text or "SIN FINALIZACIÓN" in warning_text:
            return "FALSE_PRESSURE"

        if minute >= 78 and not late_reactivation and not chaos_mode:
            return "LATE_CONFIRMATION_REQUIRED"

        if under_boost >= 12 and under_boost > over_boost:
            return "UNDER_SHAPE"

        if over_boost >= 14 and scan_score >= 65:
            return "HOT_OVER"

        if scan_score < 45:
            return "CAUTION"

        return "NEUTRAL"

    def _recommendation(
        self,
        scan_score: float,
        warnings: List[str],
        late_reactivation: bool,
        chaos_mode: bool,
        retention_shape: bool,
    ) -> str:
        warning_text = " ".join(str(w) for w in warnings if w).upper()

        if chaos_mode:
            return "PRIORITIZE_CAUTION"

        if late_reactivation and scan_score >= 55:
            return "OBSERVE_ACTIVE"

        if retention_shape:
            return "OBSERVE_RETENTION"

        if "PARTIDO POSIBLEMENTE RESUELTO" in warning_text:
            return "CAUTION"

        if "MINUTO AVANZADO SIN CONFIRMACIÓN" in warning_text:
            return "CAUTION"

        if scan_score >= 70:
            return "PRIORITIZE"

        if scan_score >= 55:
            return "OBSERVE"

        return "CAUTION"

    def _score_text(self, item: Dict[str, Any]) -> str:
        score = item.get("score") or item.get("marcador")
        if score:
            return str(score)

        home = self._num(
            item.get("home_score")
            or item.get("local_score")
            or item.get("marcador_local")
        )
        away = self._num(
            item.get("away_score")
            or item.get("visitante_score")
            or item.get("marcador_visitante")
        )

        return f"{int(home)}-{int(away)}"

    def _total_goals(self, score: str) -> int:
        try:
            parts = str(score).replace(":", "-").split("-", 1)

            if len(parts) != 2:
                return 0

            home, away = parts
            return int(float(home or 0)) + int(float(away or 0))
        except Exception:
            return 0

    def _goal_diff(self, score: str) -> int:
        try:
            parts = str(score).replace(":", "-").split("-", 1)

            if len(parts) != 2:
                return 0

            home, away = parts
            return abs(int(float(home or 0)) - int(float(away or 0)))
        except Exception:
            return 0

    def _minute(self, item: Dict[str, Any]) -> int:
        return int(
            self._num(
                item.get("minute")
                or item.get("minuto")
                or item.get("current_minute")
                or item.get("match_minute")
                or 0
            )
        )

    def _num(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
