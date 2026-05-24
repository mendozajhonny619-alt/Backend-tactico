from __future__ import annotations

from typing import Any, Dict, List


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_market(value: Any) -> str:
    text = str(value or "").upper()

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    if "SOBRE" in text:
        return "OVER"

    if "BAJO" in text:
        return "UNDER"

    return "OTHER"


class DecisionExplainerAI:
    """
    Capa explicadora y auditora de decisión V17.

    No reemplaza a TacticalAI, MarketAI, RiskAI, ContradictionJudge
    ni MasterDecisionAI.

    Su función es:
    - explicar por qué entró una señal
    - explicar por qué eligió OVER o UNDER
    - explicar por qué no eligió el mercado contrario
    - detectar contradicciones lógicas
    - recomendar degradación cuando la señal no está bien respaldada
    - entregar mensajes claros para el panel visual
    """

    CRITICAL_DATA_WARNINGS = {
        "LOW_STATS_DATA",
        "NO_SHOTS_DATA",
        "NO_SHOTS_ON_TARGET_DATA",
        "NO_DANGEROUS_ATTACKS_DATA",
        "NO_LIVE_STATS",
        "LOW_DATA_QUALITY",
    }

    CRITICAL_CLOCK_WARNINGS = {
        "CLOCK_FROZEN",
        "CLOCK_STALE",
        "MINUTE_LAG_DETECTED",
        "BLOCKED_CLOCK",
    }

    def explain(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        master: Dict[str, Any],
    ) -> Dict[str, Any]:
        selected_market = normalize_market(
            master.get("master_market")
            or market.get("suggested_market")
            or market.get("market")
        )

        minute = safe_int(
            match.get("api_minute")
            or match.get("display_minute")
            or match.get("minute"),
            0,
        )

        home_team = str(match.get("home_team") or match.get("home_name") or "Local")
        away_team = str(match.get("away_team") or match.get("away_name") or "Visitante")

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)

        data_quality = str(
            match.get("data_quality")
            or match.get("calidad_datos")
            or "LOW"
        ).upper()

        scan_phase = str(match.get("scan_phase") or "").upper()
        stats_source = str(match.get("stats_source") or "").upper()

        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        corners = safe_float(match.get("corners"), 0.0)
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        market_confidence = safe_float(market.get("market_confidence"), 0.0)

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)

        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        risk_status = str(risk.get("risk_status") or "").upper()
        risk_score = safe_float(risk.get("risk_score"), 0.0)

        contradiction_status = str(
            contradiction.get("contradiction_status") or ""
        ).upper()
        contradiction_score = safe_float(contradiction.get("contradiction_score"), 0.0)

        master_status = str(master.get("master_status") or "").upper()
        master_rank = str(master.get("master_rank") or "").upper()
        master_confidence = safe_float(master.get("master_confidence"), 0.0)

        warnings = self._collect_warnings(
            match=match,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            master=master,
        )

        support_points = self._build_support_points(
            selected_market=selected_market,
            data_quality=data_quality,
            scan_phase=scan_phase,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
            over_score=over_score,
            under_score=under_score,
            tactical_score=tactical_score,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
        )

        missing_points = self._build_missing_points(
            selected_market=selected_market,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            false_pressure_risk=false_pressure_risk,
            data_quality=data_quality,
            scan_phase=scan_phase,
        )

        why_selected = self._why_selected(
            selected_market=selected_market,
            master_status=master_status,
            master_rank=master_rank,
            master_confidence=master_confidence,
            over_score=over_score,
            under_score=under_score,
            support_points=support_points,
        )

        why_not_over = self._why_not_over(
            selected_market=selected_market,
            over_score=over_score,
            under_score=under_score,
            shots_on_target=shots_on_target,
            xg=xg,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            false_pressure_risk=false_pressure_risk,
            score_hold_probability=score_hold_probability,
        )

        why_not_under = self._why_not_under(
            selected_market=selected_market,
            over_score=over_score,
            under_score=under_score,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
        )

        logic_check = self._logic_check(
            selected_market=selected_market,
            master_status=master_status,
            master_rank=master_rank,
            data_quality=data_quality,
            scan_phase=scan_phase,
            stats_source=stats_source,
            shots=shots,
            shots_on_target=shots_on_target,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            over_score=over_score,
            under_score=under_score,
            offensive_volume_score=offensive_volume_score,
            tactical_score=tactical_score,
            false_pressure_risk=false_pressure_risk,
            risk_status=risk_status,
            risk_score=risk_score,
            contradiction_status=contradiction_status,
            contradiction_score=contradiction_score,
            warnings=warnings,
        )

        panel_message = self._panel_message(
            selected_market=selected_market,
            logic_status=logic_check["logic_status"],
            decision_valid=logic_check["decision_valid"],
            why_selected=why_selected,
            missing_points=missing_points,
        )

        return {
            "decision_explainer_version": "V17_EXPLAINER_1",
            "match_label": f"{home_team} vs {away_team}",
            "score_label": f"{home_score}-{away_score}",
            "minute": minute,

            "selected_market": selected_market,
            "master_status": master_status,
            "master_rank": master_rank,
            "master_confidence": round(master_confidence, 2),

            "logic_status": logic_check["logic_status"],
            "decision_valid": logic_check["decision_valid"],
            "recommended_demotion": logic_check["recommended_demotion"],
            "logic_warnings": logic_check["logic_warnings"],

            "why_selected": why_selected,
            "why_not_over": why_not_over,
            "why_not_under": why_not_under,
            "support_points": support_points,
            "missing_points": missing_points,

            "recommended_panel_message": panel_message,

            "explain_scores": {
                "over_score": round(over_score, 2),
                "under_score": round(under_score, 2),
                "market_confidence": round(market_confidence, 2),
                "tactical_score": round(tactical_score, 2),
                "offensive_volume_score": round(offensive_volume_score, 2),
                "offensive_depth_score": round(offensive_depth_score, 2),
                "false_pressure_risk": round(false_pressure_risk, 2),
                "risk_score": round(risk_score, 2),
                "contradiction_score": round(contradiction_score, 2),
            },
        }

    def _collect_warnings(
        self,
        match: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        master: Dict[str, Any],
    ) -> List[str]:
        warnings: List[str] = []

        for source in [
            match.get("risk_warnings", []),
            match.get("soft_warnings", []),
            tactical.get("tactical_warnings", []),
            market.get("market_warnings", []),
            risk.get("risk_warnings", []),
            risk.get("hard_blockers", []),
            contradiction.get("critical_contradictions", []),
            contradiction.get("contradiction_warnings", []),
            master.get("soft_warnings", []),
            master.get("hard_blockers", []),
        ]:
            if isinstance(source, list):
                warnings.extend(str(x) for x in source if x is not None)

        data_quality = str(match.get("data_quality") or "").upper()
        scan_phase = str(match.get("scan_phase") or "").upper()

        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)

        if data_quality == "LOW":
            warnings.append("LOW_STATS_DATA")

        if scan_phase in {"EARLY_OBSERVE", "WAITING_LIVE_STATS", "NOT_SCANNABLE_YET"}:
            warnings.append(scan_phase)

        if shots <= 0:
            warnings.append("NO_SHOTS_DATA")

        if shots_on_target <= 0:
            warnings.append("NO_SHOTS_ON_TARGET_DATA")

        if dangerous_attacks <= 0:
            warnings.append("NO_DANGEROUS_ATTACKS_DATA")

        return sorted(set(warnings))

    def _build_support_points(
        self,
        selected_market: str,
        data_quality: str,
        scan_phase: str,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
        over_score: float,
        under_score: float,
        tactical_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        under_transition_score: float,
    ) -> List[str]:
        points: List[str] = []

        if data_quality in {"MEDIUM", "HIGH"}:
            points.append(f"Calidad de datos {data_quality}.")

        if scan_phase == "SCANNABLE":
            points.append("El partido tiene datos suficientes para ser analizado.")

        if selected_market == "OVER":
            if over_score > under_score:
                points.append(f"OVER supera a UNDER por {over_score - under_score:.0f} puntos.")

            if offensive_volume_score >= 55:
                points.append("Existe volumen ofensivo real.")

            if offensive_depth_score >= 55:
                points.append("Hay profundidad ofensiva suficiente.")

            if pressure_score >= 60:
                points.append("La presión ofensiva acompaña la lectura.")

            if rhythm_score >= 60:
                points.append("El ritmo del partido sigue activo.")

            if goal_need_score >= 60:
                points.append("Existe necesidad de gol.")

            if shots_on_target >= 3:
                points.append("Hay tiros al arco que respaldan peligro real.")

            if xg >= 1.0:
                points.append("El xG respalda probabilidad ofensiva.")

        elif selected_market == "UNDER":
            if under_score > over_score:
                points.append(f"UNDER supera a OVER por {under_score - over_score:.0f} puntos.")

            if score_hold_probability >= 65:
                points.append("Alta probabilidad de conservación del marcador.")

            if under_transition_score >= 60:
                points.append("El partido muestra transición hacia cierre.")

            if offensive_volume_score <= 45:
                points.append("El volumen ofensivo es bajo.")

            if tactical_score <= 60:
                points.append("La actividad táctica ofensiva no es dominante.")

            if pressure_score <= 55:
                points.append("La presión ofensiva no es alta.")

        if shots > 0:
            points.append(f"Remates totales detectados: {shots:.0f}.")

        if shots_on_target > 0:
            points.append(f"Remates al arco detectados: {shots_on_target:.0f}.")

        if corners > 0:
            points.append(f"Tiros de esquina detectados: {corners:.0f}.")

        if dangerous_attacks > 0:
            points.append(f"Ataques peligrosos detectados: {dangerous_attacks:.0f}.")

        return points[:8]

    def _build_missing_points(
        self,
        selected_market: str,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        pressure_score: float,
        rhythm_score: float,
        false_pressure_risk: float,
        data_quality: str,
        scan_phase: str,
    ) -> List[str]:
        missing: List[str] = []

        if data_quality == "LOW":
            missing.append("Falta mejor calidad estadística.")

        if scan_phase != "SCANNABLE":
            missing.append("El partido todavía no está completamente escaneable.")

        if shots <= 0:
            missing.append("Faltan remates totales.")

        if shots_on_target <= 0:
            missing.append("Faltan remates al arco.")

        if dangerous_attacks <= 0:
            missing.append("Faltan ataques peligrosos.")

        if selected_market == "OVER":
            if offensive_volume_score < 50:
                missing.append("Falta volumen ofensivo para sostener OVER.")

            if offensive_depth_score < 50:
                missing.append("Falta profundidad ofensiva.")

            if pressure_score < 55:
                missing.append("Falta presión ofensiva sostenida.")

            if rhythm_score < 55:
                missing.append("Falta ritmo activo.")

            if false_pressure_risk >= 65:
                missing.append("Existe riesgo de presión falsa.")

        if selected_market == "UNDER":
            if offensive_volume_score > 58:
                missing.append("El volumen ofensivo es alto para una lectura UNDER segura.")

            if pressure_score > 75:
                missing.append("La presión ofensiva es alta para UNDER.")

            if shots_on_target >= 3:
                missing.append("Hay tiros al arco que aumentan riesgo para UNDER.")

            if xg >= 1.0:
                missing.append("El xG aumenta riesgo contra UNDER.")

        return missing[:8]

    def _why_selected(
        self,
        selected_market: str,
        master_status: str,
        master_rank: str,
        master_confidence: float,
        over_score: float,
        under_score: float,
        support_points: List[str],
    ) -> str:
        if selected_market == "OVER":
            base = (
                f"Se eligió OVER porque la lectura de mercado favorece el gol. "
                f"OVER marca {over_score:.0f} frente a UNDER {under_score:.0f}, "
                f"con decisión {master_status} y rango {master_rank}."
            )
        elif selected_market == "UNDER":
            base = (
                f"Se eligió UNDER porque la lectura favorece conservación del marcador. "
                f"UNDER marca {under_score:.0f} frente a OVER {over_score:.0f}, "
                f"con decisión {master_status} y rango {master_rank}."
            )
        else:
            base = (
                f"No se eligió mercado operativo claro. La decisión actual es {master_status} "
                f"con confianza {master_confidence:.0f}%."
            )

        if support_points:
            return base + " Respaldo principal: " + " ".join(support_points[:3])

        return base

    def _why_not_over(
        self,
        selected_market: str,
        over_score: float,
        under_score: float,
        shots_on_target: float,
        xg: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        pressure_score: float,
        rhythm_score: float,
        false_pressure_risk: float,
        score_hold_probability: float,
    ) -> str:
        if selected_market == "OVER":
            return "OVER sí fue elegido como lectura principal."

        reasons: List[str] = []

        if over_score <= under_score:
            reasons.append("OVER no supera a UNDER en la comparación de mercado.")

        if offensive_volume_score < 50:
            reasons.append("el volumen ofensivo no es suficiente")

        if offensive_depth_score < 50:
            reasons.append("falta profundidad ofensiva")

        if shots_on_target <= 1:
            reasons.append("hay pocos remates al arco")

        if xg < 0.8:
            reasons.append("el xG todavía es bajo")

        if pressure_score < 55:
            reasons.append("la presión no es sostenida")

        if rhythm_score < 55:
            reasons.append("el ritmo no acompaña")

        if false_pressure_risk >= 65:
            reasons.append("existe riesgo de presión falsa")

        if score_hold_probability >= 70:
            reasons.append("el partido muestra conservación del marcador")

        if not reasons:
            return "OVER no fue elegido porque la ventaja principal del partido se inclinó hacia otra lectura."

        return "OVER no fue elegido porque " + ", ".join(reasons[:5]) + "."

    def _why_not_under(
        self,
        selected_market: str,
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        pressure_score: float,
        rhythm_score: float,
        score_hold_probability: float,
        under_transition_score: float,
    ) -> str:
        if selected_market == "UNDER":
            return "UNDER sí fue elegido como lectura principal."

        reasons: List[str] = []

        if under_score <= over_score:
            reasons.append("UNDER no supera a OVER en la comparación de mercado")

        if offensive_volume_score >= 55:
            reasons.append("hay volumen ofensivo que aumenta riesgo contra UNDER")

        if offensive_depth_score >= 55:
            reasons.append("hay profundidad ofensiva")

        if pressure_score >= 65:
            reasons.append("la presión ofensiva es alta")

        if rhythm_score >= 65:
            reasons.append("el ritmo sigue activo")

        if score_hold_probability < 60:
            reasons.append("no hay suficiente conservación del marcador")

        if under_transition_score < 58:
            reasons.append("no hay transición clara hacia cierre")

        if not reasons:
            return "UNDER no fue elegido porque la ventaja principal del partido se inclinó hacia otra lectura."

        return "UNDER no fue elegido porque " + ", ".join(reasons[:5]) + "."

    def _logic_check(
        self,
        selected_market: str,
        master_status: str,
        master_rank: str,
        data_quality: str,
        scan_phase: str,
        stats_source: str,
        shots: float,
        shots_on_target: float,
        dangerous_attacks: float,
        xg: float,
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        tactical_score: float,
        false_pressure_risk: float,
        risk_status: str,
        risk_score: float,
        contradiction_status: str,
        contradiction_score: float,
        warnings: List[str],
    ) -> Dict[str, Any]:
        logic_warnings: List[str] = []

        decision_valid = True
        recommended_demotion = None

        operative = master_status in {"ENTER", "OPERABLE"}

        warning_set = {str(x).upper() for x in warnings}

        if operative and scan_phase in {"EARLY_OBSERVE", "WAITING_LIVE_STATS", "NOT_SCANNABLE_YET"}:
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("OPERATIVE_SIGNAL_WITH_NON_SCANNABLE_PHASE")

        if operative and data_quality == "LOW":
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("OPERATIVE_SIGNAL_WITH_LOW_DATA_QUALITY")

        if operative and self.CRITICAL_DATA_WARNINGS.intersection(warning_set):
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("OPERATIVE_SIGNAL_WITH_CRITICAL_DATA_WARNINGS")

        if operative and risk_status in {"HIGH_RISK", "EXTREME_RISK"}:
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("OPERATIVE_SIGNAL_WITH_HIGH_RISK")

        if operative and contradiction_status in {"STRONG_CONTRADICTION", "CRITICAL_CONTRADICTION"}:
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("OPERATIVE_SIGNAL_WITH_CONTRADICTION")

        if selected_market == "UNDER" and operative:
            if offensive_volume_score >= 60:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("UNDER_WITH_HIGH_OFFENSIVE_VOLUME")

            if under_score < over_score + 8:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("UNDER_EDGE_NOT_CLEAR")

            if shots_on_target >= 3 or xg >= 1.0:
                logic_warnings.append("UNDER_HAS_OFFENSIVE_RISK_AGAINST")

        if selected_market == "OVER" and operative:
            if offensive_volume_score < 42:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("OVER_WITH_LOW_OFFENSIVE_VOLUME")

            if false_pressure_risk >= 75:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("OVER_WITH_FALSE_PRESSURE_RISK")

        if decision_valid:
            logic_status = "COHERENT_SIGNAL" if operative else "COHERENT_OBSERVATION"
        else:
            logic_status = "SIGNAL_NEEDS_DEMOTION"

        return {
            "decision_valid": decision_valid,
            "logic_status": logic_status,
            "recommended_demotion": recommended_demotion,
            "logic_warnings": sorted(set(logic_warnings)),
        }

    def _panel_message(
        self,
        selected_market: str,
        logic_status: str,
        decision_valid: bool,
        why_selected: str,
        missing_points: List[str],
    ) -> str:
        if not decision_valid:
            if missing_points:
                return (
                    f"La lectura favorece {selected_market}, pero debe esperar confirmación. "
                    f"Falta: {missing_points[0]}"
                )

            return (
                f"La lectura favorece {selected_market}, pero la auditoría lógica recomienda esperar confirmación."
            )

        if selected_market in {"OVER", "UNDER"}:
            return why_selected

        if logic_status == "COHERENT_OBSERVATION":
            return "El partido tiene lectura parcial, pero todavía no muestra ventaja suficiente para operar."

        return "Sin ventaja clara de mercado."
