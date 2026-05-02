from __future__ import annotations

from typing import Any, Dict, List


class SignalDecisionAdvisor:
    """
    Juez final de señales.

    Importante:
    - No bloquea.
    - No elimina.
    - No cambia mercado.
    - No cambia rank.
    - Solo agrega lectura final para decidir mejor.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        market = str(signal.get("market") or "").upper()
        rank = str(signal.get("rank") or "").upper()
        market_status = str(signal.get("market_status") or "").upper()

        minute = self._safe_int(signal.get("current_minute") or signal.get("minute"))
        entry_minute = self._safe_int(signal.get("entry_minute") or signal.get("minute"))
        active_minutes = max(0, minute - entry_minute)

        score_text = str(signal.get("score") or signal.get("current_score") or "0-0")
        total_goals = self._total_goals(score_text)
        goal_diff = self._goal_diff(score_text)

        ai_score = self._safe_float(signal.get("ai_score"))
        signal_score = self._safe_float(signal.get("signal_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))

        shots = self._safe_float(signal.get("shots"))
        shots_on_target = self._safe_float(signal.get("shots_on_target"))
        corners = self._safe_float(signal.get("corners"))
        dangerous_attacks = self._safe_float(signal.get("dangerous_attacks"))
        xg = self._safe_float(signal.get("xg") or signal.get("xG"))

        line = signal.get("line")
        needed_goals = self._needed_goals_for_over(line=line, total_goals=total_goals)

        warnings: List[str] = []
        positives: List[str] = []

        decision_score = 50.0

        # -----------------------------
        # Fuerza base
        # -----------------------------
        if rank == "PREMIUM":
            decision_score += 14
            positives.append("Rango PREMIUM")
        elif rank == "FUERTE":
            decision_score += 10
            positives.append("Rango FUERTE")
        elif rank == "BUENA":
            decision_score += 6
            positives.append("Rango BUENA")
        elif rank == "OPERABLE":
            decision_score += 2
            warnings.append("Señal operable, no confirmada como fuerte")

        if signal_score >= 80:
            decision_score += 12
            positives.append("Signal Score alto")
        elif signal_score >= 70:
            decision_score += 7
            positives.append("Signal Score favorable")
        elif signal_score > 0 and signal_score < 65:
            decision_score -= 8
            warnings.append("Signal Score todavía moderado")

        if ai_score >= 80:
            decision_score += 10
            positives.append("IA muy favorable")
        elif ai_score >= 68:
            decision_score += 6
            positives.append("IA favorable")
        elif ai_score > 0 and ai_score < 60:
            decision_score -= 10
            warnings.append("IA insuficiente para entrada fuerte")

        # -----------------------------
        # Mercado OVER / UNDER
        # -----------------------------
        if market == "OVER":
            if goal_probability >= 75 and over_probability >= 72:
                decision_score += 12
                positives.append("Probabilidad OVER/GOL alineada")
            elif goal_probability >= 65 and over_probability >= 65:
                decision_score += 7
                positives.append("Probabilidad OVER aceptable")
            else:
                decision_score -= 10
                warnings.append("Probabilidad OVER/GOL no suficientemente alineada")

            if minute >= 85:
                decision_score -= 18
                warnings.append("OVER en minuto muy avanzado")
            elif minute >= 80:
                decision_score -= 12
                warnings.append("OVER en minuto avanzado")
            elif minute >= 75:
                decision_score -= 5
                warnings.append("Tramo final: vigilar timing")

            if active_minutes >= 23:
                decision_score -= 18
                warnings.append("Señal envejecida sin gol")
            elif active_minutes >= 16:
                decision_score -= 12
                warnings.append("Señal enfriándose")
            elif active_minutes >= 10:
                decision_score -= 5
                warnings.append("Señal lleva varios minutos activa")

            if goal_diff >= 3 and minute >= 60:
                decision_score -= 22
                warnings.append("Partido posiblemente resuelto por diferencia amplia")

            if needed_goals >= 2 and minute >= 70:
                decision_score -= 20
                warnings.append("Línea exigente: faltan dos o más goles")
            elif needed_goals == 1 and minute >= 80:
                decision_score -= 8
                warnings.append("Falta un gol, pero queda poco tiempo")

            if shots_on_target <= 1 and minute >= 65:
                decision_score -= 10
                warnings.append("Pocos tiros al arco para sostener OVER")

            if xg < 0.75 and minute >= 65:
                decision_score -= 10
                warnings.append("xG bajo para sostener alta probabilidad")

            if dangerous_attacks < 12 and minute >= 65:
                decision_score -= 8
                warnings.append("Ataques peligrosos bajos para OVER")

        elif market == "UNDER":
            if under_probability >= 68:
                decision_score += 12
                positives.append("UNDER bien alineado")
            elif under_probability >= 62:
                decision_score += 7
                positives.append("UNDER aceptable")
            else:
                decision_score -= 10
                warnings.append("UNDER no suficientemente alineado")

            if goal_probability >= 60:
                decision_score -= 16
                warnings.append("Amenaza de gol alta contra UNDER")

            if shots_on_target >= 4:
                decision_score -= 12
                warnings.append("Demasiados tiros al arco para UNDER")

            if dangerous_attacks >= 28:
                decision_score -= 10
                warnings.append("Presión ofensiva alta contra UNDER")

            if xg >= 1.4:
                decision_score -= 10
                warnings.append("xG alto contra UNDER")

            if minute < 55:
                decision_score -= 8
                warnings.append("UNDER demasiado temprano")

        else:
            decision_score -= 15
            warnings.append("Mercado no reconocido")

        # -----------------------------
        # Mercado real / interno
        # -----------------------------
        if market_status == "INTERNAL_ONLY":
            decision_score -= 8
            warnings.append("Señal interna sin mercado real validado")
        elif market_status == "PENDING":
            decision_score -= 6
            warnings.append("Mercado pendiente")

        # -----------------------------
        # Riesgo
        # -----------------------------
        if risk_score >= 7.5:
            decision_score -= 18
            warnings.append("Riesgo alto")
        elif risk_score >= 6.5:
            decision_score -= 10
            warnings.append("Riesgo medio-alto")
        elif 0 < risk_score <= 4.5:
            decision_score += 5
            positives.append("Riesgo controlado")

        # -----------------------------
        # Actividad positiva
        # -----------------------------
        if shots_on_target >= 3:
            decision_score += 7
            positives.append("Buen volumen de tiros al arco")

        if shots >= 8:
            decision_score += 4
            positives.append("Buen volumen de tiros")

        if corners >= 4:
            decision_score += 4
            positives.append("Corners favorables")

        if dangerous_attacks >= 25:
            decision_score += 6
            positives.append("Ataques peligrosos altos")

        if xg >= 1.25:
            decision_score += 7
            positives.append("xG competitivo")

        decision_score = round(max(0.0, min(decision_score, 100.0)), 2)

        decision_status = "ENTER_OK"
        decision_label = "ENTRADA VÁLIDA"
        decision_advice = "Señal fuerte, vigente y con condiciones aceptables."

        if decision_score < 75:
            decision_status = "WAIT_CONFIRMATION"
            decision_label = "ESPERAR CONFIRMACIÓN"
            decision_advice = "La señal existe, pero conviene esperar nueva confirmación."

        if decision_score < 60:
            decision_status = "NO_REENTRY"
            decision_label = "NO REENTRAR"
            decision_advice = "La señal perdió fuerza o tiene riesgo oculto."

        if decision_score < 45:
            decision_status = "AVOID"
            decision_label = "EVITAR"
            decision_advice = "Condiciones peligrosas para tomar esta señal."

        reason = self._build_reason(
            decision_status=decision_status,
            positives=positives,
            warnings=warnings,
        )

        return {
            "decision_status": decision_status,
            "decision_score": decision_score,
            "decision_label": decision_label,
            "decision_advice": decision_advice,
            "decision_reason": reason,
            "decision_warnings": warnings,
            "decision_positive_factors": positives,
            "decision_active_minutes": active_minutes,
            "decision_needed_goals": needed_goals,
            "decision_total_goals": total_goals,
            "decision_goal_diff": goal_diff,
        }

    def _build_reason(
        self,
        decision_status: str,
        positives: List[str],
        warnings: List[str],
    ) -> str:
        if decision_status == "ENTER_OK":
            if positives:
                return "Entrada válida: " + ", ".join(positives[:4])
            return "Entrada válida según lectura actual"

        if warnings:
            return "Aviso final: " + ", ".join(warnings[:4])

        return "Lectura final preventiva activa"

    def _needed_goals_for_over(self, line: Any, total_goals: int) -> int:
        line_value = self._safe_float(line)

        if line_value <= 0:
            return 1

        target_goals = int(line_value + 0.5)
        return max(0, target_goals - total_goals)

    def _total_goals(self, score: str) -> int:
        try:
            home, away = str(score).split("-", 1)
            return self._safe_int(home) + self._safe_int(away)
        except Exception:
            return 0

    def _goal_diff(self, score: str) -> int:
        try:
            home, away = str(score).split("-", 1)
            return abs(self._safe_int(home) - self._safe_int(away))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
