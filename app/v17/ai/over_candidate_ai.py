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


class OverCandidateAI:
    """
    Detector específico de candidatos OVER para V17.

    Recupera la intuición útil de V16:
    - presión ofensiva
    - ritmo
    - tiros
    - tiros al arco
    - corners
    - ataques peligrosos
    - necesidad de gol
    - marcador abierto
    - ventana táctica
    - momentum ofensivo

    Pero lo hace de forma limpia:
    - no fuerza OVER
    - no convierte cualquier presión en señal
    - separa candidato fuerte, observación alta y no listo
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
    ) -> Dict[str, Any]:
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
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)
        market_gap = over_score - under_score

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_volume_score = safe_float(tactical.get("offensive_volume_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)

        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)

        risk_status = str(risk.get("risk_status") or "").upper()
        contradiction_status = str(
            contradiction.get("contradiction_status") or ""
        ).upper()

        data_quality = str(
            match.get("data_quality")
            or match.get("calidad_datos")
            or ""
        ).upper()

        scan_phase = str(match.get("scan_phase") or "").upper()
        clock_status = str(match.get("clock_status") or "").upper()

        blockers = self._critical_blockers(
            clock_status=clock_status,
            risk_status=risk_status,
            contradiction_status=contradiction_status,
            false_pressure_risk=false_pressure_risk,
        )

        support_checks = self._support_checks(
            minute=minute,
            total_goals=total_goals,
            goal_gap=goal_gap,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
            over_score=over_score,
            under_score=under_score,
            market_gap=market_gap,
            tactical_score=tactical_score,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            recent_attack_proxy=recent_attack_proxy,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            goal_need_score=goal_need_score,
            score_hold_probability=score_hold_probability,
            data_quality=data_quality,
            scan_phase=scan_phase,
        )

        support_score = sum(1 for x in support_checks if x["passed"])
        support_total = len(support_checks)
        support_ratio = support_score / support_total if support_total else 0.0

        support_points = [x["label"] for x in support_checks if x["passed"]]
        missing_points = [x["label"] for x in support_checks if not x["passed"]]

        over_level = self._over_level(
            minute=minute,
            blockers=blockers,
            support_score=support_score,
            support_ratio=support_ratio,
            over_score=over_score,
            market_gap=market_gap,
            offensive_volume_score=offensive_volume_score,
            offensive_depth_score=offensive_depth_score,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
            false_pressure_risk=false_pressure_risk,
        )

        return {
            "over_candidate_version": "V17_OVER_CANDIDATE_1",
            "over_candidate_level": over_level,
            "over_candidate_active": over_level in {
                "OVER_STRONG_CANDIDATE",
                "OVER_HIGH_OBSERVATION",
            },
            "over_majority_support": support_ratio >= 0.62,
            "over_support_score": support_score,
            "over_support_total": support_total,
            "over_support_ratio": round(support_ratio, 3),
            "over_market_gap": round(market_gap, 2),
            "over_blockers": blockers,
            "over_support_points": support_points[:8],
            "over_missing_points": missing_points[:8],
            "why_over_candidate": self._why_over_candidate(
                over_level=over_level,
                support_score=support_score,
                support_total=support_total,
                market_gap=market_gap,
                support_points=support_points,
                blockers=blockers,
            ),
            "why_over_not_ready": self._why_over_not_ready(
                over_level=over_level,
                missing_points=missing_points,
                blockers=blockers,
                false_pressure_risk=false_pressure_risk,
            ),
        }

    def _critical_blockers(
        self,
        clock_status: str,
        risk_status: str,
        contradiction_status: str,
        false_pressure_risk: float,
    ) -> List[str]:
        blockers: List[str] = []

        if clock_status in {"BLOCKED_CLOCK", "CLOCK_FROZEN"}:
            blockers.append("CLOCK_BLOCKED")

        if risk_status in {"EXTREME_RISK"}:
            blockers.append("EXTREME_RISK")

        if contradiction_status in {"STRONG_CONTRADICTION", "CRITICAL_CONTRADICTION"}:
            blockers.append("CRITICAL_CONTRADICTION")

        if false_pressure_risk >= 82:
            blockers.append("FALSE_PRESSURE_CRITICAL")

        return blockers

    def _support_checks(
        self,
        minute: int,
        total_goals: int,
        goal_gap: int,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
        over_score: float,
        under_score: float,
        market_gap: float,
        tactical_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        recent_attack_proxy: float,
        pressure_score: float,
        rhythm_score: float,
        goal_need_score: float,
        score_hold_probability: float,
        data_quality: str,
        scan_phase: str,
    ) -> List[Dict[str, Any]]:
        favorable_window = 18 <= minute <= 82
        late_but_alive = 83 <= minute <= 90 and goal_need_score >= 65
        open_scoreline = total_goals >= 1 and goal_gap <= 2
        chasing_context = goal_gap == 1 or goal_need_score >= 60

        offensive_activity = (
            shots >= 5
            or shots_on_target >= 2
            or corners >= 4
            or dangerous_attacks >= 10
            or xg >= 0.70
        )

        return [
            {
                "key": "minute_window",
                "passed": favorable_window or late_but_alive,
                "label": "Minuto favorable para lectura OVER.",
            },
            {
                "key": "market_edge",
                "passed": over_score >= 58 and market_gap >= 4,
                "label": "OVER tiene ventaja mínima de mercado.",
            },
            {
                "key": "offensive_activity",
                "passed": offensive_activity,
                "label": "Existe actividad ofensiva medible.",
            },
            {
                "key": "shots",
                "passed": shots >= 5,
                "label": "Remates totales suficientes.",
            },
            {
                "key": "shots_on_target",
                "passed": shots_on_target >= 1,
                "label": "Hay remates al arco.",
            },
            {
                "key": "corners",
                "passed": corners >= 3,
                "label": "Corners respaldan presión ofensiva.",
            },
            {
                "key": "dangerous_attacks",
                "passed": dangerous_attacks >= 10,
                "label": "Ataques peligrosos presentes.",
            },
            {
                "key": "xg",
                "passed": xg >= 0.65,
                "label": "xG con señal ofensiva.",
            },
            {
                "key": "pressure",
                "passed": pressure_score >= 52,
                "label": "Presión ofensiva suficiente.",
            },
            {
                "key": "rhythm",
                "passed": rhythm_score >= 50,
                "label": "Ritmo activo.",
            },
            {
                "key": "goal_need",
                "passed": goal_need_score >= 55 or chasing_context,
                "label": "Existe necesidad de gol.",
            },
            {
                "key": "offensive_volume",
                "passed": offensive_volume_score >= 46,
                "label": "Volumen ofensivo aceptable.",
            },
            {
                "key": "offensive_depth",
                "passed": offensive_depth_score >= 42,
                "label": "Profundidad ofensiva aceptable.",
            },
            {
                "key": "recent_attack",
                "passed": recent_attack_proxy >= 42,
                "label": "Actividad reciente acompaña.",
            },
            {
                "key": "scoreline",
                "passed": open_scoreline or chasing_context,
                "label": "Marcador permite lectura de gol.",
            },
            {
                "key": "not_score_hold",
                "passed": score_hold_probability < 78,
                "label": "La conservación del marcador no domina totalmente.",
            },
            {
                "key": "data_or_phase",
                "passed": data_quality in {"MEDIUM", "HIGH"} or scan_phase == "SCANNABLE" or offensive_activity,
                "label": "Datos suficientes o actividad real detectada.",
            },
        ]

    def _over_level(
        self,
        minute: int,
        blockers: List[str],
        support_score: int,
        support_ratio: float,
        over_score: float,
        market_gap: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        pressure_score: float,
        rhythm_score: float,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
        false_pressure_risk: float,
    ) -> str:
        if blockers:
            return "OVER_BLOCKED"

        if minute < 10:
            return "OVER_NOT_READY"

        real_activity = (
            shots >= 5
            or shots_on_target >= 1
            or corners >= 3
            or dangerous_attacks >= 10
            or xg >= 0.65
        )

        soft_activity = (
            offensive_volume_score >= 46
            and offensive_depth_score >= 42
            and pressure_score >= 50
            and rhythm_score >= 48
        )

        if not real_activity and not soft_activity:
            return "OVER_NOT_READY"

        if false_pressure_risk >= 75:
            return "OVER_NORMAL_OBSERVATION"

        if (
            support_ratio >= 0.72
            and over_score >= 62
            and market_gap >= 6
            and (real_activity or soft_activity)
        ):
            return "OVER_STRONG_CANDIDATE"

        if (
            support_ratio >= 0.55
            and over_score >= 55
            and (real_activity or soft_activity)
        ):
            return "OVER_HIGH_OBSERVATION"

        return "OVER_NORMAL_OBSERVATION"

    def _why_over_candidate(
        self,
        over_level: str,
        support_score: int,
        support_total: int,
        market_gap: float,
        support_points: List[str],
        blockers: List[str],
    ) -> str:
        if blockers:
            return "OVER no puede subir porque existe bloqueo crítico: " + ", ".join(blockers[:3])

        if over_level == "OVER_STRONG_CANDIDATE":
            base = (
                f"OVER aparece como candidato fuerte porque cumple {support_score}/{support_total} "
                f"filtros ofensivos y tiene ventaja de mercado de {market_gap:.0f} puntos."
            )
        elif over_level == "OVER_HIGH_OBSERVATION":
            base = (
                f"OVER aparece como observación alta porque cumple {support_score}/{support_total} "
                "filtros ofensivos, pero todavía requiere confirmación."
            )
        elif over_level == "OVER_NORMAL_OBSERVATION":
            base = (
                f"OVER queda en observación normal porque solo cumple {support_score}/{support_total} "
                "filtros ofensivos."
            )
        else:
            base = "OVER no está listo porque no hay mayoría ofensiva suficiente."

        if support_points:
            return base + " Respaldo: " + " ".join(support_points[:3])

        return base

    def _why_over_not_ready(
        self,
        over_level: str,
        missing_points: List[str],
        blockers: List[str],
        false_pressure_risk: float,
    ) -> str:
        if blockers:
            return "OVER no está disponible por bloqueo crítico: " + ", ".join(blockers[:3])

        if over_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"}:
            if missing_points:
                return "Para subir más, OVER necesita confirmar: " + ", ".join(missing_points[:3])
            return "OVER tiene respaldo suficiente como candidato."

        if false_pressure_risk >= 75:
            return "OVER no sube porque existe riesgo de presión falsa."

        if missing_points:
            return "OVER no está listo porque falta: " + ", ".join(missing_points[:4])

        return "OVER no está listo porque no se detecta mayoría ofensiva suficiente."
