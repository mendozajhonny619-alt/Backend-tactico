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


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


class MatchMaturityAI:
    """
    Evalúa la madurez real de una señal V17.

    Objetivo:
    - Evitar que el sistema sea necio con UNDER temprano.
    - Separar panorama futbolístico de permiso de entrada.
    - Usar memoria previa + live + minuto + marcador + alternativa OVER.
    - No reemplaza MasterDecisionAI.
    - No reemplaza PanelDecisionAI.
    - Solo agrega una capa de madurez y revalidación.
    """

    VERSION = "V17_MATCH_MATURITY_AI_1"

    def evaluate(
        self,
        signal: Dict[str, Any],
        match_reader: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match_reader = match_reader or {}

        minute = self._minute(signal)
        total_goals = safe_int(signal.get("total_goals"), 0)

        market = str(
            signal.get("market")
            or signal.get("master_market")
            or signal.get("suggested_market")
            or "NO_BET"
        ).upper()

        football_dominant = str(
            signal.get("football_dominant_reading")
            or match_reader.get("football_dominant_reading")
            or market
            or ""
        ).upper()

        football_alternative = str(
            signal.get("football_alternative_reading")
            or match_reader.get("football_alternative_reading")
            or signal.get("alternative_label")
            or ""
        ).upper()

        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()
        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_support_score = safe_float(signal.get("over_support_score"), 0.0)
        over_score = safe_float(
            signal.get("over_score")
            or signal.get("result_over")
            or signal.get("over_probability")
            or signal.get("over_pre_match_score"),
            0.0,
        )
        under_score = safe_float(
            signal.get("under_score")
            or signal.get("result_under")
            or signal.get("under_probability")
            or signal.get("under_pre_match_score"),
            0.0,
        )

        league_goal_profile = str(signal.get("league_goal_profile") or "UNKNOWN_LEAGUE").upper()
        team_goal_profile = str(signal.get("team_goal_profile") or "UNKNOWN_TEAMS").upper()
        first_half_goal_risk = str(signal.get("first_half_goal_risk") or "UNKNOWN_FIRST_HALF_GOAL_RISK").upper()
        second_half_goal_risk = str(signal.get("second_half_goal_risk") or "UNKNOWN_SECOND_HALF_GOAL_RISK").upper()
        under_early_risk = str(signal.get("under_early_risk") or "UNKNOWN_UNDER_EARLY_RISK").upper()
        pre_match_behavior = str(signal.get("pre_match_recommended_behavior") or "").upper()

        game_phase = str(
            signal.get("football_game_phase")
            or match_reader.get("football_game_phase")
            or ""
        ).upper()

        game_state = str(
            signal.get("football_game_state")
            or match_reader.get("football_game_state")
            or ""
        ).upper()

        context_category = str(signal.get("context_category") or "").upper()
        risk_status = str(signal.get("risk_status") or "").upper()
        contradiction_status = str(signal.get("contradiction_status") or "").upper()
        data_quality = str(signal.get("data_quality") or "").upper()

        pressure = safe_float(
            signal.get("pressure")
            or signal.get("pressure_score")
            or signal.get("football_pressure")
            or 0,
            0.0,
        )
        shots = safe_int(signal.get("shots"), 0)
        shots_on_target = safe_int(signal.get("shots_on_target"), 0)
        corners = safe_int(signal.get("corners"), 0)
        dangerous_attacks = safe_int(signal.get("dangerous_attacks"), 0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0.0)

        maturity_score = 0.0
        warnings: List[str] = []
        support: List[str] = []

        phase = self._phase(minute)
        maturity_score += self._phase_base_score(phase)

        if data_quality in {"HIGH", "GOOD", "VALID"}:
            maturity_score += 10
            support.append("Datos live con calidad suficiente para interpretar la señal.")
        elif data_quality in {"LOW", "BAD", "INVALID"}:
            maturity_score -= 18
            warnings.append("Calidad de datos baja. No conviene elevar señal por marcador.")

        if contradiction_status in {"STRONG_CONTRADICTION", "CRITICAL_CONTRADICTION"}:
            maturity_score -= 35
            warnings.append("Contradicción fuerte o crítica. La señal debe esperar.")

        if risk_status in {"HIGH_RISK", "EXTREME_RISK", "ALTO", "EXTREMO"}:
            maturity_score -= 25
            warnings.append("Riesgo operativo elevado. Revalidación obligatoria.")

        live_volume_score = self._live_volume_score(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            pressure=pressure,
        )

        if live_volume_score >= 65:
            support.append("Volumen ofensivo live alto.")
        elif live_volume_score <= 18:
            support.append("Volumen ofensivo live bajo.")

        if market == "OVER" or football_dominant == "OVER":
            maturity_score += self._over_maturity_adjustment(
                minute=minute,
                phase=phase,
                total_goals=total_goals,
                live_volume_score=live_volume_score,
                league_goal_profile=league_goal_profile,
                team_goal_profile=team_goal_profile,
                first_half_goal_risk=first_half_goal_risk,
                second_half_goal_risk=second_half_goal_risk,
                over_support_score=over_support_score,
                over_score=over_score,
                warnings=warnings,
                support=support,
            )

        if market == "UNDER" or football_dominant == "UNDER" or football_dominant == "BAJO":
            maturity_score += self._under_maturity_adjustment(
                minute=minute,
                phase=phase,
                total_goals=total_goals,
                live_volume_score=live_volume_score,
                league_goal_profile=league_goal_profile,
                team_goal_profile=team_goal_profile,
                first_half_goal_risk=first_half_goal_risk,
                second_half_goal_risk=second_half_goal_risk,
                under_early_risk=under_early_risk,
                pre_match_behavior=pre_match_behavior,
                football_alternative=football_alternative,
                over_candidate_active=over_candidate_active,
                over_candidate_level=over_candidate_level,
                over_support_score=over_support_score,
                over_score=over_score,
                under_score=under_score,
                warnings=warnings,
                support=support,
            )

        maturity_score = clamp(maturity_score, 0, 100)

        maturity_level = self._maturity_level(maturity_score)
        entry_permission = self._entry_permission(
            maturity_score=maturity_score,
            warnings=warnings,
            market=market,
            football_dominant=football_dominant,
            phase=phase,
            minute=minute,
            total_goals=total_goals,
            under_early_risk=under_early_risk,
            over_candidate_active=over_candidate_active,
            over_candidate_level=over_candidate_level,
            league_goal_profile=league_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
        )

        corrected_rank = self._corrected_rank(
            original_rank=str(signal.get("master_rank") or signal.get("rank") or ""),
            entry_permission=entry_permission,
            maturity_level=maturity_level,
            market=market,
            football_dominant=football_dominant,
        )

        panel_label = self._panel_label(
            market=market,
            football_dominant=football_dominant,
            entry_permission=entry_permission,
            maturity_level=maturity_level,
            over_candidate_active=over_candidate_active,
            over_candidate_level=over_candidate_level,
        )

        panel_note = self._panel_note(
            entry_permission=entry_permission,
            market=market,
            football_dominant=football_dominant,
            warnings=warnings,
            support=support,
            phase=phase,
            minute=minute,
        )

        return {
            "match_maturity_version": self.VERSION,
            "match_maturity_phase": phase,
            "match_maturity_score": round(maturity_score, 2),
            "match_maturity_level": maturity_level,
            "match_maturity_entry_permission": entry_permission,
            "match_maturity_corrected_rank": corrected_rank,
            "match_maturity_panel_label": panel_label,
            "match_maturity_panel_note": panel_note,
            "match_maturity_live_volume_score": round(live_volume_score, 2),
            "match_maturity_support_points": support,
            "match_maturity_warnings": warnings,
            "match_maturity_should_demote": entry_permission in {
                "WAIT_REVALIDATION",
                "OBSERVE_ONLY",
                "BLOCK_ENTRY",
            },
            "match_maturity_no_strong_under": self._no_strong_under(
                market=market,
                football_dominant=football_dominant,
                phase=phase,
                total_goals=total_goals,
                under_early_risk=under_early_risk,
                over_candidate_active=over_candidate_active,
                over_candidate_level=over_candidate_level,
                league_goal_profile=league_goal_profile,
                first_half_goal_risk=first_half_goal_risk,
            ),
        }

    def _minute(self, signal: Dict[str, Any]) -> int:
        return safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("estimated_minute")
            or 0,
            0,
        )

    def _phase(self, minute: int) -> str:
        if minute <= 15:
            return "FIRST_HALF_RECOGNITION"
        if minute <= 25:
            return "FIRST_HALF_INITIAL_TREND"
        if minute <= 35:
            return "FIRST_HALF_PANORAMA"
        if minute <= 45:
            return "FIRST_HALF_DECISION_ZONE"
        if minute <= 55:
            return "SECOND_HALF_RESTART"
        if minute <= 70:
            return "SECOND_HALF_OVER_WINDOW"
        if minute <= 82:
            return "SECOND_HALF_CLOSING_WINDOW"
        return "LATE_GAME_CHAOS"

    def _phase_base_score(self, phase: str) -> float:
        values = {
            "FIRST_HALF_RECOGNITION": 18,
            "FIRST_HALF_INITIAL_TREND": 35,
            "FIRST_HALF_PANORAMA": 55,
            "FIRST_HALF_DECISION_ZONE": 70,
            "SECOND_HALF_RESTART": 45,
            "SECOND_HALF_OVER_WINDOW": 72,
            "SECOND_HALF_CLOSING_WINDOW": 76,
            "LATE_GAME_CHAOS": 42,
        }
        return values.get(phase, 35)

    def _live_volume_score(
        self,
        shots: int,
        shots_on_target: int,
        corners: int,
        dangerous_attacks: int,
        xg: float,
        pressure: float,
    ) -> float:
        score = 0.0
        score += clamp(shots * 2.2, 0, 28)
        score += clamp(shots_on_target * 7.5, 0, 30)
        score += clamp(corners * 3.5, 0, 16)
        score += clamp(dangerous_attacks * 0.45, 0, 18)
        score += clamp(xg * 28, 0, 26)
        score += clamp(pressure * 0.35, 0, 20)
        return clamp(score, 0, 100)

    def _over_maturity_adjustment(
        self,
        minute: int,
        phase: str,
        total_goals: int,
        live_volume_score: float,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        over_support_score: float,
        over_score: float,
        warnings: List[str],
        support: List[str],
    ) -> float:
        adj = 0.0

        if live_volume_score >= 60:
            adj += 18
            support.append("OVER tiene volumen live suficiente.")
        elif live_volume_score < 25:
            adj -= 18
            warnings.append("OVER sin volumen ofensivo suficiente.")

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            adj += 8
            support.append("Memoria previa de liga abierta favorece cautela contra UNDER.")

        if team_goal_profile in {"HIGH_GOAL_TEAMS", "OPEN_TEAMS"}:
            adj += 7
            support.append("Memoria previa de equipos con tendencia de gol.")

        if phase in {"FIRST_HALF_INITIAL_TREND", "FIRST_HALF_PANORAMA"}:
            if live_volume_score >= 65 and over_support_score >= 55:
                adj += 10
                support.append("OVER puede crecer temprano porque live y memoria previa coinciden.")
            else:
                adj -= 8
                warnings.append("OVER temprano requiere más confirmación.")

        if phase == "SECOND_HALF_OVER_WINDOW":
            adj += 10
            support.append("Ventana fuerte de segundo tiempo para buscar otro gol.")

        if total_goals >= 1 and minute <= 35 and live_volume_score >= 45:
            adj += 8
            support.append("Gol temprano más volumen posterior favorece ruptura OVER.")

        if over_score >= 75:
            adj += 8

        return adj

    def _under_maturity_adjustment(
        self,
        minute: int,
        phase: str,
        total_goals: int,
        live_volume_score: float,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        pre_match_behavior: str,
        football_alternative: str,
        over_candidate_active: bool,
        over_candidate_level: str,
        over_support_score: float,
        over_score: float,
        under_score: float,
        warnings: List[str],
        support: List[str],
    ) -> float:
        adj = 0.0

        if live_volume_score <= 20:
            adj += 12
            support.append("UNDER tiene respaldo live por bajo volumen ofensivo.")
        elif live_volume_score >= 55:
            adj -= 25
            warnings.append("UNDER contradicho por volumen ofensivo live.")

        if phase in {"FIRST_HALF_RECOGNITION", "FIRST_HALF_INITIAL_TREND"}:
            adj -= 20
            warnings.append("UNDER en primer tramo no debe subir fuerte todavía.")

        if phase == "FIRST_HALF_PANORAMA":
            adj -= 6
            support.append("Minuto de panorama. Puede existir lectura UNDER, pero todavía requiere confirmación.")

        if phase == "FIRST_HALF_DECISION_ZONE":
            if live_volume_score <= 25:
                adj += 12
                support.append("Zona final de primer tiempo con bajo volumen favorece UNDER HT.")
            else:
                adj -= 8
                warnings.append("Zona final del primer tiempo con volumen activo. Cuidado con gol antes del descanso.")

        if total_goals >= 1 and minute <= 35:
            adj -= 22
            warnings.append("Gol temprano antes del minuto 35. UNDER requiere revalidación.")

        if total_goals >= 1 and phase in {"FIRST_HALF_PANORAMA", "FIRST_HALF_DECISION_ZONE"}:
            adj -= 10
            warnings.append("Marcador ya abierto en primer tiempo. No elevar UNDER sin caída real del ritmo.")

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"} and minute <= 45:
            adj -= 18
            warnings.append("Liga abierta en primer tiempo. UNDER temprano no debe ser candidato fuerte sin confirmación extrema.")

        if first_half_goal_risk == "HIGH_FIRST_HALF_GOAL_RISK" and minute <= 45:
            adj -= 18
            warnings.append("Memoria previa advierte alto riesgo de gol en primer tiempo.")

        if under_early_risk == "HIGH_UNDER_EARLY_RISK" and minute <= 45:
            adj -= 22
            warnings.append("Memoria previa marca UNDER temprano peligroso.")

        if pre_match_behavior == "DO_NOT_PROMOTE_EARLY_UNDER_WITHOUT_LIVE_CONFIRMATION" and minute <= 45:
            adj -= 18
            warnings.append("Perfil prepartido exige no promover UNDER temprano sin confirmación live fuerte.")

        if over_candidate_active or "OVER" in football_alternative or "OVER" in over_candidate_level:
            if minute <= 70:
                adj -= 20
                warnings.append("Existe alternativa OVER WATCH activa. UNDER no debe ocultar riesgo de ruptura.")
            else:
                adj -= 8
                warnings.append("Existe alternativa OVER, aunque en fase tardía pesa menos.")

        if over_support_score >= 65 or over_score >= 70:
            adj -= 14
            warnings.append("Soporte OVER elevado. El UNDER necesita revalidación adicional.")

        if under_score >= 80 and live_volume_score <= 20 and total_goals == 0 and phase in {
            "FIRST_HALF_DECISION_ZONE",
            "SECOND_HALF_CLOSING_WINDOW",
        }:
            adj += 12
            support.append("UNDER alto con partido sin goles y bajo volumen en ventana adecuada.")

        if phase == "SECOND_HALF_CLOSING_WINDOW" and live_volume_score <= 30:
            adj += 16
            support.append("Ventana de cierre del segundo tiempo favorece UNDER si el ritmo cae.")

        if phase == "LATE_GAME_CHAOS":
            adj -= 12
            warnings.append("Tramo final caótico. Evitar confianza excesiva en UNDER.")

        return adj

    def _maturity_level(self, score: float) -> str:
        if score >= 82:
            return "VERY_MATURE"
        if score >= 70:
            return "MATURE"
        if score >= 55:
            return "PANORAMA_READY"
        if score >= 38:
            return "EARLY_OR_MIXED"
        return "IMMATURE"

    def _entry_permission(
        self,
        maturity_score: float,
        warnings: List[str],
        market: str,
        football_dominant: str,
        phase: str,
        minute: int,
        total_goals: int,
        under_early_risk: str,
        over_candidate_active: bool,
        over_candidate_level: str,
        league_goal_profile: str,
        first_half_goal_risk: str,
    ) -> str:
        if maturity_score < 38:
            return "OBSERVE_ONLY"

        if any("Contradicción" in w or "crítica" in w.lower() for w in warnings):
            return "BLOCK_ENTRY"

        is_under = market == "UNDER" or football_dominant in {"UNDER", "BAJO"}

        if is_under and minute <= 45:
            if under_early_risk == "HIGH_UNDER_EARLY_RISK":
                return "WAIT_REVALIDATION"

            if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"} and first_half_goal_risk in {
                "HIGH_FIRST_HALF_GOAL_RISK",
                "MEDIUM_FIRST_HALF_GOAL_RISK",
            }:
                return "WAIT_REVALIDATION"

            if total_goals >= 1 and minute <= 35:
                return "WAIT_REVALIDATION"

            if over_candidate_active or "OVER" in over_candidate_level:
                return "WAIT_REVALIDATION"

        if maturity_score >= 82:
            return "ALLOW_STRONG_SIGNAL"

        if maturity_score >= 70:
            return "ALLOW_CANDIDATE"

        if maturity_score >= 55:
            return "PANORAMA_ONLY"

        return "OBSERVE_ONLY"

    def _corrected_rank(
        self,
        original_rank: str,
        entry_permission: str,
        maturity_level: str,
        market: str,
        football_dominant: str,
    ) -> str:
        original_rank = original_rank.upper()

        if entry_permission == "ALLOW_STRONG_SIGNAL":
            return original_rank or "PREMIUM"

        if entry_permission == "ALLOW_CANDIDATE":
            if original_rank in {"PREMIUM", "TOP", "ELITE"}:
                return "CANDIDATE"
            return original_rank or "CANDIDATE"

        if entry_permission == "PANORAMA_ONLY":
            return "PANORAMA"

        if entry_permission == "WAIT_REVALIDATION":
            return "REVALIDATION"

        if entry_permission == "BLOCK_ENTRY":
            return "BLOCKED_BY_MATURITY"

        return "OBSERVATION"

    def _panel_label(
        self,
        market: str,
        football_dominant: str,
        entry_permission: str,
        maturity_level: str,
        over_candidate_active: bool,
        over_candidate_level: str,
    ) -> str:
        is_under = market == "UNDER" or football_dominant in {"UNDER", "BAJO"}
        is_over = market == "OVER" or football_dominant == "OVER"

        if entry_permission == "BLOCK_ENTRY":
            return "BLOQUEADO POR MADUREZ"

        if entry_permission == "WAIT_REVALIDATION":
            if is_under:
                return "UNDER EN REVALIDACIÓN"
            if is_over:
                return "OVER EN REVALIDACIÓN"
            return "PARTIDO EN REVALIDACIÓN"

        if entry_permission == "PANORAMA_ONLY":
            if is_under:
                return "PANORAMA UNDER"
            if is_over:
                return "PANORAMA OVER"
            return "PANORAMA"

        if entry_permission == "OBSERVE_ONLY":
            if over_candidate_active or "OVER" in over_candidate_level:
                return "OVER WATCH"
            return "OBSERVAR"

        if entry_permission == "ALLOW_CANDIDATE":
            if is_under:
                return "UNDER CANDIDATO"
            if is_over:
                return "OVER CANDIDATO"
            return "CANDIDATO"

        if entry_permission == "ALLOW_STRONG_SIGNAL":
            if is_under:
                return "UNDER FUERTE"
            if is_over:
                return "OVER FUERTE"
            return "SEÑAL FUERTE"

        return maturity_level

    def _panel_note(
        self,
        entry_permission: str,
        market: str,
        football_dominant: str,
        warnings: List[str],
        support: List[str],
        phase: str,
        minute: int,
    ) -> str:
        if entry_permission == "WAIT_REVALIDATION":
            reason = warnings[0] if warnings else "La señal todavía necesita confirmación."
            return f"Revalidación obligatoria en minuto {minute}. {reason}"

        if entry_permission == "PANORAMA_ONLY":
            return "El sistema ya tiene panorama futbolístico, pero todavía no autoriza entrada."

        if entry_permission == "OBSERVE_ONLY":
            reason = warnings[0] if warnings else "La señal aún no tiene madurez suficiente."
            return f"Solo observación. {reason}"

        if entry_permission == "BLOCK_ENTRY":
            reason = warnings[0] if warnings else "Condición crítica activa."
            return f"Entrada bloqueada. {reason}"

        if entry_permission in {"ALLOW_CANDIDATE", "ALLOW_STRONG_SIGNAL"}:
            reason = support[0] if support else "La lectura live y el contexto permiten elevar la señal."
            return reason

        return f"Fase {phase}. Lectura en evaluación."

    def _no_strong_under(
        self,
        market: str,
        football_dominant: str,
        phase: str,
        total_goals: int,
        under_early_risk: str,
        over_candidate_active: bool,
        over_candidate_level: str,
        league_goal_profile: str,
        first_half_goal_risk: str,
    ) -> bool:
        is_under = market == "UNDER" or football_dominant in {"UNDER", "BAJO"}

        if not is_under:
            return False

        if phase in {"FIRST_HALF_RECOGNITION", "FIRST_HALF_INITIAL_TREND"}:
            return True

        if under_early_risk == "HIGH_UNDER_EARLY_RISK":
            return True

        if over_candidate_active or "OVER" in over_candidate_level:
            return True

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"} and first_half_goal_risk in {
            "HIGH_FIRST_HALF_GOAL_RISK",
            "MEDIUM_FIRST_HALF_GOAL_RISK",
        }:
            return True

        if total_goals >= 1 and phase in {"FIRST_HALF_PANORAMA", "FIRST_HALF_DECISION_ZONE"}:
            return True

        return False
