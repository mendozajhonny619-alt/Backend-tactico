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


def normalize_text(value: Any) -> str:
    return str(value or "").upper().strip()


class LeagueVolatilityAI:
    """
    Ajustador de volatilidad por liga para V17.

    Objetivo:
    - Recuperar la lectura especial que V16 intentaba hacer con CONMEBOL.
    - No bloquear señales automáticamente.
    - Ajustar la confianza visual según liga, minuto, fase del partido y lectura OVER/UNDER.
    - Entender que Libertadores, Sudamericana y ligas sudamericanas pueden cambiar rápido.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        over_candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        league = normalize_text(match.get("league") or match.get("league_name"))
        country = normalize_text(match.get("country"))
        minute = safe_int(
            match.get("api_minute")
            or match.get("display_minute")
            or match.get("minute"),
            0,
        )

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score
        goal_gap = abs(home_score - away_score)

        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        corners = safe_float(match.get("corners"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        market_gap = over_score - under_score

        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)

        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)

        risk_status = normalize_text(risk.get("risk_status"))
        data_quality = normalize_text(match.get("data_quality"))
        clock_status = normalize_text(match.get("clock_status"))
        scan_phase = normalize_text(match.get("scan_phase"))

        league_group = self._league_group(league=league, country=country)
        minute_phase = self._minute_phase(minute)
        half_context = "FIRST_HALF" if minute <= 45 else "SECOND_HALF"

        real_volume = self._real_volume(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
        )

        conmebol_profile = self._conmebol_profile(
            league_group=league_group,
            minute=minute,
            minute_phase=minute_phase,
            half_context=half_context,
            total_goals=total_goals,
            goal_gap=goal_gap,
            real_volume=real_volume,
            over_score=over_score,
            under_score=under_score,
            market_gap=market_gap,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            recent_attack_proxy=recent_attack_proxy,
            false_pressure_risk=false_pressure_risk,
            risk_status=risk_status,
            data_quality=data_quality,
            clock_status=clock_status,
            scan_phase=scan_phase,
            over_candidate=over_candidate,
        )

        return {
            "league_volatility_version": "V17_LEAGUE_VOLATILITY_1",
            "league_context_group": league_group,
            "league_volatility_level": conmebol_profile["volatility_level"],
            "league_half_context": half_context,
            "league_minute_phase": minute_phase,
            "league_panel_modifier": conmebol_profile["panel_modifier"],
            "league_confidence_adjustment": conmebol_profile["confidence_adjustment"],
            "league_publish_modifier": conmebol_profile["publish_modifier"],
            "league_revalidation_required": conmebol_profile["revalidation_required"],
            "league_warning": conmebol_profile["warning"],
            "league_late_game_reading": conmebol_profile["late_game_reading"],
            "league_first_half_reading": conmebol_profile["first_half_reading"],
            "league_over_permission": conmebol_profile["over_permission"],
            "league_under_permission": conmebol_profile["under_permission"],
            "league_reason": conmebol_profile["reason"],
            "league_support_points": conmebol_profile["support_points"],
            "league_caution_points": conmebol_profile["caution_points"],
        }

    def _league_group(self, league: str, country: str) -> str:
        conmebol_keywords = [
            "LIBERTADORES",
            "SUDAMERICANA",
            "RECOPA",
            "CONMEBOL",
        ]

        conmebol_countries = [
            "ARGENTINA",
            "BOLIVIA",
            "BRAZIL",
            "BRASIL",
            "CHILE",
            "COLOMBIA",
            "ECUADOR",
            "PARAGUAY",
            "PERU",
            "PERÚ",
            "URUGUAY",
            "VENEZUELA",
        ]

        for word in conmebol_keywords:
            if word in league:
                return "CONMEBOL"

        for country_name in conmebol_countries:
            if country_name in country:
                return "SOUTH_AMERICA"

        return "STANDARD"

    def _minute_phase(self, minute: int) -> str:
        if minute <= 15:
            return "00_15_INITIAL_READING"

        if minute <= 30:
            return "15_30_GROWTH_WINDOW"

        if minute <= 45:
            return "30_45_PRE_HALFTIME_PUSH"

        if minute <= 60:
            return "45_60_SECOND_HALF_START"

        if minute <= 75:
            return "60_75_REVALIDATION_WINDOW"

        if minute <= 85:
            return "75_85_CLOSING_DECISION"

        return "85_90_FINAL_VOLATILITY"

    def _real_volume(
        self,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
    ) -> bool:
        return (
            shots >= 10
            or shots_on_target >= 3
            or corners >= 5
            or dangerous_attacks >= 15
            or xg >= 0.85
            or (
                offensive_volume_score >= 55
                and offensive_depth_score >= 48
            )
        )

    def _conmebol_profile(
        self,
        league_group: str,
        minute: int,
        minute_phase: str,
        half_context: str,
        total_goals: int,
        goal_gap: int,
        real_volume: bool,
        over_score: float,
        under_score: float,
        market_gap: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        recent_attack_proxy: float,
        false_pressure_risk: float,
        risk_status: str,
        data_quality: str,
        clock_status: str,
        scan_phase: str,
        over_candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        if league_group not in {"CONMEBOL", "SOUTH_AMERICA"}:
            return self._standard_profile()

        support_points: List[str] = []
        caution_points: List[str] = []

        volatility_level = "MEDIUM_HIGH"
        panel_modifier = "SHOW_CONTEXT"
        confidence_adjustment = 0
        publish_modifier = "NORMAL"
        revalidation_required = True
        warning = "CONMEBOL_CONTEXT_REQUIRES_DYNAMIC_READING"
        late_game_reading = ""
        first_half_reading = ""
        over_permission = "ALLOW_IF_CONFIRMED"
        under_permission = "ALLOW_IF_CONFIRMED"

        if league_group == "CONMEBOL":
            volatility_level = "HIGH"
            confidence_adjustment -= 4
            caution_points.append("Torneo CONMEBOL con alta volatilidad táctica y emocional.")
        else:
            volatility_level = "MEDIUM_HIGH"
            confidence_adjustment -= 2
            caution_points.append("Liga sudamericana con posible variabilidad de ritmo.")

        if data_quality == "LOW" or scan_phase == "WAITING_LIVE_STATS":
            confidence_adjustment -= 4
            panel_modifier = "SHOW_AS_CANDIDATE"
            publish_modifier = "LIMIT_DIRECT_TOP"
            caution_points.append("Datos estadísticos limitados, requiere confirmación visual o de volumen.")

        if clock_status in {"CLOCK_WARNING", "STALE_CLOCK", "CLOCK_STALE_WARNING"}:
            confidence_adjustment -= 4
            panel_modifier = "SHOW_AS_CANDIDATE"
            publish_modifier = "LIMIT_DIRECT_TOP"
            caution_points.append("Reloj con advertencia, evitar entrada automática.")

        if risk_status in {"HIGH_RISK", "EXTREME_RISK"}:
            confidence_adjustment -= 8
            panel_modifier = "SHOW_AS_OBSERVATION"
            publish_modifier = "NO_DIRECT_TOP"
            caution_points.append("Riesgo alto para operar directamente.")

        if false_pressure_risk >= 75:
            confidence_adjustment -= 5
            panel_modifier = "SHOW_AS_OBSERVATION"
            caution_points.append("Posible presión falsa, especialmente sensible en CONMEBOL.")

        if half_context == "FIRST_HALF":
            first_half = self._first_half_profile(
                minute=minute,
                minute_phase=minute_phase,
                real_volume=real_volume,
                total_goals=total_goals,
                goal_gap=goal_gap,
                over_score=over_score,
                under_score=under_score,
                market_gap=market_gap,
                pressure_score=pressure_score,
                rhythm_score=rhythm_score,
                goal_need_score=goal_need_score,
                score_hold_probability=score_hold_probability,
                offensive_volume_score=offensive_volume_score,
                offensive_depth_score=offensive_depth_score,
                recent_attack_proxy=recent_attack_proxy,
            )

            first_half_reading = first_half["reading"]
            support_points.extend(first_half["support_points"])
            caution_points.extend(first_half["caution_points"])
            confidence_adjustment += first_half["confidence_adjustment"]
            panel_modifier = self._stronger_panel_modifier(panel_modifier, first_half["panel_modifier"])
            publish_modifier = self._stricter_publish_modifier(publish_modifier, first_half["publish_modifier"])
            over_permission = first_half["over_permission"]
            under_permission = first_half["under_permission"]

        else:
            second_half = self._second_half_profile(
                minute=minute,
                minute_phase=minute_phase,
                real_volume=real_volume,
                total_goals=total_goals,
                goal_gap=goal_gap,
                over_score=over_score,
                under_score=under_score,
                market_gap=market_gap,
                pressure_score=pressure_score,
                rhythm_score=rhythm_score,
                goal_need_score=goal_need_score,
                score_hold_probability=score_hold_probability,
                offensive_volume_score=offensive_volume_score,
                offensive_depth_score=offensive_depth_score,
                recent_attack_proxy=recent_attack_proxy,
                over_candidate=over_candidate,
            )

            late_game_reading = second_half["reading"]
            support_points.extend(second_half["support_points"])
            caution_points.extend(second_half["caution_points"])
            confidence_adjustment += second_half["confidence_adjustment"]
            panel_modifier = self._stronger_panel_modifier(panel_modifier, second_half["panel_modifier"])
            publish_modifier = self._stricter_publish_modifier(publish_modifier, second_half["publish_modifier"])
            over_permission = second_half["over_permission"]
            under_permission = second_half["under_permission"]

        if real_volume:
            support_points.append("Existe volumen ofensivo real, no ocultar lectura OVER.")
            if over_permission != "BLOCK":
                over_permission = "ALLOW_AS_CANDIDATE"

        if score_hold_probability >= 78 and not real_volume and minute >= 70:
            support_points.append("Fase de cierre compatible con UNDER en conservación.")
            under_permission = "ALLOW_AS_CANDIDATE"
            late_game_reading = late_game_reading or "UNDER_CLOSING_PHASE"

        reason = self._build_reason(
            league_group=league_group,
            minute_phase=minute_phase,
            panel_modifier=panel_modifier,
            over_permission=over_permission,
            under_permission=under_permission,
            support_points=support_points,
            caution_points=caution_points,
        )

        return {
            "volatility_level": volatility_level,
            "panel_modifier": panel_modifier,
            "confidence_adjustment": confidence_adjustment,
            "publish_modifier": publish_modifier,
            "revalidation_required": revalidation_required,
            "warning": warning,
            "late_game_reading": late_game_reading,
            "first_half_reading": first_half_reading,
            "over_permission": over_permission,
            "under_permission": under_permission,
            "reason": reason,
            "support_points": support_points[:8],
            "caution_points": caution_points[:8],
        }

    def _first_half_profile(
        self,
        minute: int,
        minute_phase: str,
        real_volume: bool,
        total_goals: int,
        goal_gap: int,
        over_score: float,
        under_score: float,
        market_gap: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        recent_attack_proxy: float,
    ) -> Dict[str, Any]:
        support_points: List[str] = []
        caution_points: List[str] = []

        confidence_adjustment = 0
        panel_modifier = "SHOW_CONTEXT"
        publish_modifier = "NORMAL"
        over_permission = "ALLOW_IF_CONFIRMED"
        under_permission = "ALLOW_IF_CONFIRMED"
        reading = "FIRST_HALF_DYNAMIC_READING"

        if minute <= 15:
            panel_modifier = "SHOW_AS_OBSERVATION"
            publish_modifier = "LIMIT_DIRECT_TOP"
            confidence_adjustment -= 3
            reading = "EARLY_FIRST_HALF_OBSERVATION"
            caution_points.append("Primeros minutos, evitar conclusión fuerte demasiado temprano.")

            if real_volume and over_score >= 55:
                panel_modifier = "SHOW_AS_CANDIDATE"
                over_permission = "ALLOW_AS_CANDIDATE"
                support_points.append("OVER temprano permitido solo como candidato por volumen real.")

            if under_score >= over_score + 18 and score_hold_probability >= 72:
                under_permission = "ALLOW_AS_OBSERVATION"
                caution_points.append("UNDER temprano no debe asumirse definitivo.")

        elif minute <= 30:
            reading = "FIRST_HALF_GROWTH_WINDOW"

            if real_volume or offensive_volume_score >= 50 or recent_attack_proxy >= 45:
                panel_modifier = "SHOW_AS_CANDIDATE"
                over_permission = "ALLOW_AS_CANDIDATE"
                confidence_adjustment += 2
                support_points.append("Ventana 15-30 con señales de crecimiento ofensivo.")

            if (
                under_score >= over_score + 15
                and score_hold_probability >= 75
                and not real_volume
            ):
                under_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("Ventana 15-30 con conservación temprana del marcador.")

        else:
            reading = "PRE_HALFTIME_PUSH_WINDOW"

            if real_volume or pressure_score >= 55 or rhythm_score >= 52:
                panel_modifier = "SHOW_AS_CANDIDATE"
                over_permission = "ALLOW_AS_CANDIDATE"
                confidence_adjustment += 3
                support_points.append("Minuto 30-45, posible empuje ofensivo antes del descanso.")

            if (
                under_score >= over_score + 12
                and score_hold_probability >= 74
                and not real_volume
            ):
                panel_modifier = "SHOW_AS_CANDIDATE"
                under_permission = "ALLOW_AS_CANDIDATE"
                support_points.append("Minuto 30-45, partido entrando en control antes del descanso.")

        return {
            "reading": reading,
            "confidence_adjustment": confidence_adjustment,
            "panel_modifier": panel_modifier,
            "publish_modifier": publish_modifier,
            "over_permission": over_permission,
            "under_permission": under_permission,
            "support_points": support_points,
            "caution_points": caution_points,
        }

    def _second_half_profile(
        self,
        minute: int,
        minute_phase: str,
        real_volume: bool,
        total_goals: int,
        goal_gap: int,
        over_score: float,
        under_score: float,
        market_gap: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        recent_attack_proxy: float,
        over_candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        support_points: List[str] = []
        caution_points: List[str] = []

        confidence_adjustment = 0
        panel_modifier = "SHOW_CONTEXT"
        publish_modifier = "NORMAL"
        over_permission = "ALLOW_IF_CONFIRMED"
        under_permission = "ALLOW_IF_CONFIRMED"
        reading = "SECOND_HALF_DYNAMIC_READING"

        over_candidate_level = normalize_text(over_candidate.get("over_candidate_level"))
        over_active = bool(over_candidate.get("over_candidate_active"))

        if minute <= 60:
            reading = "SECOND_HALF_START_OVER_GROWTH"

            if real_volume or over_active:
                panel_modifier = "SHOW_AS_CANDIDATE"
                over_permission = "ALLOW_AS_CANDIDATE"
                confidence_adjustment += 2
                support_points.append("Inicio del segundo tiempo con señales de crecimiento OVER.")

            if under_score >= over_score + 18 and not real_volume:
                under_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("Inicio del segundo tiempo con lectura de conservación.")

        elif minute <= 75:
            reading = "SECOND_HALF_REVALIDATION_WINDOW"
            publish_modifier = "LIMIT_DIRECT_TOP"
            confidence_adjustment -= 2
            caution_points.append("Minuto 60-75, CONMEBOL requiere revalidar OVER y UNDER.")

            if real_volume or over_candidate_level in {
                "OVER_HIGH_OBSERVATION",
                "OVER_STRONG_CANDIDATE",
            }:
                over_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("OVER sigue vivo por volumen o candidato activo.")

            if (
                score_hold_probability >= 74
                and under_score >= over_score + 10
                and not real_volume
            ):
                under_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("UNDER empieza a tomar fuerza por conservación del marcador.")

        elif minute <= 85:
            reading = "LATE_GAME_CLOSING_DECISION"
            publish_modifier = "LIMIT_DIRECT_TOP"
            confidence_adjustment -= 3
            caution_points.append("Minuto 75-85, el partido puede girar rápido hacia cierre o asedio final.")

            if real_volume and goal_need_score >= 55:
                over_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("OVER se mantiene vivo por volumen real y necesidad de gol.")

            elif score_hold_probability >= 72 or under_score >= over_score + 8:
                under_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("UNDER en conservación por fase tardía y menor profundidad ofensiva.")

        else:
            reading = "FINAL_VOLATILITY_WINDOW"
            publish_modifier = "NO_DIRECT_TOP"
            confidence_adjustment -= 6
            panel_modifier = "SHOW_AS_OBSERVATION"
            caution_points.append("Minuto 85+, evitar entrada automática salvo asedio muy claro.")

            if real_volume and goal_need_score >= 65:
                over_permission = "ALLOW_AS_CANDIDATE"
                panel_modifier = "SHOW_AS_CANDIDATE"
                support_points.append("OVER final permitido solo como candidato por asedio claro.")

            if score_hold_probability >= 70 and not real_volume:
                under_permission = "ALLOW_AS_CANDIDATE"
                support_points.append("UNDER final por conservación y ausencia de volumen real.")

        return {
            "reading": reading,
            "confidence_adjustment": confidence_adjustment,
            "panel_modifier": panel_modifier,
            "publish_modifier": publish_modifier,
            "over_permission": over_permission,
            "under_permission": under_permission,
            "support_points": support_points,
            "caution_points": caution_points,
        }

    def _standard_profile(self) -> Dict[str, Any]:
        return {
            "volatility_level": "NORMAL",
            "panel_modifier": "NORMAL",
            "confidence_adjustment": 0,
            "publish_modifier": "NORMAL",
            "revalidation_required": False,
            "warning": "",
            "late_game_reading": "",
            "first_half_reading": "",
            "over_permission": "NORMAL",
            "under_permission": "NORMAL",
            "reason": "Liga estándar, sin ajuste especial de volatilidad.",
            "support_points": [],
            "caution_points": [],
        }

    def _stronger_panel_modifier(self, current: str, new: str) -> str:
        order = {
            "NORMAL": 0,
            "SHOW_CONTEXT": 1,
            "SHOW_AS_OBSERVATION": 2,
            "SHOW_AS_CANDIDATE": 3,
        }

        return new if order.get(new, 0) > order.get(current, 0) else current

    def _stricter_publish_modifier(self, current: str, new: str) -> str:
        order = {
            "NORMAL": 0,
            "LIMIT_DIRECT_TOP": 1,
            "NO_DIRECT_TOP": 2,
        }

        return new if order.get(new, 0) > order.get(current, 0) else current

    def _build_reason(
        self,
        league_group: str,
        minute_phase: str,
        panel_modifier: str,
        over_permission: str,
        under_permission: str,
        support_points: List[str],
        caution_points: List[str],
    ) -> str:
        parts = [
            f"Contexto {league_group}",
            f"fase {minute_phase}",
            f"modificador visual {panel_modifier}",
            f"OVER {over_permission}",
            f"UNDER {under_permission}",
        ]

        if support_points:
            parts.append("soporte: " + support_points[0])

        if caution_points:
            parts.append("cautela: " + caution_points[0])

        return ". ".join(parts) + "."
