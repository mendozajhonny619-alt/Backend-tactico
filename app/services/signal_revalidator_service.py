from __future__ import annotations

from typing import Any, Dict, List


class SignalRevalidatorService:
    """
    Revalida señales activas.

    Objetivo:
    - No bloquea señales.
    - No elimina señales.
    - No cambia mercado ni rank.
    - Solo indica si la señal sigue fuerte, se debilita o se enfría.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        market = str(signal.get("market") or "").upper()

        current_minute = self._safe_int(
            signal.get("current_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        entry_minute = self._safe_int(
            signal.get("entry_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        active_minutes = max(0, current_minute - entry_minute)

        signal_score = self._safe_float(signal.get("signal_score"))
        ai_score = self._safe_float(signal.get("ai_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))

        shots = self._safe_float(signal.get("shots"))
        shots_on_target = self._safe_float(signal.get("shots_on_target"))
        corners = self._safe_float(signal.get("corners"))
        dangerous_attacks = self._safe_float(signal.get("dangerous_attacks"))
        xg = self._safe_float(signal.get("xg") or signal.get("xG"))

        score = 50.0
        reasons: List[str] = []
        warnings: List[str] = []

        # -----------------------------
        # Base por fuerza original
        # -----------------------------
        if signal_score >= 75:
            score += 12
            reasons.append("Signal Score alto")
        elif signal_score >= 65:
            score += 7
            reasons.append("Signal Score aceptable")
        elif signal_score > 0 and signal_score < 55:
            score -= 8
            warnings.append("Signal Score bajo")

        if ai_score >= 70:
            score += 10
            reasons.append("IA favorable")
        elif ai_score >= 60:
            score += 5
            reasons.append("IA operable")
        elif ai_score > 0 and ai_score < 55:
            score -= 8
            warnings.append("IA débil")

        # -----------------------------
        # Mercado
        # -----------------------------
        if market == "OVER":
            if goal_probability >= 75:
                score += 10
                reasons.append("Probabilidad de gol alta")
            elif goal_probability >= 65:
                score += 6
                reasons.append("Probabilidad de gol favorable")
            elif goal_probability > 0 and goal_probability < 58:
                score -= 10
                warnings.append("Probabilidad de gol insuficiente")

            if over_probability >= 75:
                score += 9
                reasons.append("OVER muy alineado")
            elif over_probability >= 65:
                score += 5
                reasons.append("OVER alineado")
            elif over_probability > 0 and over_probability < 58:
                score -= 9
                warnings.append("OVER perdiendo fuerza")

        elif market == "UNDER":
            if under_probability >= 72:
                score += 10
                reasons.append("UNDER muy alineado")
            elif under_probability >= 64:
                score += 5
                reasons.append("UNDER alineado")
            elif under_probability > 0 and under_probability < 58:
                score -= 9
                warnings.append("UNDER perdiendo fuerza")

            if goal_probability >= 60:
                score -= 12
                warnings.append("Amenaza de gol elevada contra UNDER")

        # -----------------------------
        # Actividad real
        # -----------------------------
        if shots_on_target >= 3:
            score += 8
            reasons.append("Buen volumen de tiros al arco")
        elif market == "OVER" and current_minute >= 65 and shots_on_target <= 1:
            score -= 10
            warnings.append("Pocos tiros al arco para sostener OVER")

        if shots >= 8:
            score += 4
            reasons.append("Volumen de tiros aceptable")

        if corners >= 4:
            score += 4
            reasons.append("Corners favorables")

        if dangerous_attacks >= 25:
            score += 7
            reasons.append("Ataques peligrosos altos")
        elif market == "OVER" and current_minute >= 65 and dangerous_attacks < 12:
            score -= 8
            warnings.append("Ataques peligrosos bajos para OVER")

        if xg >= 1.3:
            score += 8
            reasons.append("xG competitivo")
        elif market == "OVER" and current_minute >= 65 and xg < 0.7:
            score -= 10
            warnings.append("xG bajo para sostener alta probabilidad")

        # -----------------------------
        # Edad de la señal
        # -----------------------------
        if active_minutes <= 8:
            age_label = "FRESCA"
            score += 6
            reasons.append("Señal fresca")
        elif active_minutes <= 15:
            age_label = "VIGENTE"
            score += 1
            reasons.append("Señal todavía vigente")
        elif active_minutes <= 22:
            age_label = "ENFRIANDO"
            score -= 10
            warnings.append("Señal activa por varios minutos sin cumplirse")
        else:
            age_label = "ENFRIADA"
            score -= 18
            warnings.append("Señal envejecida sin confirmación")

        # -----------------------------
        # Minuto avanzado
        # -----------------------------
        if market == "OVER":
            if current_minute >= 85:
                score -= 16
                warnings.append("Minuto muy avanzado para OVER")
            elif current_minute >= 80:
                score -= 10
                warnings.append("Minuto avanzado para OVER")
            elif current_minute >= 75:
                score -= 4
                warnings.append("Tramo final: vigilar timing")

        if risk_score >= 7.5:
            score -= 15
            warnings.append("Riesgo alto")
        elif risk_score >= 6.5:
            score -= 8
            warnings.append("Riesgo medio-alto")

        score = round(max(0.0, min(score, 100.0)), 2)

        status = "STRONG"
        advice = "SEÑAL TODAVÍA FUERTE"

        if score < 75:
            status = "WEAKENING"
            advice = "SEÑAL VÁLIDA, PERO PERDIENDO FUERZA"

        if score < 60 or age_label in {"ENFRIANDO", "ENFRIADA"}:
            status = "COOLING"
            advice = "SEÑAL ENFRIADA: NO REENTRAR SIN NUEVA CONFIRMACIÓN"

        if score < 45 or (market == "OVER" and current_minute >= 85 and active_minutes >= 12):
            status = "HIGH_RISK"
            advice = "ALTO RIESGO: EVITAR ENTRADA TARDÍA"

        reason = self._build_reason(status, reasons, warnings)

        return {
            "revalidation_status": status,
            "revalidation_score": score,
            "revalidation_reason": reason,
            "revalidation_advice": advice,
            "signal_age_label": age_label,
            "revalidation_warnings": warnings,
            "revalidation_positive_factors": reasons,
            "last_revalidated_minute": current_minute,
            "active_minutes": active_minutes,
        }

    def _build_reason(
        self,
        status: str,
        reasons: List[str],
        warnings: List[str],
    ) -> str:
        if status == "STRONG":
            return "Señal fuerte: " + ", ".join(reasons[:4]) if reasons else "Señal todavía fuerte"

        if warnings:
            return "Revalidación: " + ", ".join(warnings[:4])

        return "Revalidación activa"

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
