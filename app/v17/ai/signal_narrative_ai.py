from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class SignalNarrativeAI:
    """
    Narrativa final V17.

    Este módulo NO decide la señal.
    Este módulo NO cambia el mercado.
    Este módulo SOLO redacta la explicación final coherente para el panel.

    Objetivo:
    - Evitar frases fijas contradictorias.
    - Explicar según estado real del partido.
    - Respetar MatchMaturityAI, PanelDecisionAI, prepartido y lectura live.
    - Separar lectura principal, riesgo alternativo y acción operativa.
    """

    VERSION = "V17_SIGNAL_NARRATIVE_AI_1"

    def build(
        self,
        signal: Dict[str, Any],
        match_reader: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_reader = match_reader or {}

        minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("estimated_minute"),
            0,
        )

        scoreline = str(
            signal.get("scoreline")
            or signal.get("current_score")
            or f"{safe_int(signal.get('home_score'), 0)}-{safe_int(signal.get('away_score'), 0)}"
        )

        market = str(
            signal.get("market")
            or signal.get("master_market")
            or signal.get("suggested_market")
            or "NO_BET"
        ).upper()

        dominant = str(
            signal.get("football_dominant_reading")
            or match_reader.get("football_dominant_reading")
            or market
            or "SIN_LECTURA"
        ).upper()

        alternative = str(
            signal.get("football_alternative_reading")
            or signal.get("alternative_label")
            or match_reader.get("football_alternative_reading")
            or ""
        ).upper()

        master_status = str(signal.get("master_status") or "").upper()
        master_action = str(signal.get("master_action") or "").upper()
        panel_status = str(signal.get("panel_status") or signal.get("panel_label") or "").upper()

        maturity_permission = str(signal.get("match_maturity_entry_permission") or "").upper()
        maturity_label = str(
            signal.get("panel_maturity_label")
            or signal.get("match_maturity_panel_label")
            or ""
        ).upper()
        maturity_note = str(signal.get("match_maturity_panel_note") or "")

        over_score = safe_float(
            signal.get("over_score")
            or signal.get("result_over")
            or signal.get("over_probability")
            or 0,
            0,
        )
        under_score = safe_float(
            signal.get("under_score")
            or signal.get("result_under")
            or signal.get("under_probability")
            or 0,
            0,
        )

        confidence = safe_float(
            signal.get("football_confidence")
            or signal.get("master_confidence")
            or signal.get("panel_confidence")
            or 0,
            0,
        )

        data_quality = str(signal.get("data_quality") or "").upper()
        risk_status = str(signal.get("risk_status") or signal.get("risk") or "").upper()
        context_category = str(signal.get("context_category") or "").upper()

        league_goal_profile = str(signal.get("league_goal_profile") or "UNKNOWN_LEAGUE").upper()
        team_goal_profile = str(signal.get("team_goal_profile") or "UNKNOWN_TEAMS").upper()
        first_half_goal_risk = str(signal.get("first_half_goal_risk") or "").upper()
        second_half_goal_risk = str(signal.get("second_half_goal_risk") or "").upper()
        under_early_risk = str(signal.get("under_early_risk") or "").upper()
        pre_match_note = str(signal.get("pre_match_panel_note") or "")

        live_volume_score = safe_float(signal.get("match_maturity_live_volume_score"), 0)
        pressure = safe_float(
            signal.get("pressure")
            or signal.get("pressure_score")
            or signal.get("football_pressure")
            or 0,
            0,
        )

        shots = safe_int(signal.get("shots"), 0)
        shots_on_target = safe_int(signal.get("shots_on_target"), 0)
        dangerous_attacks = safe_int(signal.get("dangerous_attacks"), 0)
        corners = safe_int(signal.get("corners"), 0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0)

        support_points = self._collect_points(
            signal.get("match_maturity_support_points"),
            signal.get("football_support_points"),
            signal.get("pre_match_support_points"),
            signal.get("support_points"),
        )

        caution_points = self._collect_points(
            signal.get("match_maturity_warnings"),
            signal.get("football_caution_points"),
            signal.get("pre_match_caution_points"),
            signal.get("missing_points"),
            signal.get("logic_warnings"),
            signal.get("soft_warnings"),
        )

        operative_state = self._operative_state(
            master_status=master_status,
            master_action=master_action,
            maturity_permission=maturity_permission,
            panel_status=panel_status,
        )

        reading_name = self._reading_name(
            market=market,
            dominant=dominant,
        )

        final_title = self._final_title(
            operative_state=operative_state,
            reading_name=reading_name,
            maturity_label=maturity_label,
            market=market,
            dominant=dominant,
            alternative=alternative,
        )

        main_reason = self._main_reason(
            operative_state=operative_state,
            reading_name=reading_name,
            minute=minute,
            scoreline=scoreline,
            market=market,
            dominant=dominant,
            alternative=alternative,
            over_score=over_score,
            under_score=under_score,
            confidence=confidence,
            data_quality=data_quality,
            risk_status=risk_status,
            context_category=context_category,
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            pre_match_note=pre_match_note,
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
            maturity_note=maturity_note,
        )

        short_panel_message = self._short_panel_message(
            operative_state=operative_state,
            reading_name=reading_name,
            alternative=alternative,
            caution_points=caution_points,
            maturity_note=maturity_note,
        )

        action_message = self._action_message(
            operative_state=operative_state,
            maturity_permission=maturity_permission,
        )

        alternative_message = self._alternative_message(
            dominant=dominant,
            alternative=alternative,
            over_score=over_score,
            under_score=under_score,
            live_volume_score=live_volume_score,
        )

        return {
            "signal_narrative_version": self.VERSION,
            "narrative_title": final_title,
            "narrative_main_reason": main_reason,
            "narrative_short_panel_message": short_panel_message,
            "narrative_action_message": action_message,
            "narrative_alternative_message": alternative_message,
            "narrative_operative_state": operative_state,
            "narrative_reading_name": reading_name,
            "narrative_support_points": support_points[:6],
            "narrative_caution_points": caution_points[:6],

            # Campos que puede usar el panel directamente
            "main_reading": main_reason,
            "recommended_panel_message": short_panel_message,
            "panel_narrative_title": final_title,
            "panel_narrative_reason": main_reason,
            "panel_narrative_action": action_message,
            "panel_narrative_alternative": alternative_message,
        }

    def _operative_state(
        self,
        master_status: str,
        master_action: str,
        maturity_permission: str,
        panel_status: str,
    ) -> str:
        text = f"{master_status} {master_action} {maturity_permission} {panel_status}"

        if "BLOCK" in text or "NO_OPERAR" in text:
            return "BLOCKED"

        if "WAIT_REVALIDATION" in text or "ESPERAR_REVALIDACION" in text:
            return "REVALIDATION"

        if "WAIT_CONFIRMATION" in text or "ESPERAR_CONFIRMACION" in text:
            return "WAIT_CONFIRMATION"

        if "PANORAMA_ONLY" in text or "SOLO_PANORAMA" in text:
            return "PANORAMA"

        if "OBSERVE" in text or "OBSERVAR" in text or "OBSERVADOR" in text:
            return "OBSERVATION"

        if "ALLOW_STRONG_SIGNAL" in text or "OPERABLE" in text or "PUBLICAR" in text:
            return "OPERABLE"

        if "ALLOW_CANDIDATE" in text or "CANDIDATE" in text or "CANDIDATO" in text:
            return "CANDIDATE"

        return "OBSERVATION"

    def _reading_name(self, market: str, dominant: str) -> str:
        text = f"{market} {dominant}".upper()

        if "OVER" in text or "ALTO" in text:
            return "OVER"

        if "UNDER" in text or "BAJO" in text:
            return "UNDER"

        if "NO_BET" in text:
            return "NO_BET"

        return "LECTURA MIXTA"

    def _final_title(
        self,
        operative_state: str,
        reading_name: str,
        maturity_label: str,
        market: str,
        dominant: str,
        alternative: str,
    ) -> str:
        if maturity_label:
            return maturity_label.replace("_", " ")

        if operative_state == "BLOCKED":
            return "ENTRADA BLOQUEADA"

        if operative_state == "REVALIDATION":
            return f"{reading_name} EN REVALIDACIÓN"

        if operative_state == "WAIT_CONFIRMATION":
            return f"{reading_name} EN CONFIRMACIÓN"

        if operative_state == "PANORAMA":
            return f"PANORAMA {reading_name}"

        if operative_state == "OBSERVATION":
            if "OVER" in alternative and reading_name == "UNDER":
                return "UNDER EN OBSERVACIÓN CON RIESGO OVER"
            return f"{reading_name} EN OBSERVACIÓN"

        if operative_state == "OPERABLE":
            return f"{reading_name} OPERABLE"

        if operative_state == "CANDIDATE":
            return f"{reading_name} CANDIDATO"

        return "PARTIDO EN LECTURA"

    def _main_reason(
        self,
        operative_state: str,
        reading_name: str,
        minute: int,
        scoreline: str,
        market: str,
        dominant: str,
        alternative: str,
        over_score: float,
        under_score: float,
        confidence: float,
        data_quality: str,
        risk_status: str,
        context_category: str,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        pre_match_note: str,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
        maturity_note: str,
    ) -> str:
        base = self._base_reading_sentence(
            reading_name=reading_name,
            minute=minute,
            scoreline=scoreline,
            over_score=over_score,
            under_score=under_score,
            confidence=confidence,
        )

        live = self._live_sentence(
            live_volume_score=live_volume_score,
            pressure=pressure,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            corners=corners,
            xg=xg,
        )

        pre = self._pre_match_sentence(
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            pre_match_note=pre_match_note,
        )

        decision = self._decision_sentence(
            operative_state=operative_state,
            reading_name=reading_name,
            alternative=alternative,
            data_quality=data_quality,
            risk_status=risk_status,
            context_category=context_category,
            maturity_note=maturity_note,
        )

        return f"{base} {live} {pre} {decision}".strip()

    def _base_reading_sentence(
        self,
        reading_name: str,
        minute: int,
        scoreline: str,
        over_score: float,
        under_score: float,
        confidence: float,
    ) -> str:
        if reading_name == "UNDER":
            return (
                f"La lectura principal se inclina hacia UNDER en el minuto {minute}, "
                f"con marcador {scoreline}. El soporte UNDER aparece en {under_score:.0f}% "
                f"frente a OVER {over_score:.0f}%."
            )

        if reading_name == "OVER":
            return (
                f"La lectura principal se inclina hacia OVER en el minuto {minute}, "
                f"con marcador {scoreline}. El soporte OVER aparece en {over_score:.0f}% "
                f"frente a UNDER {under_score:.0f}%."
            )

        return (
            f"El partido está en lectura mixta en el minuto {minute}, "
            f"con marcador {scoreline}. No existe una lectura única suficientemente limpia."
        )

    def _live_sentence(
        self,
        live_volume_score: float,
        pressure: float,
        shots: int,
        shots_on_target: int,
        dangerous_attacks: int,
        corners: int,
        xg: float,
    ) -> str:
        if live_volume_score >= 65:
            return (
                f"El volumen ofensivo live es alto, con {shots} remates, "
                f"{shots_on_target} al arco, {corners} córners y presión estimada de {pressure:.0f}%."
            )

        if live_volume_score >= 35:
            return (
                f"El volumen ofensivo live es medio, con {shots} remates, "
                f"{shots_on_target} al arco y {corners} córners, por lo que la lectura requiere confirmación."
            )

        return (
            f"El volumen ofensivo live es bajo, con {shots} remates, "
            f"{shots_on_target} al arco, {dangerous_attacks} ataques peligrosos y xG {xg:.2f}."
        )

    def _pre_match_sentence(
        self,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        pre_match_note: str,
    ) -> str:
        parts: List[str] = []

        if league_goal_profile and league_goal_profile != "UNKNOWN_LEAGUE":
            parts.append(f"La memoria previa clasifica la liga como {league_goal_profile}.")

        if team_goal_profile and team_goal_profile != "UNKNOWN_TEAMS":
            parts.append(f"El perfil previo de los equipos es {team_goal_profile}.")

        if first_half_goal_risk and "HIGH" in first_half_goal_risk:
            parts.append("Existe advertencia previa de gol en primer tiempo.")

        if second_half_goal_risk and "HIGH" in second_half_goal_risk:
            parts.append("Existe advertencia previa de gol en segundo tiempo.")

        if under_early_risk and "HIGH" in under_early_risk:
            parts.append("El sistema marca riesgo alto para UNDER temprano.")

        if pre_match_note:
            parts.append(pre_match_note)

        if not parts:
            return "La memoria previa no agrega una advertencia fuerte y deja mayor peso a la lectura live."

        return " ".join(parts[:3])

    def _decision_sentence(
        self,
        operative_state: str,
        reading_name: str,
        alternative: str,
        data_quality: str,
        risk_status: str,
        context_category: str,
        maturity_note: str,
    ) -> str:
        reasons: List[str] = []

        if data_quality in {"LOW", "BAD", "INVALID"}:
            reasons.append("la calidad de datos no permite elevar la señal solo por marcador")

        if risk_status in {"HIGH_RISK", "EXTREME_RISK", "ALTO", "EXTREMO"}:
            reasons.append("el riesgo operativo exige cautela")

        if "OVER" in alternative and reading_name == "UNDER":
            reasons.append("existe una alternativa OVER WATCH que advierte posible ruptura")

        if "UNDER" in alternative and reading_name == "OVER":
            reasons.append("existe una alternativa UNDER que advierte posible cierre")

        if context_category in {"MUERTO", "CERRADO", "CONTROL"} and reading_name == "OVER":
            reasons.append("el contexto del partido todavía no confirma apertura total")

        if maturity_note:
            reasons.append(maturity_note)

        if operative_state == "OPERABLE":
            return "La señal queda operable porque la lectura principal, el contexto live y la madurez coinciden."

        if operative_state == "CANDIDATE":
            return "La señal queda como candidata porque existe soporte suficiente, aunque todavía requiere seguimiento."

        if operative_state == "REVALIDATION":
            detail = ", ".join(reasons[:3]) if reasons else "todavía falta confirmación live"
            return f"Por eso el sistema no autoriza entrada directa y envía la lectura a revalidación, porque {detail}."

        if operative_state == "WAIT_CONFIRMATION":
            detail = ", ".join(reasons[:3]) if reasons else "todavía faltan filtros de confirmación"
            return f"Por eso el sistema mantiene espera de confirmación, porque {detail}."

        if operative_state == "PANORAMA":
            return "El sistema ya tiene panorama futbolístico, pero todavía no autoriza una entrada."

        if operative_state == "OBSERVATION":
            detail = ", ".join(reasons[:3]) if reasons else "la señal no tiene madurez suficiente"
            return f"Por eso la lectura queda en observación, porque {detail}."

        if operative_state == "BLOCKED":
            detail = ", ".join(reasons[:3]) if reasons else "hay condición crítica activa"
            return f"La entrada queda bloqueada porque {detail}."

        return "El sistema mantiene lectura preventiva sin autorización operativa."

    def _short_panel_message(
        self,
        operative_state: str,
        reading_name: str,
        alternative: str,
        caution_points: List[str],
        maturity_note: str,
    ) -> str:
        if operative_state == "OPERABLE":
            return f"{reading_name} operable. Lectura principal y contexto alineados."

        if operative_state == "CANDIDATE":
            return f"{reading_name} candidato. Requiere seguimiento antes de confirmar."

        if operative_state == "REVALIDATION":
            return maturity_note or f"{reading_name} en revalidación. Falta confirmación."

        if operative_state == "WAIT_CONFIRMATION":
            return maturity_note or f"{reading_name} espera confirmación."

        if operative_state == "PANORAMA":
            return f"Panorama {reading_name}. Sin entrada autorizada todavía."

        if operative_state == "OBSERVATION":
            if "OVER" in alternative and reading_name == "UNDER":
                return "UNDER en observación con riesgo alternativo OVER WATCH."
            if caution_points:
                return f"Observación. {str(caution_points[0])}"
            return f"{reading_name} en observación."

        if operative_state == "BLOCKED":
            if caution_points:
                return f"Bloqueado. {str(caution_points[0])}"
            return "Entrada bloqueada por condición crítica."

        return "Partido en lectura."

    def _action_message(
        self,
        operative_state: str,
        maturity_permission: str,
    ) -> str:
        if operative_state == "OPERABLE":
            return "Acción sugerida del sistema: señal operable, siempre con gestión de riesgo."

        if operative_state == "CANDIDATE":
            return "Acción sugerida del sistema: candidato en seguimiento, no tratar como entrada automática."

        if operative_state == "REVALIDATION":
            return "Acción sugerida del sistema: esperar revalidación antes de considerar entrada."

        if operative_state == "WAIT_CONFIRMATION":
            return "Acción sugerida del sistema: esperar confirmación de filtros."

        if operative_state == "PANORAMA":
            return "Acción sugerida del sistema: solo lectura de panorama, sin entrada."

        if operative_state == "OBSERVATION":
            return "Acción sugerida del sistema: observar, no entrar todavía."

        if operative_state == "BLOCKED":
            return "Acción sugerida del sistema: no operar."

        return "Acción sugerida del sistema: mantener observación."

    def _alternative_message(
        self,
        dominant: str,
        alternative: str,
        over_score: float,
        under_score: float,
        live_volume_score: float,
    ) -> str:
        if not alternative or alternative in {"NONE", "SIN ALTERNATIVA", "N/A"}:
            return "No existe alternativa fuerte visible."

        if "OVER" in alternative:
            return (
                f"Alternativa activa: OVER WATCH. No reemplaza automáticamente la lectura principal, "
                f"pero advierte riesgo de ruptura. OVER {over_score:.0f}%, UNDER {under_score:.0f}%, "
                f"volumen live {live_volume_score:.0f}/100."
            )

        if "UNDER" in alternative or "BAJO" in alternative:
            return (
                f"Alternativa activa: UNDER. No reemplaza automáticamente la lectura principal, "
                f"pero advierte posible cierre del partido. UNDER {under_score:.0f}%, OVER {over_score:.0f}%."
            )

        return f"Alternativa activa: {alternative}."

    def _collect_points(self, *groups: Any) -> List[str]:
        points: List[str] = []

        for group in groups:
            if not group:
                continue

            if isinstance(group, str):
                points.append(group)
                continue

            if isinstance(group, list):
                for item in group:
                    if item is None:
                        continue
                    points.append(str(item))

        cleaned: List[str] = []
        seen = set()

        for point in points:
            text = point.strip()
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            cleaned.append(text)

        return cleaned
