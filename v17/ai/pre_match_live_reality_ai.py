from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PreMatchLiveRealityAI:
    """
    V17 - PreMatchLiveRealityAI

    Rol:
    - EVIDENCE_ONLY.
    - No decide.
    - No publica.
    - No modifica official_*.
    - No reemplaza a MasterDecisionAI.

    Objetivo:
    Comparar expectativa prepartido contra realidad live para entregar
    evidencia contextual interpretable por el sistema.
    """

    VERSION = "V17_PRE_MATCH_LIVE_REALITY_AI_1_EVIDENCE_ONLY"
    ROLE = "EVIDENCE_ONLY"

    def analyze(
        self,
        pre_match: Dict[str, Any] | None = None,
        live: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        pre_match = pre_match or {}
        live = live or {}

        support_points: List[str] = []
        warnings: List[str] = []

        over_pre = self._to_float(pre_match.get("over_pre_match_score"))
        under_pre = self._to_float(pre_match.get("under_pre_match_score"))
        behavior = self._upper(pre_match.get("pre_match_recommended_behavior"))

        league_goal_profile = self._upper(pre_match.get("league_goal_profile"))
        team_goal_profile = self._upper(pre_match.get("team_goal_profile"))
        first_half_goal_risk = self._to_float(pre_match.get("first_half_goal_risk"))
        second_half_goal_risk = self._to_float(pre_match.get("second_half_goal_risk"))

        minute = self._to_int(self._pick(live, ["minute", "minuto", "api_minute"]))
        home_score, away_score = self._extract_score(live)
        total_goals = home_score + away_score

        total_shots = self._to_float(self._pick(live, ["total_shots", "shots"]))
        total_shots_on = self._to_float(
            self._pick(live, ["total_shots_on", "shots_on_target"])
        )
        total_dangerous_attacks = self._to_float(
            self._pick(live, ["total_dangerous_attacks", "dangerous_attacks"])
        )
        total_corners = self._to_float(self._pick(live, ["total_corners", "corners"]))
        total_xg = self._to_float(self._pick(live, ["total_xg", "xg", "xG"]))

        pressure_score = self._to_float(live.get("pressure_score"))
        rhythm_score = self._to_float(live.get("rhythm_score"))
        risk = self._upper(live.get("risk"))
        match_reader = self._upper(live.get("match_reader"))
        market = self._upper(live.get("market"))

        pre_match_expectation = self._classify_pre_match_expectation(
            over_pre=over_pre,
            under_pre=under_pre,
            behavior=behavior,
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            support_points=support_points,
            warnings=warnings,
        )

        live_intensity = self._calculate_live_intensity(
            minute=minute,
            total_shots=total_shots,
            total_shots_on=total_shots_on,
            total_dangerous_attacks=total_dangerous_attacks,
            total_corners=total_corners,
            total_xg=total_xg,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
        )

        match_direction = self._classify_match_direction(
            minute=minute,
            total_goals=total_goals,
            live_intensity=live_intensity,
            risk=risk,
            match_reader=match_reader,
            support_points=support_points,
        )

        score_fairness = self._classify_score_fairness(
            total_goals=total_goals,
            total_xg=total_xg,
            total_shots_on=total_shots_on,
            live_intensity=live_intensity,
            support_points=support_points,
            warnings=warnings,
        )

        live_reality = self._classify_live_reality(
            pre_match_expectation=pre_match_expectation,
            match_direction=match_direction,
            live_intensity=live_intensity,
            minute=minute,
            total_goals=total_goals,
            market=market,
            support_points=support_points,
        )

        favorite_status = self._classify_favorite_status(
            behavior=behavior,
            minute=minute,
            total_goals=total_goals,
            live_intensity=live_intensity,
            score_fairness=score_fairness,
            warnings=warnings,
        )

        momentum_shift = self._classify_momentum_shift(
            pre_match_expectation=pre_match_expectation,
            live_reality=live_reality,
            match_direction=match_direction,
            live_intensity=live_intensity,
        )

        reality_confidence = self._calculate_confidence(
            pre_match=pre_match,
            live=live,
            live_intensity=live_intensity,
            warnings=warnings,
        )

        reality_panel_note = self._build_panel_note(
            pre_match_expectation=pre_match_expectation,
            live_reality=live_reality,
            match_direction=match_direction,
            score_fairness=score_fairness,
            favorite_status=favorite_status,
            reality_confidence=reality_confidence,
        )

        return {
            "reality_role": self.ROLE,
            "reality_is_official_decision": False,
            "reality_can_publish": False,
            "pre_match_expectation": pre_match_expectation,
            "live_reality": live_reality,
            "favorite_status": favorite_status,
            "score_fairness": score_fairness,
            "momentum_shift": momentum_shift,
            "match_direction": match_direction,
            "reality_confidence": reality_confidence,
            "reality_support_points": support_points[:8],
            "reality_warnings": warnings[:8],
            "reality_panel_note": reality_panel_note,
        }

    def _classify_pre_match_expectation(
        self,
        *,
        over_pre: float,
        under_pre: float,
        behavior: str,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_goal_risk: float,
        second_half_goal_risk: float,
        support_points: List[str],
        warnings: List[str],
    ) -> str:
        if over_pre <= 0 and under_pre <= 0 and not behavior:
            warnings.append("No hay suficiente contexto prepartido para una lectura fuerte.")
            return "BALANCED_EXPECTED"

        if "FAVORITE" in behavior or "FAVORITO" in behavior:
            support_points.append("El prepartido sugiere expectativa asociada al favorito.")
            return "FAVORITE_WIN_EXPECTED"

        over_profile = "OVER" in league_goal_profile or "OVER" in team_goal_profile
        under_profile = "UNDER" in league_goal_profile or "UNDER" in team_goal_profile

        if over_pre >= 62 and over_pre >= under_pre + 8:
            support_points.append(f"Prepartido inclinado al OVER: {round(over_pre, 1)}.")
            return "OVER_EXPECTED"

        if under_pre >= 62 and under_pre >= over_pre + 8:
            support_points.append(f"Prepartido inclinado al UNDER: {round(under_pre, 1)}.")
            return "UNDER_EXPECTED"

        if over_profile and not under_profile:
            support_points.append("Perfil de liga/equipos con tendencia previa hacia goles.")
            return "OVER_EXPECTED"

        if under_profile and not over_profile:
            support_points.append("Perfil de liga/equipos con tendencia previa de control.")
            return "UNDER_EXPECTED"

        if max(first_half_goal_risk, second_half_goal_risk) >= 70:
            support_points.append("Riesgo prepartido de gol elevado por tramo del partido.")
            return "OVER_EXPECTED"

        support_points.append("El prepartido no muestra una ventaja clara.")
        return "BALANCED_EXPECTED"

    def _calculate_live_intensity(
        self,
        *,
        minute: int,
        total_shots: float,
        total_shots_on: float,
        total_dangerous_attacks: float,
        total_corners: float,
        total_xg: float,
        pressure_score: float,
        rhythm_score: float,
    ) -> float:
        minute_factor = max(minute, 1)

        shot_rate = min(35.0, (total_shots / minute_factor) * 90.0 * 1.2)
        shot_on_rate = min(28.0, total_shots_on * 7.0)
        attack_rate = min(22.0, (total_dangerous_attacks / minute_factor) * 90.0 * 0.35)
        corner_score = min(10.0, total_corners * 2.0)
        xg_score = min(25.0, total_xg * 18.0)

        pressure_component = min(20.0, pressure_score * 0.20)
        rhythm_component = min(20.0, rhythm_score * 0.20)

        return round(
            min(
                100.0,
                shot_rate
                + shot_on_rate
                + attack_rate
                + corner_score
                + xg_score
                + pressure_component
                + rhythm_component,
            ),
            2,
        )

    def _classify_match_direction(
        self,
        *,
        minute: int,
        total_goals: int,
        live_intensity: float,
        risk: str,
        match_reader: str,
        support_points: List[str],
    ) -> str:
        if "BLOCK" in risk or "BLOQUE" in risk or "BLOCK" in match_reader:
            support_points.append("La lectura live contiene señales de bloqueo.")
            return "CLOSING"

        if live_intensity >= 78:
            support_points.append(f"Ritmo live muy alto: intensidad {live_intensity}.")
            return "CHAOTIC"

        if live_intensity >= 58:
            support_points.append(f"El partido muestra señales de ruptura: intensidad {live_intensity}.")
            return "BREAKING"

        if minute >= 60 and live_intensity <= 35:
            support_points.append("El partido entra en tramo de cierre con baja producción ofensiva.")
            return "CLOSING"

        if total_goals >= 3 and live_intensity >= 45:
            support_points.append("Marcador con varios goles y actividad suficiente para sostener apertura.")
            return "BREAKING"

        support_points.append("La realidad live se mantiene estable.")
        return "STABLE"

    def _classify_score_fairness(
        self,
        *,
        total_goals: int,
        total_xg: float,
        total_shots_on: float,
        live_intensity: float,
        support_points: List[str],
        warnings: List[str],
    ) -> str:
        if total_xg <= 0:
            warnings.append("No hay xG confiable disponible para evaluar justicia del marcador.")
            if total_goals == 0 and total_shots_on >= 4:
                return "MISLEADING_SCORE"
            return "FAIR_SCORE"

        if total_goals == 0 and total_xg >= 1.0 and total_shots_on >= 3:
            support_points.append("El 0-0 parece engañoso por xG y tiros al arco.")
            return "MISLEADING_SCORE"

        if total_xg >= total_goals + 0.85:
            support_points.append("La producción ofensiva supera claramente el marcador actual.")
            return "UNDERSTATED_DOMINANCE"

        if total_goals >= total_xg + 1.25 and live_intensity < 55:
            support_points.append("El marcador parece alto para la amenaza real generada.")
            return "OVERSTATED_DOMINANCE"

        return "FAIR_SCORE"

    def _classify_live_reality(
        self,
        *,
        pre_match_expectation: str,
        match_direction: str,
        live_intensity: float,
        minute: int,
        total_goals: int,
        market: str,
        support_points: List[str],
    ) -> str:
        live_supports_goals = match_direction in {"BREAKING", "CHAOTIC"} or live_intensity >= 58
        live_supports_control = match_direction == "CLOSING" or live_intensity <= 35

        if pre_match_expectation == "OVER_EXPECTED":
            if live_supports_goals:
                return "LIVE_CONFIRMS_PREMATCH"
            if minute >= 25 and live_supports_control:
                return "LIVE_CONTRADICTS_PREMATCH"

        if pre_match_expectation == "UNDER_EXPECTED":
            if live_supports_control:
                return "LIVE_CONFIRMS_PREMATCH"
            if live_supports_goals:
                return "LIVE_CONTRADICTS_PREMATCH"

        if pre_match_expectation == "BALANCED_EXPECTED" and match_direction == "CHAOTIC":
            support_points.append("El live rompió una expectativa prepartido equilibrada.")
            return "LIVE_REVERSAL"

        if "OVER" in market and live_supports_goals:
            return "LIVE_CONFIRMS_PREMATCH"

        if "UNDER" in market and live_supports_control:
            return "LIVE_CONFIRMS_PREMATCH"

        if total_goals >= 2 and live_intensity >= 50:
            return "LIVE_NEUTRAL"

        return "LIVE_NEUTRAL"

    def _classify_favorite_status(
        self,
        *,
        behavior: str,
        minute: int,
        total_goals: int,
        live_intensity: float,
        score_fairness: str,
        warnings: List[str],
    ) -> str:
        has_favorite_context = "FAVORITE" in behavior or "FAVORITO" in behavior

        if not has_favorite_context:
            warnings.append("No se recibió favorito explícito; favorite_status se mantiene neutral.")
            return "NO_CLEAR_FAVORITE"

        if minute >= 30 and total_goals == 0 and live_intensity <= 38:
            return "FAVORITE_BLOCKED"

        if score_fairness in {"MISLEADING_SCORE", "OVERSTATED_DOMINANCE"}:
            return "FAVORITE_AT_RISK"

        if live_intensity >= 58:
            return "FAVORITE_CONFIRMED"

        return "FAVORITE_AT_RISK"

    def _classify_momentum_shift(
        self,
        *,
        pre_match_expectation: str,
        live_reality: str,
        match_direction: str,
        live_intensity: float,
    ) -> str:
        if live_reality == "LIVE_CONFIRMS_PREMATCH":
            return "PREMATCH_CONFIRMED_BY_LIVE"

        if live_reality == "LIVE_CONTRADICTS_PREMATCH":
            return "LIVE_WEAKER_THAN_PREMATCH"

        if live_reality == "LIVE_REVERSAL":
            return "LIVE_STRONGER_THAN_PREMATCH"

        if pre_match_expectation == "UNDER_EXPECTED" and match_direction in {"BREAKING", "CHAOTIC"}:
            return "LIVE_STRONGER_THAN_PREMATCH"

        if pre_match_expectation == "OVER_EXPECTED" and match_direction == "CLOSING":
            return "LIVE_WEAKER_THAN_PREMATCH"

        if live_intensity >= 70:
            return "LIVE_ACCELERATING"

        if live_intensity <= 32:
            return "LIVE_COOLING_DOWN"

        return "NO_CLEAR_SHIFT"

    def _calculate_confidence(
        self,
        *,
        pre_match: Dict[str, Any],
        live: Dict[str, Any],
        live_intensity: float,
        warnings: List[str],
    ) -> int:
        pre_fields = [
            "over_pre_match_score",
            "under_pre_match_score",
            "pre_match_recommended_behavior",
            "league_goal_profile",
            "team_goal_profile",
            "first_half_goal_risk",
            "second_half_goal_risk",
        ]

        live_fields = [
            "minute",
            "total_shots",
            "total_shots_on",
            "total_dangerous_attacks",
            "total_corners",
            "total_xg",
            "pressure_score",
            "rhythm_score",
            "risk",
            "match_reader",
            "market",
        ]

        pre_available = sum(1 for key in pre_fields if pre_match.get(key) is not None)
        live_available = sum(1 for key in live_fields if live.get(key) is not None)

        confidence = 35
        confidence += min(20, pre_available * 3)
        confidence += min(28, live_available * 3)

        if live_intensity >= 60 or live_intensity <= 35:
            confidence += 8

        confidence -= min(15, len(warnings) * 4)

        return max(20, min(88, int(confidence)))

    def _build_panel_note(
        self,
        *,
        pre_match_expectation: str,
        live_reality: str,
        match_direction: str,
        score_fairness: str,
        favorite_status: str,
        reality_confidence: int,
    ) -> str:
        return (
            "Lectura de evidencia solamente: "
            f"el prepartido marca {pre_match_expectation}, "
            f"el live responde como {live_reality}, "
            f"la dirección actual es {match_direction}, "
            f"el marcador se interpreta como {score_fairness} "
            f"y el favorito queda en estado {favorite_status}. "
            f"Confianza contextual: {reality_confidence}%. "
            "Esta capa no decide, no publica y no reemplaza la decisión oficial."
        )

    def _extract_score(self, live: Dict[str, Any]) -> Tuple[int, int]:
        home_score = live.get("home_score")
        away_score = live.get("away_score")

        if home_score is not None or away_score is not None:
            return self._to_int(home_score), self._to_int(away_score)

        score = str(live.get("score") or live.get("marcador") or "").strip()
        if "-" in score:
            left, right = score.split("-", 1)
            return self._to_int(left), self._to_int(right)

        return 0, 0

    def _pick(self, data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        for key in keys:
            if key in data and data.get(key) is not None:
                return data.get(key)
        return default

    def _upper(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(str(value).replace("%", "").strip())
        except Exception:
            return default

    def _to_int(self, value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(float(str(value).strip()))
        except Exception:
            return default
