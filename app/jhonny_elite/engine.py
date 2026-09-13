from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config.config import Config
from app.jhonny_elite.live_dynamics import LiveDynamicsMemory
from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine
from app.v17.ai.market_ai import MarketAI
from app.v17.ai.pre_match_profile_ai import PreMatchProfileAI
from app.v17.ai.risk_ai import RiskAI
from app.v17.ai.tactical_ai import TacticalAI
from app.v17.core.clock_guard import ClockGuard
from app.v17.core.context_reader import ContextReader
from app.v17.core.data_quality_guard import DataQualityGuard
from app.v17.services.candidate_odds_service import CandidateOddsService
from app.v17.services.pre_match_data_service import PreMatchDataService


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def si(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JhonnyEliteEngine:
    """Motor unificado JHONNY ELITE.

    Protocolo operativo:
    1. Lee TODOS los partidos live elegibles.
    2. Hace una lectura económica live (contexto/táctica/mercado/riesgo).
    3. Solo si aparece un candidato OVER/UNDER consulta prepartido y cuota.
    4. Ejecuta el modelo matemático hazard/Poisson.
    5. Una única decisión final publica, observa o descarta.

    El motor es deliberadamente selectivo. No promete certeza; cuantifica la
    evidencia disponible y se abstiene cuando la ventaja no es suficiente.
    """

    VERSION = "JHONNY_ELITE_19.0"

    def __init__(self) -> None:
        self.clock_guard = ClockGuard()
        self.data_quality_guard = DataQualityGuard()
        self.context_reader = ContextReader()
        self.tactical_ai = TacticalAI()
        self.market_ai = MarketAI()
        self.risk_ai = RiskAI()
        self.pre_match_data_service = PreMatchDataService()
        self.pre_match_profile_ai = PreMatchProfileAI()
        self.math_engine = AdvancedProbabilityEngine()
        self.live_dynamics = LiveDynamicsMemory()
        self.odds_service = CandidateOddsService()

    def process_live_matches(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        analyzed: List[Dict[str, Any]] = []
        for raw in matches or []:
            if not isinstance(raw, dict):
                continue
            try:
                item = self.analyze_match(raw)
                if item:
                    analyzed.append(item)
            except Exception as exc:
                # Un partido defectuoso nunca debe detener el escaneo global.
                analyzed.append(self._error_item(raw, exc))

        published = sorted(
            [x for x in analyzed if x.get("can_publish")],
            key=lambda x: (sf(x.get("official_confidence")), sf(x.get("value_edge"))),
            reverse=True,
        )
        observe = sorted(
            [x for x in analyzed if x.get("decision_status") == "OBSERVE" and not x.get("can_publish")],
            key=lambda x: sf(x.get("candidate_score")),
            reverse=True,
        )
        blocked = [x for x in analyzed if x.get("decision_status") == "BLOCKED"]
        no_bet = [x for x in analyzed if x.get("decision_status") == "NO_BET"]

        return {
            "ok": True,
            "version": self.VERSION,
            "updated_at": now_iso(),
            "live_count": len(matches or []),
            "analyzed_count": len(analyzed),
            "top_signals": published,
            "observe": observe,
            "no_bet": no_bet,
            "blocked": blocked,
            "all_analyzed": analyzed,
            "summary": {
                "published": len(published),
                "observe": len(observe),
                "no_bet": len(no_bet),
                "blocked": len(blocked),
                "over": sum(1 for x in published if x.get("market") == "OVER"),
                "under": sum(1 for x in published if x.get("market") == "UNDER"),
                "prematch_enrichments": sum(1 for x in analyzed if x.get("pre_match_triggered")),
            },
        }

    def analyze_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        match = self._normalize_aliases(deepcopy(match))
        match = self.live_dynamics.enrich(match)
        minute = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)

        clock = self.clock_guard.evaluate(match)
        quality = self.data_quality_guard.evaluate(match)
        context = self.context_reader.evaluate(match)
        tactical = self.tactical_ai.evaluate(match, context)
        market_read = self.market_ai.evaluate(match, context, tactical)
        risk = self.risk_ai.evaluate(match, clock, quality, context, tactical, market_read)

        live_scores = self._live_candidate_scores(match, context, tactical, market_read, risk)
        direction, candidate_score = self._candidate_direction(live_scores, minute)
        blockers = self._critical_blockers(clock, quality, risk, minute, direction)

        candidate = (
            direction in {"OVER", "UNDER"}
            and candidate_score >= sf(getattr(Config, "CANDIDATE_PREMATCH_MIN_CONFIDENCE", 58), 58)
            and not blockers
        )

        pre_match_profile = self._empty_prematch()
        math = self.math_engine.evaluate(match, context, tactical, pre_match_profile)
        odds = self._empty_odds(direction, match)

        if candidate:
            pre_match_profile = self._load_prematch(match)
            math = self.math_engine.evaluate(match, context, tactical, pre_match_profile)
            model_probability = (
                sf(math.get("math_support_over")) if direction == "OVER"
                else sf(math.get("math_support_under"))
            )
            odds = self.odds_service.enrich(match, direction, model_probability)

        decision = self._master_decision(
            match=match,
            direction=direction,
            candidate_score=candidate_score,
            candidate=candidate,
            blockers=blockers,
            clock=clock,
            quality=quality,
            context=context,
            tactical=tactical,
            market_read=market_read,
            risk=risk,
            pre_match=pre_match_profile,
            math=math,
            odds=odds,
        )

        home = si(match.get("home_score"), 0)
        away = si(match.get("away_score"), 0)
        line = sf(odds.get("line"), home + away + 0.5)
        signal_key = f"JE19:{match.get('match_id')}:{decision['market']}:{line:.1f}:{home + away}"

        support, cautions = self._explain(
            direction=direction,
            match=match,
            context=context,
            tactical=tactical,
            market_read=market_read,
            risk=risk,
            pre_match=pre_match_profile,
            math=math,
            odds=odds,
        )

        result = {
            **match,
            **clock,
            **quality,
            **context,
            **tactical,
            **market_read,
            **risk,
            "engine_version": self.VERSION,
            "decision_timestamp": now_iso(),
            "signal_key": signal_key,
            "market": decision["market"],
            "market_direction": decision["market"],
            "suggested_market": direction or "NO_BET",
            "decision_status": decision["status"],
            "official_status": decision["status"],
            "official_market": decision["market"],
            "official_confidence": decision["confidence"],
            "confidence": decision["confidence"],
            "can_publish": decision["can_publish"],
            "official_can_publish": decision["can_publish"],
            "candidate_score": round(candidate_score, 2),
            "candidate_detected": candidate,
            "pre_match_triggered": candidate,
            "pre_match_stage": "POST_CANDIDATE_ONLY" if candidate else "NOT_REQUESTED",
            "critical_blockers": blockers,
            "hard_blockers": blockers,
            "risk_score": round(sf(risk.get("risk_score")), 2),
            "risk_level": decision["risk_level"],
            "signal_strength": decision["strength"],
            "signal_tier": decision["strength"],
            "support_points": support,
            "caution_points": cautions,
            "missing_points": cautions[:3],
            "main_reading": decision["reading"],
            "why_signal": decision["reading"],
            "pre_match_profile": pre_match_profile,
            **self._flatten_prematch(pre_match_profile),
            "mathematical_evidence": math,
            **math,
            "candidate_odds": odds,
            "line": line,
            "odds": sf(odds.get("odds"), 0.0),
            "odds_available": bool(odds.get("odds_available")),
            "implied_probability": sf(odds.get("implied_probability"), 0.0),
            "value_edge": sf(odds.get("value_edge"), 0.0),
            "has_positive_value": bool(odds.get("has_positive_value")),
            "official_probable_score": math.get("primary_final_score"),
            "prediction_final_score": math.get("primary_final_score"),
            "prediction_score": math.get("primary_final_score"),
            "prediction_alternative_score": self._first_alt_score(math),
            "alternative_scores": math.get("alternative_scores", []),
            "official_main_scenario": decision["scenario"],
            "official_next_goal_team": self._next_goal_team(match, math) if direction == "OVER" else None,
            "result_status": "PENDING" if decision["can_publish"] else "NOT_TRACKED",
        }
        return result

    def _live_candidate_scores(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, float]:
        minute = max(1, si(match.get("api_minute") or match.get("minute"), 1))
        shots = sf(match.get("shots") or match.get("total_shots"))
        sot = sf(match.get("shots_on_target") or match.get("total_shots_on"))
        xg = sf(match.get("xg") or match.get("xG"))
        dangerous = sf(match.get("dangerous_attacks") or match.get("total_dangerous_attacks"))
        corners = sf(match.get("corners"))

        # Rate-adjusted live threat. Evita favorecer automáticamente a partidos
        # tardíos solo por tener más estadísticas acumuladas.
        pace = clamp(
            (sot / minute * 90.0) * 7.0
            + (shots / minute * 90.0) * 1.4
            + (dangerous / minute * 90.0) * 0.16
            + (corners / minute * 90.0) * 1.1
            + min(30.0, xg * 14.0),
            0,
            100,
        )
        over_market = sf(market.get("over_score"), sf(context.get("over_context_score"), 0.0))
        under_market = sf(market.get("under_score"), sf(context.get("under_context_score"), 0.0))
        pressure = sf(context.get("pressure_score"), 0.0)
        rhythm = sf(context.get("rhythm_score"), 0.0)
        goal_need = sf(context.get("goal_need_score"), 0.0)
        hold = sf(context.get("score_hold_probability"), 0.0)
        under_transition = sf(context.get("under_transition_score"), 0.0)
        tactical_score = sf(tactical.get("tactical_score"), 0.0)
        false_pressure = sf(tactical.get("false_pressure_risk"), 0.0)
        risk_score = sf(risk.get("risk_score"), 0.0)
        dynamics_available = bool(match.get("dynamics_available"))
        recent_threat = sf(match.get("recent_threat_score"), 0.0)
        dynamic_instability = sf(match.get("dynamic_instability_score"), 0.0)

        over = (
            over_market * 0.34 + pressure * 0.13 + rhythm * 0.12
            + goal_need * 0.10 + tactical_score * 0.11 + pace * 0.20
            - false_pressure * 0.08 - risk_score * 0.07
        )
        if dynamics_available:
            over += recent_threat * 0.11 + dynamic_instability * 0.035 - 5.0
        if sot >= 4:
            over += 5
        if xg >= 1.25:
            over += 4
        if minute < 15:
            over -= 6

        under = (
            under_market * 0.35 + hold * 0.25 + under_transition * 0.18
            + max(0.0, 100.0 - pressure) * 0.08
            + max(0.0, 100.0 - rhythm) * 0.07
            + max(0.0, 100.0 - pace) * 0.07
            - risk_score * 0.05
        )
        if dynamics_available:
            under += max(0.0, 45.0 - recent_threat) * 0.08
            under -= recent_threat * 0.10 + dynamic_instability * 0.06
            if str(match.get("dynamic_match_state") or "") in {"CLOSING", "CLOSED"}:
                under += 5.0
            if str(match.get("dynamic_match_state") or "") in {"OPENING", "OPEN"}:
                under -= 7.0
        if minute < int(getattr(Config, "UNDER_MINUTE_MIN", 75)):
            under = min(under, 45.0)
        if sf(context.get("over_context_score")) >= 70 or pace >= 70:
            under -= 10

        return {"OVER": clamp(over), "UNDER": clamp(under), "PACE": pace}

    def _candidate_direction(self, scores: Dict[str, float], minute: int) -> tuple[Optional[str], float]:
        over = sf(scores.get("OVER"))
        under = sf(scores.get("UNDER"))
        under_minute = int(getattr(Config, "UNDER_MINUTE_MIN", 75))

        if minute < under_minute:
            return ("OVER", over) if over >= 50 else (None, max(over, under))
        if over >= under and over >= 50:
            return "OVER", over
        if under > over and under >= 50:
            return "UNDER", under
        return None, max(over, under)

    def _critical_blockers(
        self,
        clock: Dict[str, Any],
        quality: Dict[str, Any],
        risk: Dict[str, Any],
        minute: int,
        direction: Optional[str],
    ) -> List[str]:
        blockers: List[str] = []
        if not quality.get("data_valid", True):
            blockers.extend(quality.get("data_issues", []) or ["INVALID_DATA"])
        # Reloj: un warning blando no bloquea; freeze/edad/invalidez sí.
        for value in clock.get("clock_blockers", []) or []:
            if value not in blockers:
                blockers.append(str(value))
        for value in risk.get("hard_blockers", []) or []:
            if value and value not in blockers:
                blockers.append(str(value))
        if direction == "UNDER" and minute < int(getattr(Config, "UNDER_MINUTE_MIN", 75)):
            blockers.append("UNDER_BEFORE_MINUTE_WINDOW")
        return blockers

    def _master_decision(self, **kw: Any) -> Dict[str, Any]:
        direction = kw.get("direction")
        candidate_score = sf(kw.get("candidate_score"))
        candidate = bool(kw.get("candidate"))
        blockers = kw.get("blockers") or []
        risk = kw.get("risk") or {}
        pre = kw.get("pre_match") or {}
        math = kw.get("math") or {}
        odds = kw.get("odds") or {}
        context = kw.get("context") or {}
        minute = si((kw.get("match") or {}).get("api_minute") or (kw.get("match") or {}).get("minute"), 0)

        if blockers:
            return self._decision("NO_BET", "BLOCKED", 0.0, False, "BAJA", "ALTO", "Bloqueo crítico de datos/reloj.", "BLOCKED")
        if not candidate or direction not in {"OVER", "UNDER"}:
            return self._decision("NO_BET", "OBSERVE" if candidate_score >= 45 else "NO_BET", candidate_score, False, "BAJA", "MEDIO", "No existe todavía una ventaja suficiente para publicar.", "WAIT")

        math_support = sf(math.get("math_support_over" if direction == "OVER" else "math_support_under"), 50.0)
        pre_support = sf(pre.get("over_pre_match_score" if direction == "OVER" else "under_pre_match_score"), 50.0)
        if not pre.get("pre_match_available"):
            pre_support = 50.0  # ausencia de datos es no-crítica, no evidencia negativa.

        live_weight = 0.58
        math_weight = 0.22
        pre_weight = 0.15
        value_weight = 0.05
        value_component = 50.0
        if odds.get("odds_available"):
            value_component = clamp(50.0 + sf(odds.get("value_edge")) * 2.0, 20, 100)

        confidence = (
            candidate_score * live_weight
            + math_support * math_weight
            + pre_support * pre_weight
            + value_component * value_weight
        )

        risk_score = sf(risk.get("risk_score"), 0.0)
        confidence -= max(0.0, risk_score - 40.0) * 0.18

        # Si prepartido contradice claramente, no mata una señal live fuerte pero sí
        # exige más confianza. Es exactamente un filtro de refuerzo, no un selector.
        if pre.get("pre_match_available") and pre_support < 38:
            confidence -= 7
        if direction == "UNDER" and minute < int(getattr(Config, "UNDER_MINUTE_MIN", 75)):
            confidence = 0

        confidence = clamp(confidence)
        min_publish = sf(getattr(Config, "PUBLISH_MIN_CONFIDENCE", 68), 68)
        can_publish = confidence >= min_publish and risk_score < 72

        # Cuota: valor es obligatorio solo para etiquetar una señal como premium;
        # si no está disponible, no ocultamos una excelente lectura futbolística.
        if odds.get("odds_available") and sf(odds.get("value_edge")) < -4.0:
            confidence = clamp(confidence - 5)
            can_publish = confidence >= min_publish + 2

        if confidence >= sf(getattr(Config, "PREMIUM_SIGNAL_CONFIDENCE", 88), 88) and (
            not odds.get("odds_available") or odds.get("has_positive_value")
        ):
            strength = "FUERTE"
        elif confidence >= sf(getattr(Config, "STRONG_SIGNAL_CONFIDENCE", 82), 82):
            strength = "FUERTE"
        elif confidence >= min_publish:
            strength = "MEDIA"
        else:
            strength = "BAJA"

        risk_level = "BAJO" if risk_score < 35 else "MEDIO" if risk_score < 60 else "ALTO"
        status = "ENTER" if can_publish else "OBSERVE"
        market = direction if can_publish else "NO_BET"
        scenario = "MORE_GOALS_EXPECTED" if direction == "OVER" else "SCORE_HOLD_EXPECTED"
        reading = (
            f"{direction} validado por lectura live, contexto, modelo matemático y refuerzo prepartido."
            if can_publish else
            f"{direction} detectado como candidato, pero la confianza final aún no supera el umbral de publicación."
        )
        return self._decision(market, status, confidence, can_publish, strength, risk_level, reading, scenario)

    @staticmethod
    def _decision(market: str, status: str, confidence: float, can_publish: bool, strength: str, risk: str, reading: str, scenario: str) -> Dict[str, Any]:
        return {
            "market": market,
            "status": status,
            "confidence": round(clamp(confidence), 2),
            "can_publish": can_publish,
            "strength": strength,
            "risk_level": risk,
            "reading": reading,
            "scenario": scenario,
        }

    def _load_prematch(self, match: Dict[str, Any]) -> Dict[str, Any]:
        try:
            package = self.pre_match_data_service.get_pre_match_package(match)
            profile = self.pre_match_profile_ai.analyze(package, match)
            if isinstance(profile, dict):
                profile["pre_match_trigger_reason"] = "LIVE_CANDIDATE_DETECTED"
                for key in (
                    "home_team_statistics", "away_team_statistics", "provider_prediction",
                    "standings_context", "home_last_5", "away_last_5",
                    "home_home_last_5", "away_away_last_5", "head_to_head_last_5",
                ):
                    if key in package:
                        profile[key] = package.get(key)
                return profile
        except Exception as exc:
            return {**self._empty_prematch(), "pre_match_error": str(exc)[:240]}
        return self._empty_prematch()

    @staticmethod
    def _empty_prematch() -> Dict[str, Any]:
        return {
            "pre_match_available": False,
            "pre_match_ok": False,
            "pre_match_source": "NOT_REQUESTED_OR_UNAVAILABLE",
            "over_pre_match_score": 50.0,
            "under_pre_match_score": 50.0,
            "pre_match_support_points": [],
            "pre_match_caution_points": [],
        }

    @staticmethod
    def _empty_odds(direction: Optional[str], match: Dict[str, Any]) -> Dict[str, Any]:
        total = si(match.get("home_score"), 0) + si(match.get("away_score"), 0)
        return {
            "odds_available": False,
            "odds_status": "NOT_REQUESTED",
            "market_direction": direction or "NONE",
            "line": total + 0.5,
            "odds": 0.0,
            "implied_probability": 0.0,
            "value_edge": 0.0,
            "has_positive_value": False,
        }

    @staticmethod
    def _flatten_prematch(pre: Dict[str, Any]) -> Dict[str, Any]:
        wanted = [
            "pre_match_available", "pre_match_ok", "pre_match_source",
            "pre_match_avg_total_goals", "over_pre_match_score", "under_pre_match_score",
            "home_recent_over_25_rate", "away_recent_over_25_rate",
            "home_recent_btts_rate", "away_recent_btts_rate",
            "home_recent_goal_profile", "away_recent_goal_profile",
            "pre_match_support_points", "pre_match_caution_points",
            "home_team_statistics", "away_team_statistics", "provider_prediction",
            "standings_context", "home_last_5", "away_last_5",
            "home_home_last_5", "away_away_last_5", "head_to_head_last_5",
            "season_expected_total_goals",
        ]
        return {k: pre.get(k) for k in wanted if k in pre}

    def _explain(self, **kw: Any) -> tuple[List[str], List[str]]:
        direction = kw.get("direction")
        c = kw.get("context") or {}
        t = kw.get("tactical") or {}
        m = kw.get("market_read") or {}
        r = kw.get("risk") or {}
        p = kw.get("pre_match") or {}
        math = kw.get("math") or {}
        odds = kw.get("odds") or {}
        match = kw.get("match") or {}
        support: List[str] = []
        caution: List[str] = []
        if direction == "OVER":
            if sf(c.get("pressure_score")) >= 60: support.append("Presión live real elevada")
            if sf(c.get("rhythm_score")) >= 60: support.append("Ritmo ofensivo favorable")
            if sf(t.get("offensive_depth_score")) >= 55: support.append("Profundidad ofensiva confirmada")
            if sf(math.get("math_support_over")) >= 65: support.append("Modelo matemático favorece otro gol")
        elif direction == "UNDER":
            if sf(c.get("score_hold_probability")) >= 65: support.append("Alta probabilidad de conservar marcador")
            if sf(c.get("under_transition_score")) >= 65: support.append("Transición táctica hacia cierre")
            if sf(math.get("math_support_under")) >= 65: support.append("Modelo matemático favorece ausencia de más goles")
        support.extend((p.get("pre_match_support_points") or [])[:3])
        if odds.get("has_positive_value"): support.append("Cuota con valor matemático positivo")
        if match.get("dynamics_available") and sf(match.get("recent_threat_score")) >= 58:
            support.append("Amenaza reciente acelerándose entre escaneos")
        if match.get("post_goal_reanalysis"):
            caution.append("Reanálisis activado tras cambio de marcador")
        dynamic_state = str(match.get("dynamic_match_state") or "")
        if dynamic_state in {"OPENING", "OPEN"}:
            if direction == "OVER":
                support.append("El partido se está abriendo en la ventana reciente")
            elif direction == "UNDER":
                caution.append("La ventana reciente se está abriendo y contradice el UNDER")
        elif dynamic_state in {"CLOSING", "CLOSED"}:
            if direction == "UNDER":
                support.append("El ritmo reciente se está cerrando y respalda el UNDER")
            elif direction == "OVER":
                caution.append("El ritmo reciente se está cerrando y reduce fuerza al OVER")
        caution.extend((r.get("risk_reasons") or [])[:3])
        caution.extend((m.get("market_warnings") or [])[:2])
        caution.extend((p.get("pre_match_caution_points") or [])[:2])
        if not odds.get("odds_available"): caution.append("Cuota live no disponible: valor económico no confirmado")
        # Mantener mensajes compactos y únicos.
        return list(dict.fromkeys(map(str, support)))[:6], list(dict.fromkeys(map(str, caution)))[:6]

    @staticmethod
    def _first_alt_score(math: Dict[str, Any]) -> Optional[str]:
        alts = math.get("alternative_scores") or []
        if alts and isinstance(alts[0], dict):
            return alts[0].get("score")
        return None

    @staticmethod
    def _next_goal_team(match: Dict[str, Any], math: Dict[str, Any]) -> Optional[str]:
        hp = sf(math.get("home_next_goal_probability"))
        ap = sf(math.get("away_next_goal_probability"))
        if max(hp, ap) < 35:
            return None
        return match.get("home_team") if hp >= ap else match.get("away_team")

    @staticmethod
    def _normalize_aliases(match: Dict[str, Any]) -> Dict[str, Any]:
        match["match_id"] = match.get("match_id") or match.get("fixture_id") or match.get("id")
        match["fixture_id"] = match.get("fixture_id") or match.get("match_id")
        match["home_team"] = match.get("home_team") or match.get("home_name") or match.get("home")
        match["away_team"] = match.get("away_team") or match.get("away_name") or match.get("away")
        match["api_minute"] = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)
        match["effective_minute"] = match["api_minute"]
        # Guards históricos usan aliases total_*.
        match["total_shots"] = sf(match.get("total_shots"), sf(match.get("shots")))
        match["total_shots_on"] = sf(match.get("total_shots_on"), sf(match.get("shots_on_target")))
        match["total_dangerous_attacks"] = sf(match.get("total_dangerous_attacks"), sf(match.get("dangerous_attacks")))
        match["total_attacks"] = sf(match.get("total_attacks"), sf(match.get("attacks")))
        return match

    @staticmethod
    def _error_item(match: Dict[str, Any], exc: Exception) -> Dict[str, Any]:
        return {
            **(match or {}),
            "engine_version": JhonnyEliteEngine.VERSION,
            "decision_status": "BLOCKED",
            "official_status": "BLOCKED",
            "market": "NO_BET",
            "official_market": "NO_BET",
            "can_publish": False,
            "official_can_publish": False,
            "official_confidence": 0.0,
            "critical_blockers": ["ANALYSIS_ERROR"],
            "analysis_error": str(exc)[:300],
        }
