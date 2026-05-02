from __future__ import annotations

from typing import Any, Dict, List


class SignalRiskReducer:
    """
    Analiza señales activas y agrega avisos de riesgo.

    IMPORTANTE:
    - No bloquea señales.
    - No elimina señales.
    - No cambia el mercado.
    - Solo agrega lectura preventiva para ayudar a decidir mejor.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        market = str(signal.get("market") or "").upper()
        rank = str(signal.get("rank") or "").upper()
        risk_level = str(signal.get("risk_level") or "").upper()

        minute = self._safe_int(
            signal.get("current_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        entry_minute = self._safe_int(
            signal.get("entry_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        active_minutes = max(0, minute - entry_minute)

        signal_score = self._safe_float(signal.get("signal_score"))
        ai_score = self._safe_float(signal.get("ai_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))

        shots_on_target = self._safe_float(signal.get("shots_on_target"))
        shots = self._safe_float(signal.get("shots"))
        corners = self._safe_float(signal.get("corners"))
        dangerous_attacks = self._safe_float(signal.get("dangerous_attacks"))
        xg = self._safe_float(signal.get("xg") or signal.get("xG"))

        warnings: List[str] = []
        positives: List[str] = []

        # -----------------------------
        # Lecturas positivas
        # -----------------------------
        if rank in {"PREMIUM", "FUERTE", "BUENA"}:
            positives.append("Rango fuerte del sistema")

        if signal_score >= 70:
            positives.append("Signal Score alto")

        if ai_score >= 65:
            positives.append("IA con lectura favorable")

        if goal_probability >= 68:
            positives.append("Probabilidad de gol elevada")

        if market == "OVER" and over_probability >= 68:
            positives.append("Probabilidad OVER favorable")

        if market == "UNDER" and under_probability >= 68:
            positives.append("Probabilidad UNDER favorable")

        if shots_on_target >= 3:
            positives.append("Buen volumen de tiros al arco")

        if dangerous_attacks >= 20:
            positives.append("Ataques peligrosos relevantes")

        if xg >= 1.0:
            positives.append("xG competitivo")

        # -----------------------------
        # Alertas de riesgo
        # -----------------------------
        if risk_level == "ALTO" or risk_score >= 7.0:
            warnings.append("Riesgo alto detectado")

        if market == "OVER":
            if minute >= 80:
                warnings.append("OVER en minuto avanzado")

            if active_minutes >= 15:
                warnings.append("La señal lleva varios minutos activa sin cumplirse")

            if active_minutes >= 22:
                warnings.append("Señal enfriada por tiempo activo prolongado")

            if shots_on_target <= 1 and minute >= 65:
                warnings.append("Pocos tiros al arco para una señal OVER")

            if xg < 0.7 and minute >= 65:
                warnings.append("xG bajo para sostener alta probabilidad de gol")

            if dangerous_attacks < 12 and minute >= 65:
                warnings.append("Ataques peligrosos bajos para OVER")

        if market == "UNDER":
            if goal_probability >= 60:
                warnings.append("Amenaza de gol elevada para una señal UNDER")

            if shots_on_target >= 4:
                warnings.append("Demasiados tiros al arco para UNDER")

            if dangerous_attacks >= 28:
                warnings.append("Partido con presión alta contra UNDER")

        # -----------------------------
        # Estado final del avisador
        # -----------------------------
        status = "OK"
        live_advice = "SEÑAL LIMPIA SEGÚN LECTURA ACTUAL"

        if warnings:
            status = "CAUTION"
            live_advice = "SEÑAL VÁLIDA, PERO CON PRECAUCIÓN"

        if len(warnings) >= 3 or risk_score >= 7.5:
            status = "HIGH_CAUTION"
            live_advice = "RIESGO ELEVADO: NO REFORZAR SIN NUEVA CONFIRMACIÓN"

        if market == "OVER" and active_minutes >= 22:
            status = "COOLING"
            live_advice = "SEÑAL ENFRIADA: OBSERVAR Y EVITAR REENTRADA"

        if market == "OVER" and minute >= 85 and active_minutes >= 15:
            status = "HIGH_CAUTION"
            live_advice = "MINUTO MUY AVANZADO: SOLO CON PRESIÓN EXTREMA"

        reason = self._build_reason(
            status=status,
            positives=positives,
            warnings=warnings,
        )

        return {
            "risk_reducer_status": status,
            "risk_reducer_reason": reason,
            "live_advice": live_advice,
            "risk_warnings": warnings,
            "positive_factors": positives,
            "active_minutes": active_minutes,
        }

    def _build_reason(
        self,
        status: str,
        positives: List[str],
        warnings: List[str],
    ) -> str:
        if status == "OK":
            if positives:
                return "Señal limpia: " + ", ".join(positives[:4])
            return "Señal sin alertas relevantes"

        if warnings:
            return "Aviso PRO: " + ", ".join(warnings[:4])

        return "Lectura preventiva activa"

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
