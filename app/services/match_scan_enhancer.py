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
        if shots >= 8 and shots_on_target <= 1:
            scan_score -= 8
            warnings.append("Posible presión falsa: muchos tiros sin precisión")

        if dangerous_attacks >= 25 and shots_on_target <= 1:
            scan_score -= 8
            warnings.append("Ataques peligrosos sin finalización clara")

        # Partido muerto / goleada
        if goal_diff >= 3 and minute >= 60:
            scan_score -= 18
            over_boost -= 12
            warnings.append("Partido posiblemente resuelto por diferencia amplia")

        # Timing OVER
        if minute >= 85:
            scan_score -= 14
            over_boost -= 10
            warnings.append("Minuto muy avanzado")
        elif minute >= 78:
            scan_score -= 8
            over_boost -= 5
            warnings.append("Tramo final con riesgo de entrada tardía")
        elif 20 <= minute <= 70:
            scan_score += 5
            positives.append("Ventana temporal útil")

        # Perfil UNDER
        if minute >= 55:
            if shots_on_target <= 1 and xg <= 0.7 and dangerous_attacks <= 14:
                under_boost += 14
                scan_score += 5
                positives.append("Perfil frío/controlado favorable para UNDER")

            if total_goals <= 1 and shots_on_target <= 2 and corners <= 3:
                under_boost += 8
                positives.append("Partido bajo en producción ofensiva")

        if shots_on_target >= 4 or xg >= 1.4 or dangerous_attacks >= 30:
            under_boost -= 12
            warnings.append("Amenaza ofensiva alta contra UNDER")

        if red_cards > 0:
            scan_score -= 5
            warnings.append("Tarjeta roja detectada: dinámica inestable")

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
        )
        data["scan_recommendation"] = self._recommendation(scan_score, warnings)
        data["scan_positive_factors"] = positives
        data["scan_warnings"] = warnings
        data["scan_over_boost"] = round(over_boost, 2)
        data["scan_under_boost"] = round(under_boost, 2)
        data["scan_total_goals"] = total_goals
        data["scan_goal_diff"] = goal_diff

        return data

    def _profile(
        self,
        minute: int,
        scan_score: float,
        over_boost: float,
        under_boost: float,
        goal_diff: int,
        warnings: List[str],
    ) -> str:
        warning_text = " ".join(warnings).upper()

        if goal_diff >= 3 and minute >= 60:
            return "DEAD_GAME_RISK"

        if "PRESIÓN FALSA" in warning_text or "SIN FINALIZACIÓN" in warning_text:
            return "FALSE_PRESSURE"

        if minute >= 78:
            return "LATE_RISK"

        if under_boost >= 12 and under_boost > over_boost:
            return "UNDER_SHAPE"

        if over_boost >= 14 and scan_score >= 65:
            return "HOT_OVER"

        if scan_score < 45:
            return "CAUTION"

        return "NEUTRAL"

    def _recommendation(self, scan_score: float, warnings: List[str]) -> str:
        warning_text = " ".join(warnings).upper()

        if "PARTIDO POSIBLEMENTE RESUELTO" in warning_text:
            return "CAUTION"

        if "MINUTO MUY AVANZADO" in warning_text:
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
            home, away = str(score).split("-", 1)
            return int(float(home or 0)) + int(float(away or 0))
        except Exception:
            return 0

    def _goal_diff(self, score: str) -> int:
        try:
            home, away = str(score).split("-", 1)
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
