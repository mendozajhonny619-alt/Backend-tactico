from __future__ import annotations

from typing import Any, Dict


class MatchAnalystEngine:
    """
    Unifica la lectura técnica final del partido.

    Resume:
    - contexto
    - IA
    - táctica
    - riesgo
    - mercado
    - value

    Devuelve:
    - analyst_label
    - recommended_market
    - technical_summary
    - consensus
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        market: Dict[str, Any] | None,
        value: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        context = context or {}
        ai = ai or {}
        window = window or {}
        tactical = tactical or {}
        risk = risk or {}
        market = market or {}
        value = value or {}

        minute = self._extract_minute(match)
        match_name = match.get("match_name") or self._build_match_name(match)

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        dominance = str(context.get("dominance") or "BALANCED").upper()

        tactical_state = str(tactical.get("tactical_state") or "MUERTO").upper()
        tactical_bias = str(tactical.get("tactical_bias") or "NEUTRAL").upper()
        tempo_label = str(tactical.get("tempo_label") or "MUY_BAJO").upper()
        market_alignment = str(tactical.get("market_alignment") or "BAJA").upper()

        risk_score = self._safe_float(risk.get("risk_score"))
        risk_level = str(risk.get("risk_level") or "ALTO").upper()

        market_valid = bool(market.get("is_valid")) if market else False
        market_type = str(market.get("market_type") or "").upper() if market else ""
        odds = self._safe_float(market.get("odds")) if market else 0.0
        line = market.get("line") if market else None

        value_ok = bool(value.get("is_value")) if value else False
        value_edge = self._safe_float(value.get("edge")) if value else 0.0
        value_category = str(value.get("value_category") or "NONE").upper() if value else "NONE"

        consensus = self._build_consensus(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            tactical_bias=tactical_bias,
            market_valid=market_valid,
            market_type=market_type,
            value_ok=value_ok,
            risk_score=risk_score,
        )

        recommended_market = self._recommended_market(
            tactical_bias=tactical_bias,
            over_probability=over_probability,
            under_probability=under_probability,
            market_type=market_type,
            market_valid=market_valid,
        )

        analyst_label = self._analyst_label(
            consensus_score=consensus["consensus_score"],
            risk_score=risk_score,
            value_ok=value_ok,
            market_valid=market_valid,
            tactical_state=tactical_state,
        )

        technical_summary = self._build_summary(
            match_name=match_name,
            minute=minute,
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            pressure=pressure,
            rhythm=rhythm,
            data_quality=data_quality,
            game_quality=game_quality,
            context_state=context_state,
            dominance=dominance,
            tactical_state=tactical_state,
            tactical_bias=tactical_bias,
            tempo_label=tempo_label,
            market_alignment=market_alignment,
            risk_score=risk_score,
            risk_level=risk_level,
            market_valid=market_valid,
            market_type=market_type,
            odds=odds,
            line=line,
            value_ok=value_ok,
            value_edge=value_edge,
            value_category=value_category,
            recommended_market=recommended_market,
            analyst_label=analyst_label,
        )

        return {
            "analyst_label": analyst_label,
            "recommended_market": recommended_market,
            "technical_summary": technical_summary,
            "consensus": consensus,
        }

    # ---------------------------------------------------
    # Consensus / label
    # ---------------------------------------------------

    def _build_consensus(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        pressure: float,
        rhythm: float,
        context_state: str,
        tactical_bias: str,
        market_valid: bool,
        market_type: str,
        value_ok: bool,
        risk_score: float,
    ) -> Dict[str, Any]:
        checks = 0
        details: list[str] = []

        if ai_score >= 60:
            checks += 1
            details.append("AI_OK")

        if tactical_bias == "OVER" and over_probability >= 60:
            checks += 1
            details.append("OVER_PROB_OK")
        elif tactical_bias == "UNDER" and under_probability >= 64:
            checks += 1
            details.append("UNDER_PROB_OK")

        if pressure >= 14 or rhythm >= 10:
            checks += 1
            details.append("TEMPO_OK")

        if context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE", "CONTROLADO", "FRIO"}:
            checks += 1
            details.append("CONTEXT_OK")

        if market_valid and market_type == tactical_bias:
            checks += 1
            details.append("MARKET_ALIGNED")
        elif not market_valid:
            details.append("MARKET_PENDING")

        if value_ok:
            checks += 1
            details.append("VALUE_OK")

        if risk_score <= 6.5:
            checks += 1
            details.append("RISK_OK")

        return {
            "consensus_score": checks,
            "details": details,
        }

    def _analyst_label(
        self,
        consensus_score: float,
        risk_score: float,
        value_ok: bool,
        market_valid: bool,
        tactical_state: str,
    ) -> str:
        if consensus_score >= 6 and risk_score <= 4.5 and value_ok and market_valid:
            return "ALTA_CONVICCION"

        if consensus_score >= 5 and risk_score <= 6.5:
            return "OPERABLE"

        if tactical_state in {"CALIENTE", "EXPLOSIVO", "CONTROLADO", "FRIO"} and consensus_score >= 3:
            return "OBSERVABLE"

        return "DEBIL"

    def _recommended_market(
        self,
        tactical_bias: str,
        over_probability: float,
        under_probability: float,
        market_type: str,
        market_valid: bool,
    ) -> str:
        if market_valid and market_type in {"OVER", "UNDER"}:
            return market_type

        if tactical_bias == "OVER" and over_probability >= 58:
            return "OVER"

        if tactical_bias == "UNDER" and under_probability >= 62:
            return "UNDER"

        return "OBSERVE"

    # ---------------------------------------------------
    # Summary
    # ---------------------------------------------------

    def _build_summary(
        self,
        match_name: str,
        minute: int,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        pressure: float,
        rhythm: float,
        data_quality: str,
        game_quality: str,
        context_state: str,
        dominance: str,
        tactical_state: str,
        tactical_bias: str,
        tempo_label: str,
        market_alignment: str,
        risk_score: float,
        risk_level: str,
        market_valid: bool,
        market_type: str,
        odds: float,
        line: Any,
        value_ok: bool,
        value_edge: float,
        value_category: str,
        recommended_market: str,
        analyst_label: str,
    ) -> str:
        market_text = (
            f"mercado={market_type} cuota={round(odds, 2)} linea={line}"
            if market_valid
            else "mercado pendiente/no válido"
        )

        value_text = (
            f"value={value_category} edge={round(value_edge, 4)}"
            if value_ok
            else "sin value confirmado"
        )

        return (
            f"{match_name} min {minute}: "
            f"contexto={context_state}, tactico={tactical_state}, bias={tactical_bias}, "
            f"tempo={tempo_label}, dominio={dominance}, calidad_datos={data_quality}, "
            f"calidad_partido={game_quality}, ai_score={round(ai_score,2)}, "
            f"goal_prob={round(goal_probability,2)}, over_prob={round(over_probability,2)}, "
            f"under_prob={round(under_probability,2)}, pressure={round(pressure,2)}, "
            f"rhythm={round(rhythm,2)}, riesgo={risk_level}({round(risk_score,2)}), "
            f"alineacion_mercado={market_alignment}, {market_text}, {value_text}, "
            f"mercado_recomendado={recommended_market}, label={analyst_label}"
        )

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or 0
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def _build_match_name(self, match: Dict[str, Any]) -> str:
        home_name = (
            match.get("home_name")
            or match.get("home_team")
            or match.get("home")
            or "HOME"
        )
        away_name = (
            match.get("away_name")
            or match.get("away_team")
            or match.get("away")
            or "AWAY"
        )
        return f"{home_name} vs {away_name}"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
