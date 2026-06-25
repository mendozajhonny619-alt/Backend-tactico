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

    Versión con lógica de mayoría.

    Principio:
    - No publicar señales malas.
    - No ocultar buenos candidatos.
    - Si cumple la mayoría de filtros y solo faltan 1 o 2 elementos no críticos,
      puede subir como candidato fuerte u observación alta.
    - Si falla reloj crítico, contradicción crítica o riesgo extremo real,
      no puede subir.
    """

    CRITICAL_CLOCK_WARNINGS = {
        "CLOCK_FROZEN",
        "CLOCK_STALE",
        "MINUTE_LAG_DETECTED",
        "BLOCKED_CLOCK",
        "CLOCK_CRITICAL",
    }

    DATA_WARNINGS = {
        "LOW_STATS_DATA",
        "NO_SHOTS_DATA",
        "NO_SHOTS_ON_TARGET_DATA",
        "NO_DANGEROUS_ATTACKS_DATA",
        "NO_LIVE_STATS",
        "LOW_DATA_QUALITY",
    }

    CRITICAL_CONTRADICTIONS = {
        "STRONG_CONTRADICTION",
        "CRITICAL_CONTRADICTION",
    }

    CRITICAL_RISKS = {
        "EXTREME_RISK",
    }

    HIGH_RISKS = {
        "HIGH_RISK",
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
            minute=minute,
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
            minute=minute,
        )

        logic_check = self._logic_check(
            selected_market=selected_market,
            master_status=master_status,
            master_rank=master_rank,
            data_quality=data_quality,
            scan_phase=scan_phase,
            stats_source=stats_source,
            minute=minute,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            over_score=over_score,
            under_score=under_score,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            tactical_score=tactical_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
            false_pressure_risk=false_pressure_risk,
            risk_status=risk_status,
            risk_score=risk_score,
            contradiction_status=contradiction_status,
            contradiction_score=contradiction_score,
            warnings=warnings,
        )

        why_selected = self._why_selected(
            selected_market=selected_market,
            master_status=master_status,
            master_rank=master_rank,
            master_confidence=master_confidence,
            over_score=over_score,
            under_score=under_score,
            support_points=support_points,
            logic_level=logic_check["candidate_level"],
            majority_support=logic_check["majority_support"],
            support_score=logic_check["support_score"],
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

        panel_message = self._panel_message(
            selected_market=selected_market,
            logic_status=logic_check["logic_status"],
            candidate_level=logic_check["candidate_level"],
            decision_valid=logic_check["decision_valid"],
            why_selected=why_selected,
            missing_points=missing_points,
            majority_support=logic_check["majority_support"],
            support_score=logic_check["support_score"],
        )

        return {
            "decision_explainer_version": "V17_EXPLAINER_3_MAJORITY_SUPPORT",
            "match_label": f"{home_team} vs {away_team}",
            "score_label": f"{home_score}-{away_score}",
            "minute": minute,

            "selected_market": selected_market,
            "master_status": master_status,
            "master_rank": master_rank,
            "master_confidence": round(master_confidence, 2),

            "logic_status": logic_check["logic_status"],
            "candidate_level": logic_check["candidate_level"],
            "decision_valid": logic_check["decision_valid"],
            "recommended_demotion": logic_check["recommended_demotion"],
            "logic_warnings": logic_check["logic_warnings"],

            "majority_support": logic_check["majority_support"],
            "support_score": logic_check["support_score"],
            "support_ratio": logic_check["support_ratio"],
            "non_critical_missing_count": logic_check["non_critical_missing_count"],
            "critical_block": logic_check["critical_block"],

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
                "pressure_score": round(pressure_score, 2),
                "rhythm_score": round(rhythm_score, 2),
                "goal_need_score": round(goal_need_score, 2),
                "score_hold_probability": round(score_hold_probability, 2),
                "under_transition_score": round(under_transition_score, 2),
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
        minute: int,
    ) -> List[str]:
        points: List[str] = []

        if data_quality in {"MEDIUM", "HIGH"}:
            points.append(f"Calidad de datos {data_quality}.")

        if scan_phase == "SCANNABLE":
            points.append("El partido tiene datos suficientes para ser analizado.")

        if minute >= 70:
            points.append("Minuto avanzado, aumenta el valor de lectura contextual.")

        if selected_market == "OVER":
            if over_score > under_score:
                points.append(f"OVER supera a UNDER por {over_score - under_score:.0f} puntos.")

            if offensive_volume_score >= 48:
                points.append("Existe volumen ofensivo real.")

            if offensive_depth_score >= 45:
                points.append("Hay profundidad ofensiva suficiente.")

            if pressure_score >= 52:
                points.append("La presión ofensiva acompaña la lectura.")

            if rhythm_score >= 50:
                points.append("El ritmo del partido sigue activo.")

            if goal_need_score >= 58:
                points.append("Existe necesidad de gol.")

            if shots_on_target >= 2:
                points.append("Hay tiros al arco que respaldan peligro real.")

            if corners >= 4:
                points.append("Los tiros de esquina respaldan actividad ofensiva.")

            if xg >= 0.75:
                points.append("El xG respalda probabilidad ofensiva.")

        elif selected_market == "UNDER":
            if under_score > over_score:
                points.append(f"UNDER supera a OVER por {under_score - over_score:.0f} puntos.")

            if score_hold_probability >= 65:
                points.append("Alta probabilidad de conservación del marcador.")

            if under_transition_score >= 60:
                points.append("El partido muestra transición hacia cierre.")

            if offensive_volume_score <= 55:
                points.append("El volumen ofensivo no amenaza la lectura UNDER.")

            if tactical_score <= 65:
                points.append("La actividad táctica ofensiva no es dominante.")

            if pressure_score <= 65:
                points.append("La presión ofensiva no es alta.")

        if shots > 0:
            points.append(f"Remates totales detectados: {shots:.0f}.")

        if shots_on_target > 0:
            points.append(f"Remates al arco detectados: {shots_on_target:.0f}.")

        if corners > 0:
            points.append(f"Tiros de esquina detectados: {corners:.0f}.")

        if dangerous_attacks > 0:
            points.append(f"Ataques peligrosos detectados: {dangerous_attacks:.0f}.")

        return points[:9]

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
        minute: int,
    ) -> List[str]:
        missing: List[str] = []

        late_match = minute >= 70

        if data_quality == "LOW":
            if late_match:
                missing.append("Fuente estadística limitada, pero el minuto avanzado permite lectura cautelosa.")
            else:
                missing.append("Falta mejor calidad estadística.")

        if scan_phase != "SCANNABLE":
            if late_match:
                missing.append("El partido tiene datos parciales, lectura solo como candidato.")
            else:
                missing.append("El partido todavía no está completamente escaneable.")

        if shots <= 0 and not late_match:
            missing.append("Faltan remates totales.")

        if shots_on_target <= 0 and not late_match:
            missing.append("Faltan remates al arco.")

        if dangerous_attacks <= 0 and not late_match:
            missing.append("Faltan ataques peligrosos.")

        if selected_market == "OVER":
            if offensive_volume_score < 45:
                missing.append("Falta volumen ofensivo para sostener OVER.")

            if offensive_depth_score < 42:
                missing.append("Falta profundidad ofensiva.")

            if pressure_score < 50:
                missing.append("Falta presión ofensiva sostenida.")

            if rhythm_score < 48:
                missing.append("Falta ritmo activo.")

            if false_pressure_risk >= 68:
                missing.append("Existe riesgo de presión falsa.")

        if selected_market == "UNDER":
            if offensive_volume_score > 65:
                missing.append("El volumen ofensivo es alto para una lectura UNDER segura.")

            if pressure_score > 82:
                missing.append("La presión ofensiva es alta para UNDER.")

            if shots_on_target >= 4:
                missing.append("Hay tiros al arco que aumentan riesgo para UNDER.")

            if xg >= 1.25:
                missing.append("El xG aumenta riesgo contra UNDER.")

        return missing[:8]

    def _majority_support_check(
        self,
        selected_market: str,
        minute: int,
        data_quality: str,
        scan_phase: str,
        market_edge: float,
        over_score: float,
        under_score: float,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        tactical_score: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        under_transition_score: float,
        false_pressure_risk: float,
        risk_status: str,
        contradiction_status: str,
        has_data_warning: bool,
    ) -> Dict[str, Any]:
        checks: List[bool] = []

        data_ok = data_quality in {"MEDIUM", "HIGH"} or scan_phase == "SCANNABLE" or minute >= 70
        risk_ok = risk_status not in {"EXTREME_RISK", "HIGH_RISK"} or minute >= 75
        contradiction_ok = contradiction_status not in self.CRITICAL_CONTRADICTIONS

        checks.append(data_ok)
        checks.append(risk_ok)
        checks.append(contradiction_ok)

        if selected_market == "UNDER":
            checks.extend([
                under_score >= 65,
                market_edge >= 8,
                score_hold_probability >= 65,
                under_transition_score >= 58,
                offensive_volume_score <= 60,
                pressure_score <= 75,
                tactical_score <= 70,
                shots_on_target < 4,
                xg < 1.25,
            ])

        elif selected_market == "OVER":
            offensive_activity = (
                shots >= 5
                or shots_on_target >= 2
                or corners >= 4
                or dangerous_attacks >= 10
                or xg >= 0.70
                or offensive_volume_score >= 48
                or pressure_score >= 52
            )

            checks.extend([
                over_score >= 58,
                market_edge >= 6,
                offensive_activity,
                offensive_volume_score >= 45,
                offensive_depth_score >= 42,
                pressure_score >= 50,
                rhythm_score >= 48,
                goal_need_score >= 50,
                false_pressure_risk < 72,
            ])

        else:
            return {
                "majority_support": False,
                "support_score": 0,
                "support_total": 0,
                "support_ratio": 0,
                "non_critical_missing_count": 99,
            }

        support_score = sum(1 for x in checks if x)
        support_total = len(checks)
        support_ratio = support_score / support_total if support_total else 0.0

        non_critical_missing_count = support_total - support_score

        if has_data_warning and minute < 20:
            majority_support = False
        else:
            majority_support = support_ratio >= 0.68

        return {
            "majority_support": majority_support,
            "support_score": support_score,
            "support_total": support_total,
            "support_ratio": round(support_ratio, 3),
            "non_critical_missing_count": non_critical_missing_count,
        }

    def _why_selected(
        self,
        selected_market: str,
        master_status: str,
        master_rank: str,
        master_confidence: float,
        over_score: float,
        under_score: float,
        support_points: List[str],
        logic_level: str,
        majority_support: bool,
        support_score: int,
    ) -> str:
        level_text = {
            "TOP_SIGNAL": "señal fuerte",
            "STRONG_CANDIDATE": "candidato fuerte",
            "HIGH_OBSERVATION": "observación alta",
            "NORMAL_OBSERVATION": "observación normal",
            "NO_BET": "sin ventaja operativa",
            "TECHNICAL_BLOCK": "bloqueo técnico",
        }.get(logic_level, "lectura en evaluación")

        majority_text = ""
        if majority_support:
            majority_text = f" Cumple mayoría de filtros con soporte {support_score}."

        if selected_market == "OVER":
            base = (
                f"Se eligió OVER como {level_text} porque la lectura favorece el gol. "
                f"OVER marca {over_score:.0f} frente a UNDER {under_score:.0f}, "
                f"con decisión {master_status} y rango {master_rank}."
            )
        elif selected_market == "UNDER":
            base = (
                f"Se eligió UNDER como {level_text} porque la lectura favorece conservación del marcador. "
                f"UNDER marca {under_score:.0f} frente a OVER {over_score:.0f}, "
                f"con decisión {master_status} y rango {master_rank}."
            )
        else:
            base = (
                f"No se eligió mercado operativo claro. La decisión actual es {master_status} "
                f"con confianza {master_confidence:.0f}%."
            )

        if support_points:
            return base + majority_text + " Respaldo principal: " + " ".join(support_points[:3])

        return base + majority_text

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
            reasons.append("OVER no supera a UNDER en la comparación de mercado")

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
        minute: int,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        over_score: float,
        under_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        tactical_score: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        under_transition_score: float,
        false_pressure_risk: float,
        risk_status: str,
        risk_score: float,
        contradiction_status: str,
        contradiction_score: float,
        warnings: List[str],
    ) -> Dict[str, Any]:
        logic_warnings: List[str] = []

        operative = master_status in {"ENTER", "OPERABLE"}
        warning_set = {str(x).upper() for x in warnings}

        has_clock_problem = bool(self.CRITICAL_CLOCK_WARNINGS.intersection(warning_set))
        has_data_warning = bool(self.DATA_WARNINGS.intersection(warning_set))
        has_critical_contradiction = contradiction_status in self.CRITICAL_CONTRADICTIONS
        has_extreme_risk = risk_status in self.CRITICAL_RISKS

        market_edge = 0.0
        if selected_market == "OVER":
            market_edge = over_score - under_score
        elif selected_market == "UNDER":
            market_edge = under_score - over_score

        majority = self._majority_support_check(
            selected_market=selected_market,
            minute=minute,
            data_quality=data_quality,
            scan_phase=scan_phase,
            market_edge=market_edge,
            over_score=over_score,
            under_score=under_score,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            tactical_score=tactical_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            under_transition_score=under_transition_score,
            false_pressure_risk=false_pressure_risk,
            risk_status=risk_status,
            contradiction_status=contradiction_status,
            has_data_warning=has_data_warning,
        )

        majority_support = bool(majority["majority_support"])
        support_score = int(majority["support_score"])
        support_ratio = float(majority["support_ratio"])
        non_critical_missing_count = int(majority["non_critical_missing_count"])

        critical_block = False
        decision_valid = True
        recommended_demotion = None

        if has_clock_problem:
            critical_block = True
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("CLOCK_PROBLEM_FORCE_CONFIRMATION")

        if has_critical_contradiction:
            critical_block = True
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("CONTRADICTION_FORCE_CONFIRMATION")

        if has_extreme_risk and minute < 80:
            critical_block = True
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("EXTREME_RISK_FORCE_CONFIRMATION")

        if selected_market == "UNDER":
            if offensive_volume_score >= 70 or pressure_score >= 86 or shots_on_target >= 5 or xg >= 1.45:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("UNDER_WITH_REAL_ATTACK_RISK")

            if market_edge < 6:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("UNDER_EDGE_NOT_CLEAR")

        if selected_market == "OVER":
            if false_pressure_risk >= 78:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("OVER_WITH_FALSE_PRESSURE_RISK")

            offensive_evidence = (
                shots >= 5
                or shots_on_target >= 2
                or corners >= 4
                or dangerous_attacks >= 10
                or xg >= 0.70
                or offensive_volume_score >= 48
                or pressure_score >= 52
            )

            if not offensive_evidence and not majority_support:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("OVER_WITHOUT_OFFENSIVE_EVIDENCE")

            if market_edge < 5:
                decision_valid = False
                recommended_demotion = "WAIT_CONFIRMATION"
                logic_warnings.append("OVER_EDGE_NOT_CLEAR")

        if has_data_warning and minute < 15:
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("VERY_EARLY_MATCH_WITH_LOW_DATA")

        if has_data_warning and not majority_support and not critical_block:
            decision_valid = False
            recommended_demotion = "WAIT_CONFIRMATION"
            logic_warnings.append("LOW_DATA_WITHOUT_MAJORITY_SUPPORT")

        if has_data_warning and majority_support and not critical_block:
            logic_warnings.append("LOW_DATA_BUT_MAJORITY_SUPPORT")

        candidate_level = self._candidate_level(
            selected_market=selected_market,
            operative=operative,
            decision_valid=decision_valid,
            minute=minute,
            has_data_warning=has_data_warning,
            has_clock_problem=has_clock_problem,
            critical_block=critical_block,
            market_edge=market_edge,
            over_score=over_score,
            under_score=under_score,
            majority_support=majority_support,
            support_ratio=support_ratio,
            non_critical_missing_count=non_critical_missing_count,
            master_rank=master_rank,
            risk_status=risk_status,
        )

        if critical_block:
            logic_status = "TECHNICAL_BLOCK"
        elif decision_valid and operative:
            logic_status = "COHERENT_SIGNAL"
        elif decision_valid and candidate_level in {"STRONG_CANDIDATE", "HIGH_OBSERVATION"}:
            logic_status = "COHERENT_CANDIDATE"
        elif decision_valid:
            logic_status = "COHERENT_OBSERVATION"
        else:
            logic_status = "SIGNAL_NEEDS_CONFIRMATION"

        return {
            "decision_valid": decision_valid,
            "logic_status": logic_status,
            "candidate_level": candidate_level,
            "recommended_demotion": recommended_demotion,
            "logic_warnings": sorted(set(logic_warnings)),
            "majority_support": majority_support,
            "support_score": support_score,
            "support_ratio": support_ratio,
            "non_critical_missing_count": non_critical_missing_count,
            "critical_block": critical_block,
        }

    def _candidate_level(
        self,
        selected_market: str,
        operative: bool,
        decision_valid: bool,
        minute: int,
        has_data_warning: bool,
        has_clock_problem: bool,
        critical_block: bool,
        market_edge: float,
        over_score: float,
        under_score: float,
        majority_support: bool,
        support_ratio: float,
        non_critical_missing_count: int,
        master_rank: str,
        risk_status: str,
    ) -> str:
        if selected_market not in {"OVER", "UNDER"}:
            return "NO_BET"

        if critical_block or has_clock_problem:
            return "TECHNICAL_BLOCK"

        if risk_status in {"EXTREME_RISK", "HIGH_RISK"} and minute < 75:
            return "NORMAL_OBSERVATION"

        if operative and decision_valid and not has_data_warning:
            if master_rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"} and support_ratio >= 0.78:
                return "TOP_SIGNAL"

        if majority_support:
            if support_ratio >= 0.80 and non_critical_missing_count <= 2:
                return "STRONG_CANDIDATE"

            if support_ratio >= 0.68 and non_critical_missing_count <= 4:
                return "HIGH_OBSERVATION"

        if selected_market == "UNDER":
            if under_score >= 70 and market_edge >= 10:
                return "HIGH_OBSERVATION"

        if selected_market == "OVER":
            if over_score >= 60 and market_edge >= 6:
                return "HIGH_OBSERVATION"

        return "NORMAL_OBSERVATION"

    def _panel_message(
        self,
        selected_market: str,
        logic_status: str,
        candidate_level: str,
        decision_valid: bool,
        why_selected: str,
        missing_points: List[str],
        majority_support: bool,
        support_score: int,
    ) -> str:
        if candidate_level == "TECHNICAL_BLOCK":
            return (
                f"La lectura favorece {selected_market}, pero existe bloqueo técnico. "
                "Debe esperar confirmación de reloj, datos o contradicción."
            )

        if candidate_level == "TOP_SIGNAL":
            return why_selected

        if candidate_level == "STRONG_CANDIDATE":
            if missing_points:
                return (
                    f"La lectura favorece {selected_market} como candidato fuerte. "
                    f"Cumple mayoría de filtros con soporte {support_score}. "
                    f"Falta no crítica: {missing_points[0]}"
                )

            return (
                f"La lectura favorece {selected_market} como candidato fuerte. "
                f"Cumple mayoría de filtros con soporte {support_score}."
            )

        if candidate_level == "HIGH_OBSERVATION":
            if majority_support:
                return (
                    f"La lectura favorece {selected_market} y cumple mayoría de filtros, "
                    "pero aún requiere confirmación antes de subir a señal principal."
                )

            if missing_points:
                return (
                    f"La lectura favorece {selected_market}, pero sigue en observación alta. "
                    f"Falta: {missing_points[0]}"
                )

            return (
                f"La lectura favorece {selected_market}, pero todavía no alcanza nivel operativo."
            )

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
