from __future__ import annotations

from typing import Any, Dict, List


class LeagueStabilityEngine:
    """
    Evalúa qué tan confiable o peligrosa es una liga para generar señales.

    No crea señales.
    No decide entradas.
    Solo entrega contexto de estabilidad para que la IA no opere a ciegas.
    """

    LOW_DATA_KEYWORDS = [
        "reserve",
        "reserves",
        "u20",
        "u21",
        "u23",
        "youth",
        "women",
        "femenino",
        "segunda",
        "third",
        "regional",
        "amateur",
        "cup",
    ]

    CHAOTIC_KEYWORDS = [
        "bolivia",
        "paraguay",
        "peru",
        "ecuador",
        "colombia",
        "venezuela",
        "uruguay",
        "chile",
        "argentina",
        "brasil",
        "brazil",
        "conmebol",
        "libertadores",
        "sudamericana",
    ]

    def evaluate(
        self,
        league: str | None = None,
        country: str | None = None,
        data_quality: str | None = None,
        history_items: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        league_text = str(league or "").lower()
        country_text = str(country or "").lower()
        quality = str(data_quality or "LOW").upper()

        history_items = history_items or []

        base_score = 60.0
        warnings: List[str] = []
        positive: List[str] = []

        if quality == "HIGH":
            base_score += 18
            positive.append("Datos live de alta calidad.")
        elif quality == "MEDIUM":
            base_score += 8
            positive.append("Datos live aceptables.")
        else:
            base_score -= 18
            warnings.append("Datos insuficientes o incompletos.")

        if self._contains_any(league_text, self.LOW_DATA_KEYWORDS):
            base_score -= 18
            warnings.append("Liga o categoría con posible baja cobertura de datos.")

        if self._contains_any(country_text, self.CHAOTIC_KEYWORDS) or self._contains_any(
            league_text, self.CHAOTIC_KEYWORDS
        ):
            base_score -= 8
            warnings.append("Entorno CONMEBOL o liga con posible variabilidad táctica alta.")

        history_profile = self._history_profile(history_items)

        if history_profile["sample_size"] >= 20:
            base_score += 8
            positive.append("Existe muestra histórica suficiente para comparar patrones.")

            if history_profile["loss_rate"] >= 55:
                base_score -= 16
                warnings.append("Historial propio muestra demasiadas señales fallidas en esta liga.")

            if history_profile["win_rate"] >= 60:
                base_score += 10
                positive.append("Historial propio favorable para esta liga.")
        else:
            base_score -= 6
            warnings.append("Muestra histórica todavía pequeña para esta liga.")

        stability_score = max(0.0, min(100.0, base_score))
        stability_level = self._level(stability_score)

        return {
            "league_stability_enabled": True,
            "league_stability_score": round(stability_score, 2),
            "league_stability_level": stability_level,
            "league_stability_warnings": warnings,
            "league_stability_positive_factors": positive,
            "league_history_profile": history_profile,
            "league_operational_advice": self._advice(stability_level, warnings),
        }

    def _contains_any(self, text: str, keywords: List[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _history_profile(self, history_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(history_items)

        wins = sum(
            1
            for item in history_items
            if str(item.get("resultado") or item.get("status") or "").upper() == "WIN"
        )

        losses = sum(
            1
            for item in history_items
            if str(item.get("resultado") or item.get("status") or "").upper() == "LOSS"
        )

        settled = wins + losses

        win_rate = (wins / settled * 100) if settled else 0.0
        loss_rate = (losses / settled * 100) if settled else 0.0

        over_items = [
            item
            for item in history_items
            if str(item.get("market") or "").upper() == "OVER"
        ]

        under_items = [
            item
            for item in history_items
            if str(item.get("market") or "").upper() == "UNDER"
        ]

        return {
            "sample_size": total,
            "settled": settled,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "loss_rate": round(loss_rate, 2),
            "over_signals": len(over_items),
            "under_signals": len(under_items),
        }

    def _level(self, score: float) -> str:
        if score >= 78:
            return "CONFIABLE"
        if score >= 58:
            return "MEDIA"
        if score >= 38:
            return "INESTABLE"
        return "PELIGROSA"

    def _advice(self, level: str, warnings: List[str]) -> str:
        if level == "CONFIABLE":
            return "Liga apta para análisis normal. Mantener filtros tácticos habituales."

        if level == "MEDIA":
            return "Liga operable con confirmación live. Evitar entradas tempranas sin presión real."

        if level == "INESTABLE":
            return "Liga riesgosa. Solo considerar señales fuertes con datos confirmados."

        return "Liga peligrosa. Priorizar observación y evitar entradas salvo confirmación excepcional."
