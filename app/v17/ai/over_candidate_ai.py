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
    return str(value or "").strip().upper()


class OverCandidateAI:
    """
    Detector específico de candidatos OVER para V17.

    Filosofía V17:
    - No decide por estadística aislada.
    - Lee si el volumen ofensivo representa amenaza real o solo actividad sin profundidad.
    - No promueve OVER fuerte con datos fixture-only, sin estadísticas live o con presión falsa.
    - Usa PressureQualityAI si está disponible, pero mantiene compatibilidad si aún no fue integrado.
    """

    VERSION = "V17_OVER_CANDIDATE_3_PRESSURE_QUALITY"

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        tactical = tactical or {}
        market = market or {}
        risk = risk or {}
        contradiction = contradiction or {}

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

        risk_status = normalize_text(risk.get("risk_status"))
        contradiction_status = normalize_text(contradiction.get("contradiction_status"))

        data_quality = normalize_text(
            match.get("data_quality")
            or match.get("calidad_datos")
            or match.get("data_quality_status")
        )
        scan_phase = normalize_text(match.get("scan_phase"))
        stats_source = normalize_text(match.get("stats_source"))
        clock_status = normalize_text(match.get("clock_status"))
        is_scannable = bool(match.get("is_scannable", True))

        pressure_type = normalize_text(
            match.get("pressure_type")
            or tactical.get("pressure_type")
            or context.get("pressure_type")
        )
        real_goal_threat = normalize_text(
            match.get("real_goal_threat")
            or tactical.get("real_goal_threat")
            or context.get("real_goal_threat")
        )
        pressure_game_state = normalize_text(
            match.get("pressure_game_state")
            or match.get("game_state")
            or tactical.get("game_state")
            or context.get("game_state")
        )
        pressure_reading = str(
            match.get("pressure_reading")
            or tactical.get("pressure_reading")
            or context.get("pressure_reading")
            or ""
        )

        has_live_stats = self._has_live_stats(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            xg=xg,
            dangerous_attacks=dangerous_attacks,
        )

        if self._should_wait_live_stats(
            is_scannable=is_scannable,
            scan_phase=scan_phase,
            stats_source=stats_source,
            data_quality=data_quality,
            has_live_stats=has_live_stats,
        ):
            return self._wait_live_stats_result(
                minute=minute,
                data_quality=data_quality,
                scan_phase=scan_phase,
                stats_source=stats_source,
            )

        blockers = self._critical_blockers(
            clock_status=clock_status,
            risk_status=risk_status,
            contradiction_status=contradiction_status,
            false_pressure_risk=false_pressure_risk,
        )

        volume_profile = self._volume_profile(
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            dangerous_attacks=dangerous_attacks,
            xg=xg,
            pressure_type=pressure_type,
            real_goal_threat=real_goal_threat,
            pressure_game_state=pressure_game_state,
            has_live_stats=has_live_stats,
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
            pressure_type=pressure_type,
            real_goal_threat=real_goal_threat,
            pressure_game_state=pressure_game_state,
            volume_profile=volume_profile,
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
            pressure_type=pressure_type,
            real_goal_threat=real_goal_threat,
            pressure_game_state=pressure_game_state,
            volume_profile=volume_profile,
        )

        return {
            "over_candidate_version": self.VERSION,
            "over_candidate_level": over_level,
            "over_candidate_active": over_level in {
                "OVER_STRONG_CANDIDATE",
                "OVER_HIGH_OBSERVATION",
            },
            "over_majority_support": support_ratio >= 0.58,
            "over_support_score": support_score,
            "over_support_total": support_total,
            "over_support_ratio": round(support_ratio, 3),
            "over_market_gap": round(market_gap, 2),
            "over_volume_profile": volume_profile,
            "over_blockers": blockers,
            "over_support_points": support_points[:8],
            "over_missing_points": missing_points[:8],
            "over_pressure_type": pressure_type,
            "over_real_goal_threat": real_goal_threat,
            "over_pressure_game_state": pressure_game_state,
            "over_pressure_reading": pressure_reading,
            "why_over_candidate": self._why_over_candidate(
                over_level=over_level,
                support_score=support_score,
                support_total=support_total,
                market_gap=market_gap,
                support_points=support_points,
                blockers=blockers,
                volume_profile=volume_profile,
                pressure_type=pressure_type,
                real_goal_threat=real_goal_threat,
                pressure_reading=pressure_reading,
            ),
            "why_over_not_ready": self._why_over_not_ready(
                over_level=over_level,
                missing_points=missing_points,
                blockers=blockers,
                false_pressure_risk=false_pressure_risk,
                volume_profile=volume_profile,
                pressure_type=pressure_type,
                real_goal_threat=real_goal_threat,
            ),
        }

    def _should_wait_live_stats(
        self,
        is_scannable: bool,
        scan_phase: str,
        stats_source: str,
        data_quality: str,
        has_live_stats: bool,
    ) -> bool:
        if not is_scannable:
            return True

        if scan_phase in {"INITIALIZING", "WAITING_LIVE_STATS", "NO_LIVE_STATS"}:
            return True

        if stats_source in {"API_FOOTBALL_FIXTURE_ONLY", "FIXTURE_ONLY"}:
            return True

        if data_quality in {"LOW", "BAD", "NO_DATA"} and not has_live_stats:
            return True

        return False

    def _wait_live_stats_result(
        self,
        minute: int,
        data_quality: str,
        scan_phase: str,
        stats_source: str,
    ) -> Dict[str, Any]:
        reason = (
            "OVER no se evalúa todavía porque el partido no tiene estadísticas live suficientes. "
            "Se espera confirmación de remates, ataques, xG, córners o presión real."
        )

        return {
            "over_candidate_version": self.VERSION,
            "over_candidate_level": "WAIT_LIVE_STATS",
            "over_candidate_active": False,
            "over_majority_support": False,
            "over_support_score": 0,
            "over_support_total": 0,
            "over_support_ratio": 0.0,
            "over_market_gap": 0.0,
            "over_volume_profile": {
                "strong_volume": False,
                "medium_volume": False,
                "minimum_volume": False,
                "has_live_stats": False,
                "pressure_type": "WAIT_LIVE_STATS",
                "real_goal_threat": "UNKNOWN",
                "false_pressure": False,
                "lateral_pressure": False,
                "dominance_without_depth": False,
            },
            "over_blockers": [],
            "over_support_points": [],
            "over_missing_points": [
                "Esperar estadísticas live reales.",
                "Esperar presión, remates o ataques medibles.",
            ],
            "over_pressure_type": "WAIT_LIVE_STATS",
            "over_real_goal_threat": "UNKNOWN",
            "over_pressure_game_state": "WAIT_LIVE_STATS",
            "over_pressure_reading": reason,
            "why_over_candidate": reason,
            "why_over_not_ready": (
                f"Esperando datos live. Minuto {minute}, calidad={data_quality or 'UNKNOWN'}, "
                f"fase={scan_phase or 'UNKNOWN'}, fuente={stats_source or 'UNKNOWN'}."
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

        if false_pressure_risk >= 88:
            blockers.append("FALSE_PRESSURE_CRITICAL")

        return blockers

    def _volume_profile(
        self,
        shots: float,
        shots_on_target: float,
        corners: float,
        dangerous_attacks: float,
        xg: float,
        pressure_type: str,
        real_goal_threat: str,
        pressure_game_state: str,
        has_live_stats: bool,
    ) -> Dict[str, Any]:
        false_pressure = pressure_type in {"FALSE_PRESSURE", "LOW_PRESSURE"}
        lateral_pressure = pressure_type in {"LATERAL_PRESSURE", "DOMINANCE_WITHOUT_DEPTH"}
        real_pressure = pressure_type in {"REAL_PRESSURE", "HIGH_THREAT_PRESSURE"}
        high_threat = real_goal_threat in {"HIGH", "MEDIUM_HIGH"}

        real_shot_threat = shots_on_target >= 2 or dangerous_attacks >= 10
        clear_goal_threat = shots_on_target >= 3 or dangerous_attacks >= 16 or (xg >= 1.0 and shots_on_target >= 1)

        strong_volume = has_live_stats and (
            clear_goal_threat
            or real_pressure
            or (xg >= 1.20 and real_shot_threat)
        )

        medium_volume = has_live_stats and (
            shots_on_target >= 1
            or dangerous_attacks >= 8
            or xg >= 0.65
            or corners >= 4
            or shots >= 7
            or high_threat
        )

        minimum_volume = has_live_stats and (
            shots >= 3
            or shots_on_target >= 1
            or corners >= 2
            or dangerous_attacks >= 5
            or xg >= 0.35
        )

        if false_pressure and not clear_goal_threat:
            strong_volume = False

        if lateral_pressure and shots_on_target == 0 and dangerous_attacks == 0:
            strong_volume = False

        dominance_without_depth = (
            corners >= 4
            and shots_on_target == 0
            and dangerous_attacks == 0
        )

        return {
            "strong_volume": strong_volume,
            "medium_volume": medium_volume,
            "minimum_volume": minimum_volume,
            "has_live_stats": has_live_stats,
            "shots": shots,
            "shots_on_target": shots_on_target,
            "corners": corners,
            "dangerous_attacks": dangerous_attacks,
            "xg": xg,
            "pressure_type": pressure_type,
            "real_goal_threat": real_goal_threat,
            "pressure_game_state": pressure_game_state,
            "false_pressure": false_pressure,
            "lateral_pressure": lateral_pressure,
            "real_pressure": real_pressure,
            "dominance_without_depth": dominance_without_depth,
        }

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
        pressure_type: str,
        real_goal_threat: str,
        pressure_game_state: str,
        volume_profile: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        favorable_window = 16 <= minute <= 84
        late_but_alive = 85 <= minute <= 90 and goal_need_score >= 60
        open_scoreline = total_goals >= 1 and goal_gap <= 2
        chasing_context = goal_gap == 1 or goal_need_score >= 58

        strong_volume = bool(volume_profile.get("strong_volume"))
        medium_volume = bool(volume_profile.get("medium_volume"))
        minimum_volume = bool(volume_profile.get("minimum_volume"))
        has_live_stats = bool(volume_profile.get("has_live_stats"))
        false_pressure = bool(volume_profile.get("false_pressure"))
        lateral_pressure = bool(volume_profile.get("lateral_pressure"))
        real_pressure = bool(volume_profile.get("real_pressure"))
        dominance_without_depth = bool(volume_profile.get("dominance_without_depth"))

        real_offensive_activity = has_live_stats and (
            minimum_volume
            or real_pressure
            or real_goal_threat in {"HIGH", "MEDIUM_HIGH", "MEDIUM"}
        )

        useful_pressure = real_pressure or (
            pressure_score >= 48
            and shots_on_target >= 1
        )

        return [
            {
                "key": "minute_window",
                "passed": favorable_window or late_but_alive,
                "label": "Minuto favorable para lectura OVER.",
            },
            {
                "key": "market_edge",
                "passed": over_score >= 54 and market_gap >= -8,
                "label": "OVER no está demasiado lejos en mercado.",
            },
            {
                "key": "live_stats",
                "passed": has_live_stats,
                "label": "Existen estadísticas live reales.",
            },
            {
                "key": "offensive_activity",
                "passed": real_offensive_activity,
                "label": "Existe actividad ofensiva útil, no solo estadística vacía.",
            },
            {
                "key": "pressure_quality",
                "passed": real_pressure or real_goal_threat in {"HIGH", "MEDIUM_HIGH"},
                "label": "La presión muestra amenaza real de gol.",
            },
            {
                "key": "not_false_pressure",
                "passed": not (false_pressure or dominance_without_depth),
                "label": "La presión no parece falsa ni lateral.",
            },
            {
                "key": "strong_volume",
                "passed": strong_volume,
                "label": "Volumen ofensivo fuerte con amenaza real.",
            },
            {
                "key": "medium_volume",
                "passed": medium_volume,
                "label": "Volumen ofensivo medio detectado.",
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
                "passed": corners >= 3 and not lateral_pressure,
                "label": "Corners respaldan presión ofensiva útil.",
            },
            {
                "key": "dangerous_attacks",
                "passed": dangerous_attacks >= 8 or (real_pressure and medium_volume),
                "label": "Ataques peligrosos o presión real presentes.",
            },
            {
                "key": "xg",
                "passed": xg >= 0.65 and not (false_pressure and shots_on_target == 0),
                "label": "xG ofensivo con amenaza creíble.",
            },
            {
                "key": "pressure",
                "passed": useful_pressure or strong_volume,
                "label": "Presión ofensiva útil.",
            },
            {
                "key": "rhythm",
                "passed": rhythm_score >= 46 or (medium_volume and not false_pressure),
                "label": "Ritmo activo o volumen útil suficiente.",
            },
            {
                "key": "goal_need",
                "passed": goal_need_score >= 52 or chasing_context,
                "label": "Existe necesidad de gol.",
            },
            {
                "key": "offensive_volume",
                "passed": offensive_volume_score >= 42 or medium_volume,
                "label": "Volumen ofensivo aceptable.",
            },
            {
                "key": "offensive_depth",
                "passed": offensive_depth_score >= 40 or shots_on_target >= 2 or real_pressure,
                "label": "Profundidad ofensiva aceptable.",
            },
            {
                "key": "recent_attack",
                "passed": recent_attack_proxy >= 40 and not false_pressure,
                "label": "Actividad reciente acompaña sin señal clara de presión falsa.",
            },
            {
                "key": "scoreline",
                "passed": open_scoreline or chasing_context,
                "label": "Marcador permite lectura de gol.",
            },
            {
                "key": "not_score_hold",
                "passed": score_hold_probability < 82 or strong_volume,
                "label": "La conservación del marcador no domina totalmente.",
            },
            {
                "key": "data_or_phase",
                "passed": data_quality in {"MEDIUM", "HIGH"} or scan_phase in {"SCANNABLE", "FULL_SCAN"},
                "label": "Datos suficientes para interpretar el partido.",
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
        pressure_type: str,
        real_goal_threat: str,
        pressure_game_state: str,
        volume_profile: Dict[str, Any],
    ) -> str:
        if blockers:
            return "OVER_BLOCKED"

        if minute < 10:
            return "OVER_NOT_READY"

        strong_volume = bool(volume_profile.get("strong_volume"))
        medium_volume = bool(volume_profile.get("medium_volume"))
        minimum_volume = bool(volume_profile.get("minimum_volume"))
        has_live_stats = bool(volume_profile.get("has_live_stats"))
        false_pressure = bool(volume_profile.get("false_pressure"))
        lateral_pressure = bool(volume_profile.get("lateral_pressure"))
        dominance_without_depth = bool(volume_profile.get("dominance_without_depth"))
        real_pressure = bool(volume_profile.get("real_pressure"))

        if not has_live_stats:
            return "OVER_NOT_READY"

        real_activity = minimum_volume or medium_volume or strong_volume or real_pressure

        soft_activity = (
            offensive_volume_score >= 42
            and offensive_depth_score >= 40
            and not false_pressure
        ) or (
            pressure_score >= 46
            and rhythm_score >= 44
            and shots_on_target >= 1
        )

        if not real_activity and not soft_activity:
            return "OVER_NOT_READY"

        if shots_on_target == 0 and dangerous_attacks == 0:
            if corners >= 4 or shots >= 7:
                return "OVER_NORMAL_OBSERVATION"
            return "OVER_NOT_READY"

        if false_pressure_risk >= 78 and not strong_volume:
            return "OVER_NORMAL_OBSERVATION"

        if false_pressure or dominance_without_depth:
            if support_ratio >= 0.72 and (shots_on_target >= 2 or xg >= 1.20):
                return "OVER_HIGH_OBSERVATION"
            return "OVER_NORMAL_OBSERVATION"

        if lateral_pressure and not real_pressure:
            if support_ratio >= 0.70 and shots_on_target >= 1 and xg >= 0.85:
                return "OVER_HIGH_OBSERVATION"
            return "OVER_NORMAL_OBSERVATION"

        if (
            support_ratio >= 0.74
            and over_score >= 60
            and market_gap >= 2
            and (strong_volume or real_pressure or real_goal_threat == "HIGH")
        ):
            return "OVER_STRONG_CANDIDATE"

        if (
            support_ratio >= 0.64
            and over_score >= 54
            and market_gap >= -12
            and (medium_volume or strong_volume or soft_activity or real_pressure)
        ):
            return "OVER_HIGH_OBSERVATION"

        if (
            support_score >= 11
            and (strong_volume or real_pressure)
            and market_gap >= -35
        ):
            return "OVER_HIGH_OBSERVATION"

        if (
            support_ratio >= 0.58
            and medium_volume
            and market_gap >= -45
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
        volume_profile: Dict[str, Any],
        pressure_type: str,
        real_goal_threat: str,
        pressure_reading: str,
    ) -> str:
        if blockers:
            return "OVER no puede subir porque existe bloqueo crítico: " + ", ".join(blockers[:3])

        strong_volume = bool(volume_profile.get("strong_volume"))
        medium_volume = bool(volume_profile.get("medium_volume"))
        false_pressure = bool(volume_profile.get("false_pressure"))
        lateral_pressure = bool(volume_profile.get("lateral_pressure"))
        dominance_without_depth = bool(volume_profile.get("dominance_without_depth"))

        pressure_detail = ""
        if pressure_reading:
            pressure_detail = f" Lectura de presión: {pressure_reading}"
        elif pressure_type:
            pressure_detail = f" Tipo de presión: {pressure_type}."

        if over_level == "OVER_STRONG_CANDIDATE":
            base = (
                f"OVER aparece como candidato fuerte porque cumple {support_score}/{support_total} "
                f"filtros útiles, tiene amenaza real de gol y una diferencia de mercado de {market_gap:.0f} puntos."
            )
        elif over_level == "OVER_HIGH_OBSERVATION":
            if strong_volume or medium_volume:
                base = (
                    f"OVER aparece como observación alta porque cumple {support_score}/{support_total} "
                    "filtros útiles y tiene volumen ofensivo con cierta amenaza, aunque todavía necesita confirmación."
                )
            else:
                base = (
                    f"OVER aparece como observación alta porque cumple {support_score}/{support_total} "
                    "filtros útiles, pero todavía requiere confirmación de profundidad."
                )
        elif over_level == "OVER_NORMAL_OBSERVATION":
            if false_pressure or lateral_pressure or dominance_without_depth:
                base = (
                    "OVER queda en observación normal porque hay actividad ofensiva, pero la lectura sugiere "
                    "presión lateral, falsa o sin profundidad suficiente."
                )
            else:
                base = (
                    f"OVER queda en observación normal porque cumple {support_score}/{support_total} "
                    "filtros útiles, pero todavía no tiene amenaza suficiente para subir."
                )
        else:
            base = "OVER no está listo porque no hay amenaza ofensiva real suficiente."

        if support_points:
            return base + pressure_detail + " Respaldo: " + " ".join(support_points[:3])

        return base + pressure_detail

    def _why_over_not_ready(
        self,
        over_level: str,
        missing_points: List[str],
        blockers: List[str],
        false_pressure_risk: float,
        volume_profile: Dict[str, Any],
        pressure_type: str,
        real_goal_threat: str,
    ) -> str:
        if blockers:
            return "OVER no está disponible por bloqueo crítico: " + ", ".join(blockers[:3])

        strong_volume = bool(volume_profile.get("strong_volume"))
        medium_volume = bool(volume_profile.get("medium_volume"))
        false_pressure = bool(volume_profile.get("false_pressure"))
        lateral_pressure = bool(volume_profile.get("lateral_pressure"))
        dominance_without_depth = bool(volume_profile.get("dominance_without_depth"))

        if over_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"}:
            if missing_points:
                return "Para subir más, OVER necesita confirmar: " + ", ".join(missing_points[:3])
            return "OVER tiene respaldo suficiente como candidato."

        if false_pressure or dominance_without_depth:
            return (
                "OVER no sube porque la actividad ofensiva parece presión falsa o dominio sin profundidad. "
                "Se necesita amenaza real: remates al arco, ataques peligrosos o xG más creíble."
            )

        if lateral_pressure:
            return (
                "OVER no sube porque la presión es principalmente lateral. "
                "Falta profundidad ofensiva y amenaza directa al arco."
            )

        if false_pressure_risk >= 78 and not strong_volume:
            return "OVER no sube porque existe riesgo alto de presión falsa."

        if strong_volume or medium_volume:
            return (
                "OVER tiene volumen ofensivo visible, pero no sube más porque aún falta amenaza real "
                "o la comparación de mercado favorece otra lectura."
            )

        if missing_points:
            return "OVER no está listo porque falta: " + ", ".join(missing_points[:4])

        return "OVER no está listo porque no se detecta amenaza ofensiva suficiente."

    def _has_live_stats(
        self,
        shots: float,
        shots_on_target: float,
        corners: float,
        xg: float,
        dangerous_attacks: float,
    ) -> bool:
        return (
            shots > 0
            or shots_on_target > 0
            or corners > 0
            or xg > 0.05
            or dangerous_attacks > 0
        )
