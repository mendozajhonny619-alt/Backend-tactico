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
    - lectura live avanzada
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
        match = match or {}
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
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))

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
        market_type = str(market.get("market_type") or market.get("market") or "").upper() if market else ""
        odds = self._safe_float(market.get("odds")) if market else 0.0
        line = market.get("line") if market else None
        market_status = str(market.get("market_status") or "").upper() if market else ""
        market_live_bias = str(market.get("market_live_bias") or "").upper() if market else ""

        value_ok = bool(value.get("is_value")) if value else False
        value_edge = self._safe_float(value.get("edge")) if value else 0.0
        value_category = str(value.get("value_category") or "NONE").upper() if value else "NONE"

        live_profile = self._live_profile(match, context)

        consensus = self._build_consensus(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            context_state=context_state,
            tactical_bias=tactical_bias,
            market_valid=market_valid,
            market_type=market_type,
            market_status=market_status,
            market_live_bias=market_live_bias,
            value_ok=value_ok,
            risk_score=risk_score,
            live_profile=live_profile,
        )

        recommended_market = self._recommended_market(
            tactical_bias=tactical_bias,
            over_probability=over_probability,
            under_probability=under_probability,
            market_type=market_type,
            market_valid=market_valid,
            live_profile=live_profile,
            market_live_bias=market_live_bias,
        )

        analyst_label = self._analyst_label(
            consensus_score=consensus["consensus_score"],
            risk_score=risk_score,
            value_ok=value_ok,
            market_valid=market_valid,
            market_status=market_status,
            tactical_state=tactical_state,
            live_profile=live_profile,
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
            market_status=market_status,
            odds=odds,
            line=line,
            value_ok=value_ok,
            value_edge=value_edge,
            value_category=value_category,
            recommended_market=recommended_market,
            analyst_label=analyst_label,
            live_profile=live_profile,
        )

        return {
            "analyst_label": analyst_label,
            "recommended_market": recommended_market,
            "technical_summary": technical_summary,
            "consensus": consensus,
            "analyst_live_profile": live_profile,
        }

    def _live_profile(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = self._extract_minute(match)

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        context_state = str(context.get("context_state") or "").upper()

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        red_alert = bool(context.get("red_alert", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        score_hold_probability = self._safe_float(
            match.get("score_hold_probability")
            or context.get("score_hold_probability")
        )
        retention_risk = self._safe_float(
            match.get("retention_risk")
            or context.get("retention_risk")
        )

        next_goal_bias = str(match.get("next_goal_bias") or "").upper()
        next_goal_confidence = self._safe_float(match.get("next_goal_confidence"))
        next_goal_support = str(match.get("next_goal_support") or "").upper()

        field_vision_status = str(context.get("field_vision_status") or match.get("field_vision_status") or "").upper()
        is_added_time = bool(
            context.get("is_added_time")
            or match.get("is_added_time")
            or context.get("field_vision_is_added_time")
            or match.get("field_vision_is_added_time")
            or minute >= 90
        )

        live_reactivation = self._has_live_reactivation(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        if fake_pressure_detected or pressure_without_depth:
            profile = "FAKE_PRESSURE"
            advice = "Presión sin profundidad. Evitar sobrevalorar OVER."
        elif retention_shape or score_hold_probability >= 70 or retention_risk >= 70:
            profile = "RETENTION"
            advice = "Partido con forma de retención. UNDER/hold tiene más sentido."
        elif under_transition_score >= 70:
            profile = "UNDER_TRANSITION"
            advice = "El partido está migrando a lectura UNDER."
        elif cooling_detected or live_decay_factor <= 0.70:
            profile = "COOLING"
            advice = "La intensidad se está enfriando."
        elif live_reactivation:
            profile = "LATE_REACTIVATION"
            advice = "Reactivación live detectada. OVER solo con confirmación fuerte."
        elif chaos_mode or red_alert:
            profile = "CHAOS"
            advice = "Partido abierto/volátil. Alta varianza."
        elif context_state in {"CALIENTE", "MUY_CALIENTE"}:
            profile = "HOT_MATCH"
            advice = "Partido con amenaza ofensiva real."
        elif context_state in {"FRIO", "MUERTO"}:
            profile = "COLD_MATCH"
            advice = "Partido frío. Cuidado con entradas por impulso."
        else:
            profile = "NORMAL"
            advice = "Lectura normal sin alerta extrema."

        return {
            "profile": profile,
            "advice": advice,
            "live_reactivation": live_reactivation,
            "late_reactivation": late_reactivation,
            "chaos_mode": chaos_mode,
            "red_alert": red_alert,
            "fake_pressure_detected": fake_pressure_detected,
            "pressure_without_depth": pressure_without_depth,
            "retention_shape": retention_shape,
            "cooling_detected": cooling_detected,
            "under_transition_score": under_transition_score,
            "score_hold_probability": score_hold_probability,
            "retention_risk": retention_risk,
            "next_goal_bias": next_goal_bias,
            "next_goal_confidence": next_goal_confidence,
            "next_goal_support": next_goal_support,
            "is_added_time": is_added_time,
            "field_vision_status": field_vision_status,
        }

    def _build_consensus(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
        tactical_bias: str,
        market_valid: bool,
        market_type: str,
        market_status: str,
        market_live_bias: str,
        value_ok: bool,
        risk_score: float,
        live_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks = 0
        details: list[str] = []

        profile = str(live_profile.get("profile") or "").upper()
        live_reactivation = bool(live_profile.get("live_reactivation"))

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

        if goal_window >= 12 or over_window >= 12:
            checks += 1
            details.append("WINDOW_THREAT_OK")

        if context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE", "CONTROLADO", "FRIO"}:
            checks += 1
            details.append("CONTEXT_OK")

        if market_valid and market_type == tactical_bias:
            checks += 1
            details.append("MARKET_ALIGNED")
        elif market_status in {"PENDING", "INTERNAL_ONLY"}:
            checks += 1
            details.append("MARKET_INTERNAL_OR_PENDING")
        elif not market_valid:
            details.append("MARKET_PENDING")

        if value_ok:
            checks += 1
            details.append("VALUE_OK")

        if risk_score <= 6.8:
            checks += 1
            details.append("RISK_OK")

        if live_reactivation:
            checks += 1
            details.append("LIVE_REACTIVATION_OK")

        if profile in {"RETENTION", "UNDER_TRANSITION"} and tactical_bias == "UNDER":
            checks += 1
            details.append("UNDER_CONTEXT_OK")

        if profile in {"FAKE_PRESSURE", "RETENTION"} and tactical_bias == "OVER":
            checks -= 1
            details.append("OVER_CONTEXT_WARNING")

        if market_live_bias in {"AGAINST_OVER", "AGAINST_UNDER"}:
            checks -= 1
            details.append("MARKET_LIVE_BIAS_WARNING")

        return {
            "consensus_score": max(0, checks),
            "details": details,
        }

    def _analyst_label(
        self,
        consensus_score: float,
        risk_score: float,
        value_ok: bool,
        market_valid: bool,
        market_status: str,
        tactical_state: str,
        live_profile: Dict[str, Any],
    ) -> str:
        profile = str(live_profile.get("profile") or "").upper()
        live_reactivation = bool(live_profile.get("live_reactivation"))

        has_market_support = market_valid or market_status in {"PENDING", "INTERNAL_ONLY"}

        if profile in {"FAKE_PRESSURE", "RETENTION"} and risk_score >= 6.5:
            return "ALERTA"

        if consensus_score >= 6 and risk_score <= 4.8 and value_ok and has_market_support:
            return "ALTA_CONVICCION"

        if live_reactivation and consensus_score >= 5 and risk_score <= 7.0:
            return "REACTIVACION"

        if consensus_score >= 5 and risk_score <= 6.8:
            return "OPERABLE"

        if profile in {"RETENTION", "UNDER_TRANSITION"} and consensus_score >= 4:
            return "LECTURA_UNDER"

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
        live_profile: Dict[str, Any],
        market_live_bias: str,
    ) -> str:
        profile = str(live_profile.get("profile") or "").upper()
        live_reactivation = bool(live_profile.get("live_reactivation"))
        next_goal_support = str(live_profile.get("next_goal_support") or "").upper()

        if profile in {"RETENTION", "UNDER_TRANSITION", "COOLING"} and under_probability >= 60:
            return "UNDER"

        if profile == "FAKE_PRESSURE":
            return "UNDER" if under_probability >= 58 else "OBSERVE"

        if market_live_bias == "AGAINST_OVER":
            return "UNDER" if under_probability >= 58 else "OBSERVE"

        if live_reactivation and over_probability >= 60:
            return "OVER"

        if next_goal_support == "SUPPORTS_UNDER" and under_probability >= 58:
            return "UNDER"

        if next_goal_support == "AGAINST_OVER":
            return "UNDER" if under_probability >= 58 else "OBSERVE"

        if market_valid and market_type in {"OVER", "UNDER"}:
            return market_type

        if tactical_bias == "OVER" and over_probability >= 58:
            return "OVER"

        if tactical_bias == "UNDER" and under_probability >= 62:
            return "UNDER"

        return "OBSERVE"

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
        market_status: str,
        odds: float,
        line: Any,
        value_ok: bool,
        value_edge: float,
        value_category: str,
        recommended_market: str,
        analyst_label: str,
        live_profile: Dict[str, Any],
    ) -> str:
        market_text = (
            f"mercado={market_type} cuota={round(odds, 2)} linea={line}"
            if market_valid and odds > 0
            else f"mercado={market_status or 'PENDIENTE'}"
        )

        value_text = (
            f"value={value_category} edge={round(value_edge, 4)}"
            if value_ok
            else "sin value confirmado"
        )

        return (
            f"{match_name} min {minute}: "
            f"perfil_live={live_profile.get('profile')}, consejo={live_profile.get('advice')}, "
            f"contexto={context_state}, tactico={tactical_state}, bias={tactical_bias}, "
            f"tempo={tempo_label}, dominio={dominance}, calidad_datos={data_quality}, "
            f"calidad_partido={game_quality}, ai_score={round(ai_score,2)}, "
            f"goal_prob={round(goal_probability,2)}, over_prob={round(over_probability,2)}, "
            f"under_prob={round(under_probability,2)}, pressure={round(pressure,2)}, "
            f"rhythm={round(rhythm,2)}, riesgo={risk_level}({round(risk_score,2)}), "
            f"alineacion_mercado={market_alignment}, {market_text}, {value_text}, "
            f"mercado_recomendado={recommended_market}, label={analyst_label}"
        )

    def _has_live_reactivation(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
        late_reactivation: bool,
        chaos_mode: bool,
        red_alert: bool,
        field_vision_status: str,
        is_added_time: bool,
    ) -> bool:
        if minute < 70:
            return False

        if late_reactivation or chaos_mode or red_alert:
            return True

        if field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
            return True

        if (
            pressure >= 26
            and rhythm >= 15
            and (goal_window >= 22 or over_window >= 22)
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if is_added_time and pressure >= 30 and rhythm >= 16:
            return True

        return False

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or 0
        )
        try:
            return int(float(raw))
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
