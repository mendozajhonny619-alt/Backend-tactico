from __future__ import annotations

from typing import Any, Dict


class TacticalEngine:
    """
    Motor táctico del partido.

    Clasifica el estado del juego en:

    - EXPLOSIVO
    - CALIENTE
    - CONTROLADO
    - FRIO
    - MUERTO

    Y además:
    - tempo_label
    - tactical_bias (OVER / UNDER / NEUTRAL)
    - market_alignment
    """

    def evaluate(
        self,
        context: Dict[str, Any],
        window: Dict[str, Any],
    ) -> Dict[str, Any]:

        context = context or {}
        window = window or {}

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_prob = self._safe_float(
            context.get("goal_probability")
            or context.get("goal_window_score")
        )
        minute = self._safe_float(context.get("minute"))

        dominance = str(context.get("dominance") or "BALANCED").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()

        # ---------------------------------------------------
        # 🔥 CLASIFICACIÓN TÁCTICA PRINCIPAL
        # ---------------------------------------------------

        if pressure >= 25 and rhythm >= 18:
            tactical_state = "EXPLOSIVO"

        elif pressure >= 18 and rhythm >= 14:
            tactical_state = "CALIENTE"

        elif pressure >= 12 and rhythm >= 10:
            tactical_state = "CONTROLADO"

        elif pressure >= 7 and rhythm >= 7:
            tactical_state = "FRIO"

        else:
            tactical_state = "MUERTO"

        # ---------------------------------------------------
        # ⚡ TEMPO
        # ---------------------------------------------------

        if rhythm >= 18:
            tempo_label = "ALTISIMO"
        elif rhythm >= 14:
            tempo_label = "ALTO"
        elif rhythm >= 10:
            tempo_label = "MEDIO"
        elif rhythm >= 7:
            tempo_label = "BAJO"
        else:
            tempo_label = "MUY_BAJO"

        # ---------------------------------------------------
        # 🎯 BIAS DE MERCADO (OVER / UNDER)
        # ---------------------------------------------------

        if tactical_state in {"EXPLOSIVO", "CALIENTE"} and goal_prob >= 60:
            tactical_bias = "OVER"

        elif tactical_state in {"CONTROLADO", "FRIO", "MUERTO"} and goal_prob <= 52:
            tactical_bias = "UNDER"

        else:
            tactical_bias = "NEUTRAL"

        # ---------------------------------------------------
        # 🧠 ALINEACIÓN CON MERCADO (SIMULADA)
        # ---------------------------------------------------

        market_alignment = self._calculate_alignment(
            tactical_state,
            tactical_bias,
            context_state,
        )

        return {
            "tactical_state": tactical_state,
            "tempo_label": tempo_label,
            "tactical_bias": tactical_bias,
            "market_alignment": market_alignment,
        }

    # ---------------------------------------------------
    # 🔍 ALIGNMENT
    # ---------------------------------------------------

    def _calculate_alignment(
        self,
        tactical_state: str,
        tactical_bias: str,
        context_state: str,
    ) -> str:

        if tactical_bias == "OVER":
            if tactical_state in {"EXPLOSIVO", "CALIENTE"} and context_state in {
                "CALIENTE",
                "MUY_CALIENTE",
                "TIBIO",
            }:
                return "ALTA"
            return "MEDIA"

        if tactical_bias == "UNDER":
            if tactical_state in {"CONTROLADO", "FRIO", "MUERTO"} and context_state in {
                "FRIO",
                "MUERTO",
                "CONTROLADO",
                "TIBIO",
            }:
                return "ALTA"
            return "MEDIA"

        return "BAJA"

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
