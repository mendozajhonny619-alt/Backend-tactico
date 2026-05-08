from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from app.services.match_window_engine import MatchWindowEngine
from app.services.match_context_engine import MatchContextEngine
from app.services.ai_match_engine import AIMatchEngine
from app.services.match_opportunity_service import MatchOpportunityService
from app.services.elite_signal_gate import EliteSignalGate
from app.services.under_signal_gate import UnderSignalGate
from app.services.signal_ranker_service import SignalRankerService
from app.services.elite_analyst_filter import EliteAnalystFilter
from app.services.match_scan_enhancer import MatchScanEnhancer
from app.services.match_reading_enhancer import MatchReadingEnhancer
from app.services.next_goal_context_helper import NextGoalContextHelper
from app.services.match_timeline_tracker import MatchTimelineTracker
from app.services.deep_live_match_analyzer import DeepLiveMatchAnalyzer
from app.services.player_live_analyzer import PlayerLiveAnalyzer
from app.services.final_decision_engine import FinalDecisionEngine

from app.engines.market_engine import MarketEngine
from app.engines.value_engine import ValueEngine
from app.engines.risk_engine import RiskEngine
from app.engines.tactical_engine import TacticalEngine
from app.engines.match_analyst_engine import MatchAnalystEngine
from app.engines.next_goal_side_engine import NextGoalSideEngine


class ScanService:
    """
    Corazón operativo del sistema.

    Ajuste:
    - No mata por LOW DATA si hay consenso fuerte.
    - OBSERVE fuerte puede convertirse en señal interna BUENA.
    - OVER/UNDER_CANDIDATE puede publicarse como INTERNAL si no hay mercado real.
    - Riesgo alto no publica; manda a observación.
    - Evita señales internas débiles.
    - Filtro final tipo analista élite antes de publicar.
    - Mejora lectura del partido con MatchReadingEnhancer sin bloquear señales.
    - Agrega lectura auxiliar de próximo gol sin modificar decisiones.
    - Agrega timeline/análisis profundo/jugadores como lectura auxiliar.
    - Agrega FinalDecisionEngine como juez maestro antes de publicar.
    """

    def __init__(self) -> None:
        self.window_engine = MatchWindowEngine()
        self.context_engine = MatchContextEngine()
        self.ai_engine = AIMatchEngine()
        self.risk_engine = RiskEngine()
        self.tactical_engine = TacticalEngine()
        self.analyst_engine = MatchAnalystEngine()
        self.opportunity_service = MatchOpportunityService()
        self.over_gate = EliteSignalGate()
        self.under_gate = UnderSignalGate()
        self.market_engine = MarketEngine()
        self.value_engine = ValueEngine()
        self.ranker = SignalRankerService()
        self.elite_analyst_filter = EliteAnalystFilter()
        self.scan_enhancer = MatchScanEnhancer()
        self.reading_enhancer = MatchReadingEnhancer()
        self.next_goal_engine = NextGoalSideEngine()
        self.next_goal_helper = NextGoalContextHelper()
        self.timeline_tracker = MatchTimelineTracker()
        self.deep_live_analyzer = DeepLiveMatchAnalyzer()
        self.player_live_analyzer = PlayerLiveAnalyzer()
        self.final_decision_engine = FinalDecisionEngine()

    def scan(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        candidates: List[Dict[str, Any]] = []
        opportunities: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for match in live_matches or []:
            result = self._process_match(match)

            status = result.get("status")
            if status == "BLOCKED":
                blocked.append(result)
            elif status == "OPPORTUNITY":
                opportunities.append(result["opportunity"])
            elif status == "CANDIDATE":
                candidates.append(result["signal"])

        published = self.ranker.rank(candidates)

        return {
            "published_signals": published,
            "opportunities": opportunities,
            "blocked": blocked,
            "stats": {
                "scanned_matches": len(live_matches or []),
                "publishable_candidates": len(candidates),
                "opportunities_count": len(opportunities),
                "blocked_matches": len(blocked),
                "published_count": len(published),
            },
        }

    def _process_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        match = self.scan_enhancer.enhance(match)

        match_id = match.get("match_id")
        if match_id is None:
            return self._block(match, "BLOCK_MATCH_ID_MISSING")

        context = self.context_engine.build(match)

        match = self.reading_enhancer.enhance({
            **match,
            **context,
        })

        window = self.window_engine.evaluate({
            **match,
            **context,
        })

        if not window.get("allowed", False):
            return self._block(match, "BLOCK_INVALID_WINDOW", context=context, window=window)

        if match.get("is_scannable") is False:
            ai = self.ai_engine.evaluate(context)

            next_goal = self.next_goal_engine.evaluate(
                match=match,
                context=context,
                ai=ai,
            )
            next_goal_context = self.next_goal_helper.interpret(
                next_goal=next_goal,
                opportunity={},
            )
            match.update(next_goal)
            match.update(next_goal_context)
            self._apply_auxiliary_live_analysis(match, context, ai)

            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="MATCH_NOT_SCANNABLE",
                )

        if not self._has_minimal_stats(match):
            ai = self.ai_engine.evaluate(context)

            next_goal = self.next_goal_engine.evaluate(
                match=match,
                context=context,
                ai=ai,
            )
            next_goal_context = self.next_goal_helper.interpret(
                next_goal=next_goal,
                opportunity={},
            )
            match.update(next_goal)
            match.update(next_goal_context)
            self._apply_auxiliary_live_analysis(match, context, ai)

            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="LOW_STATS_OBSERVATION",
                )

        ai = self.ai_engine.evaluate(context)
        ai_score = self._safe_float(ai.get("ai_score"))

        next_goal = self.next_goal_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
        )
        next_goal_context = self.next_goal_helper.interpret(
            next_goal=next_goal,
            opportunity={},
        )
        match.update(next_goal)
        match.update(next_goal_context)
        self._apply_auxiliary_live_analysis(match, context, ai)

        if str(context.get("data_quality") or "LOW").upper() == "LOW":
            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="LOW_DATA_OBSERVATION",
                )

        if ai_score < 42:
            return self._block(
                match,
                "BLOCK_AI_SCORE_TOO_LOW",
                context=context,
                ai=ai,
                window=window,
            )

        if ai_score < 55:
            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="AI_SCORE_UNDER_OPERABLE_THRESHOLD",
                )

        risk = self.risk_engine.evaluate(
            context=context,
            ai=ai,
            window=window,
            market=None,
        )

        if not risk.get("is_risk_acceptable", False):
            return self._observe(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical={},
                risk=risk,
                reason="RISK_UNDER_REVIEW",
            )

        tactical = self.tactical_engine.evaluate(
            context=context,
            window=window,
        )

        opportunity = self.opportunity_service.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
        )

        next_goal_context = self.next_goal_helper.interpret(
            next_goal=next_goal,
            opportunity=opportunity,
        )
        match.update(next_goal_context)

        analyst_pre = self.analyst_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            market=None,
            value=None,
        )

        if opportunity.get("type") in {"NO_BET", "REJECTED"}:
            if self._should_rescue_to_observe(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=analyst_pre,
                    reason="RECOVERED_TO_OBSERVE",
                )

            return self._block(
                match,
                opportunity.get("reason", "BLOCK_NO_OPPORTUNITY"),
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_pre,
                opportunity=opportunity,
            )

        if opportunity.get("type") == "OBSERVE":
            if self._should_promote_observe_to_internal_signal(match, context, ai):
                promoted_opportunity = {
                    "type": "OVER_CANDIDATE",
                    "rank": "BUENA",
                    "market": "OVER",
                    "reason": "OBSERVE_PROMOTED_BY_INTERNAL_CONSENSUS",
                }

                promoted_next_goal_context = self.next_goal_helper.interpret(
                    next_goal=next_goal,
                    opportunity=promoted_opportunity,
                )
                match.update(promoted_next_goal_context)

                return self._emit_internal_signal(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=None,
                    opportunity=promoted_opportunity,
                )

            return {
                "status": "OPPORTUNITY",
                "opportunity": self._build_opportunity_payload(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=analyst_pre,
                    opportunity=opportunity,
                    market=None,
                    value=None,
                ),
            }

        if self._should_emit_internal_signal(ai, context, opportunity):
            return self._emit_internal_signal(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=None,
                opportunity=opportunity,
            )

        market = self.market_engine.evaluate(
            match=match,
            market_type=opportunity.get("market"),
        )

        if not market.get("is_valid", False):
            if self._should_emit_internal_signal(ai, context, opportunity, allow_operable=True):
                return self._emit_internal_signal(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=None,
                    opportunity=opportunity,
                )

            analyst_market_fail = self.analyst_engine.evaluate(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                market=market,
                value=None,
            )

            payload = self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_market_fail,
                opportunity=opportunity,
                market=market,
                value=None,
            )
            payload["block_reason"] = market.get("reason", "BLOCK_NO_REAL_MARKET")

            return {
                "status": "OPPORTUNITY",
                "opportunity": payload,
            }

        risk = self.risk_engine.evaluate(
            context=context,
            ai=ai,
            window=window,
            market=market,
        )

        if not risk.get("is_risk_acceptable", False):
            payload = self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_pre,
                opportunity=opportunity,
                market=market,
                value=None,
            )
            payload["block_reason"] = "BLOCK_RISK_TOO_HIGH"
            return {
                "status": "OPPORTUNITY",
                "opportunity": payload,
            }

        value = self.value_engine.evaluate(
            ai=ai,
            market=market,
            market_type=opportunity.get("market"),
        )

        final_decision = self.final_decision_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
            risk=risk,
            tactical=tactical,
            opportunity=opportunity,
            market=market,
            value=value,
        )
        match.update(final_decision)

        analyst_full = self.analyst_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            market=market,
            value=value,
        )

        if self._should_hold_by_final_decision(final_decision):
            return self._final_decision_to_opportunity(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
                final_decision=final_decision,
            )

        if not value.get("is_value", False):
            if self._should_emit_internal_signal(ai, context, opportunity, allow_operable=True):
                return self._emit_internal_signal(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=analyst_full,
                    opportunity=opportunity,
                )

            payload = self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
            )
            payload["block_reason"] = value.get("reason") or value.get("status", "BLOCK_NO_VALUE")

            return {
                "status": "OPPORTUNITY",
                "opportunity": payload,
            }

        if opportunity.get("market") == "OVER":
            gate = self.over_gate.validate(
                context=context,
                ai=ai,
                window=window,
                market=market,
                value=value,
            )
        elif opportunity.get("market") == "UNDER":
            gate = self.under_gate.validate(
                context=context,
                ai=ai,
                window=window,
                market=market,
                value=value,
            )
        else:
            return self._block(
                match,
                "BLOCK_MARKET_TYPE_UNKNOWN",
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
            )

        if not gate.get("approved", False):
            if self._should_emit_internal_signal(ai, context, opportunity, allow_operable=True):
                return self._emit_internal_signal(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=analyst_full,
                    opportunity=opportunity,
                )

            payload = self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
            )
            payload["block_reason"] = gate.get("reason", "BLOCK_GATE_REJECT")
            return {
                "status": "OPPORTUNITY",
                "opportunity": payload,
            }

        signal = self._build_signal(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            analyst=analyst_full,
            opportunity=opportunity,
            market=market,
            value=value,
        )

        if signal.get("rank") in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}:
            if self._safe_float(signal.get("signal_score")) < 55:
                return {
                    "status": "OPPORTUNITY",
                    "opportunity": self._build_opportunity_payload(
                        match=match,
                        context=context,
                        ai=ai,
                        window=window,
                        tactical=tactical,
                        risk=risk,
                        analyst=analyst_full,
                        opportunity=opportunity,
                        market=market,
                        value=value,
                    ),
                }

            return self._apply_elite_analyst_filter(
                signal=signal,
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
            )

        return {
            "status": "OPPORTUNITY",
            "opportunity": self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_full,
                opportunity=opportunity,
                market=market,
                value=value,
            ),
        }

    def _should_hold_by_final_decision(self, final_decision: Dict[str, Any]) -> bool:
        decision = str(final_decision.get("final_decision") or "").upper()
        return decision in {"OBSERVE", "WAIT", "NO_REENTRY", "AVOID"}

    def _final_decision_to_opportunity(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        analyst: Dict[str, Any],
        opportunity: Dict[str, Any],
        market: Dict[str, Any] | None,
        value: Dict[str, Any] | None,
        final_decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self._build_opportunity_payload(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            analyst=analyst,
            opportunity=opportunity,
            market=market,
            value=value,
        )
        payload["block_reason"] = final_decision.get("final_decision_reason", "FINAL_DECISION_HOLD")
        payload["final_decision_status"] = final_decision.get("final_decision")
        payload.update(final_decision)

        return {
            "status": "OPPORTUNITY",
            "opportunity": payload,
        }

    def _apply_elite_analyst_filter(
        self,
        signal: Dict[str, Any],
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        analyst: Dict[str, Any],
        opportunity: Dict[str, Any],
        market: Dict[str, Any],
        value: Dict[str, Any],
    ) -> Dict[str, Any]:
        analyst_filter = self.elite_analyst_filter.validate(
            signal=signal,
            context=context,
            ai=ai,
            risk=risk,
        )

        action = analyst_filter.get("action")
        new_rank = analyst_filter.get("rank")
        reason = analyst_filter.get("reason")

        if action == "APPROVE":
            signal["elite_analyst_status"] = "APPROVED"
            signal["elite_analyst_reason"] = reason
            return {
                "status": "CANDIDATE",
                "signal": signal,
            }

        if action == "DOWNGRADE" and new_rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}:
            signal["rank"] = new_rank
            signal["elite_analyst_status"] = "DOWNGRADED"
            signal["elite_analyst_reason"] = reason
            return {
                "status": "CANDIDATE",
                "signal": signal,
            }

        payload = self._build_opportunity_payload(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            analyst=analyst,
            opportunity=opportunity,
            market=market,
            value=value,
        )
        payload["block_reason"] = reason or "ELITE_ANALYST_FILTER_REJECT"
        payload["elite_analyst_status"] = action or "REJECT"

        return {
            "status": "OPPORTUNITY",
            "opportunity": payload,
        }

    def _emit_internal_signal(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        analyst: Dict[str, Any] | None,
        opportunity: Dict[str, Any],
    ) -> Dict[str, Any]:
        fake_market = {
            "is_valid": True,
            "market_type": opportunity.get("market"),
            "line": "AUTO",
            "odds": 0.0,
            "bookmaker": None,
            "market_status": "INTERNAL_ONLY",
            "reason": None,
            "raw_market": None,
        }

        fake_value = {
            "is_value": True,
            "edge": 0.0,
            "value_category": "INTERNAL",
            "status": "INTERNAL_OK",
            "reason": None,
        }

        analyst_internal = analyst or self.analyst_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            market=fake_market,
            value=fake_value,
        )

        final_decision = self.final_decision_engine.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
            risk=risk,
            tactical=tactical,
            opportunity=opportunity,
            market=fake_market,
            value=fake_value,
        )
        match.update(final_decision)

        if self._should_hold_by_final_decision(final_decision):
            return self._final_decision_to_opportunity(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                analyst=analyst_internal,
                opportunity=opportunity,
                market=fake_market,
                value=fake_value,
                final_decision=final_decision,
            )

        signal = self._build_signal(
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            analyst=analyst_internal,
            opportunity=opportunity,
            market=fake_market,
            value=fake_value,
        )

        if self._safe_float(signal.get("signal_score")) < 55:
            return {
                "status": "OPPORTUNITY",
                "opportunity": self._build_opportunity_payload(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    tactical=tactical,
                    risk=risk,
                    analyst=analyst_internal,
                    opportunity=opportunity,
                    market=fake_market,
                    value=fake_value,
                ),
            }

        signal["signal_mode"] = "INTERNAL"
        signal["odds"] = None
        signal["bookmaker"] = "INTERNAL"
        signal["line"] = "AUTO"

        return self._apply_elite_analyst_filter(
            signal=signal,
            match=match,
            context=context,
            ai=ai,
            window=window,
            tactical=tactical,
            risk=risk,
            analyst=analyst_internal,
            opportunity=opportunity,
            market=fake_market,
            value=fake_value,
        )

    def _observe(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any] | None = None,
        risk: Dict[str, Any] | None = None,
        analyst: Dict[str, Any] | None = None,
        reason: str = "OBSERVE",
    ) -> Dict[str, Any]:
        opportunity = {
            "type": "OBSERVE",
            "rank": "OBSERVACION",
            "market": None,
            "reason": reason,
        }

        fallback_risk = risk or self._fallback_risk_from_ai(ai)

        return {
            "status": "OPPORTUNITY",
            "opportunity": self._build_opportunity_payload(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical or {},
                risk=fallback_risk,
                analyst=analyst or {},
                opportunity=opportunity,
                market=None,
                value=None,
            ),
        }

    def _fallback_risk_from_ai(self, ai: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "risk_score": ai.get("risk_score"),
            "risk_level": ai.get("risk_level"),
            "risk_flags": [],
        }

    def _apply_auxiliary_live_analysis(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> None:
        timeline = self.timeline_tracker.update(
            match=match,
            context=context,
            ai=ai,
        )

        deep_analysis = self.deep_live_analyzer.analyze(
            match=match,
            context=context,
            ai=ai,
            timeline=timeline,
        )

        player_analysis = self.player_live_analyzer.analyze(
            match=match,
            context=context,
            ai=ai,
        )

        match.update(timeline)
        match.update(deep_analysis)
        match.update(player_analysis)

    def _should_continue_despite_low_data(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> bool:
        minute = self._extract_minute(match)
        ai_score = self._safe_float(ai.get("ai_score"))
        goal_prob = self._safe_float(ai.get("goal_probability"))
        over_prob = self._safe_float(ai.get("over_probability"))
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        context_state = str(context.get("context_state") or "").upper()

        if minute < 15:
            return False

        if ai_score >= 80 and goal_prob >= 80 and over_prob >= 80:
            return True

        if (
            ai_score >= 62
            and goal_prob >= 62
            and over_prob >= 62
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if (
            ai_score >= 58
            and pressure >= 9
            and rhythm >= 5
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        return False

    def _should_rescue_to_observe(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> bool:
        minute = self._extract_minute(match)
        ai_score = self._safe_float(ai.get("ai_score"))
        goal_prob = self._safe_float(ai.get("goal_probability"))
        over_prob = self._safe_float(ai.get("over_probability"))
        under_prob = self._safe_float(ai.get("under_probability"))
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        context_state = str(context.get("context_state") or "").upper()

        over_watch = (
            minute >= 15
            and ai_score >= 50
            and (goal_prob >= 54 or over_prob >= 54)
            and context_state in {"CONTROLADO", "TIBIO", "CALIENTE", "MUY_CALIENTE"}
        )

        under_watch = (
            minute >= 55
            and ai_score >= 52
            and under_prob >= 58
            and pressure <= 20
            and rhythm <= 15
            and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
        )

        return over_watch or under_watch

    def _should_promote_observe_to_internal_signal(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> bool:
        minute = self._extract_minute(match)
        ai_score = self._safe_float(ai.get("ai_score"))
        goal_prob = self._safe_float(ai.get("goal_probability"))
        over_prob = self._safe_float(ai.get("over_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "").upper()
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        context_state = str(context.get("context_state") or "").upper()

        if risk_level == "ALTO" and risk_score >= 7.0:
            return False

        if (
            20 <= minute <= 85
            and ai_score >= 62
            and goal_prob >= 66
            and over_prob >= 66
            and pressure >= 10
            and rhythm >= 6
            and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if (
            58 <= minute <= 85
            and ai_score >= 60
            and self._safe_float(ai.get("under_probability")) >= 65
            and goal_prob <= 52
            and pressure <= 14
            and rhythm <= 10
            and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
        ):
            return True

        return False

    def _should_emit_internal_signal(
        self,
        ai: Dict[str, Any],
        context: Dict[str, Any],
        opportunity: Dict[str, Any],
        allow_operable: bool = False,
    ) -> bool:
        ai_score = self._safe_float(ai.get("ai_score"))
        goal_prob = self._safe_float(ai.get("goal_probability"))
        over_prob = self._safe_float(ai.get("over_probability"))
        under_prob = self._safe_float(ai.get("under_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "").upper()

        data_quality = str(context.get("data_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "").upper()
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        market_type = str(opportunity.get("market") or "").upper()
        rank = str(opportunity.get("rank") or "").upper()

        if risk_level == "ALTO" and risk_score >= 7.5:
            return False

        allowed_ranks = {"PREMIUM", "FUERTE", "BUENA"}
        if allow_operable:
            allowed_ranks.add("OPERABLE")

        if rank not in allowed_ranks:
            return False

        if market_type == "OVER":
            return (
                ai_score >= 60
                and goal_prob >= 64
                and over_prob >= 64
                and pressure >= 9
                and rhythm >= 6
                and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
                and data_quality in {"MEDIUM", "HIGH"}
            )

        if market_type == "UNDER":
            return (
                ai_score >= 60
                and under_prob >= 65
                and goal_prob <= 55
                and context_state in {"CONTROLADO", "FRIO", "MUERTO", "TIBIO"}
                and data_quality in {"MEDIUM", "HIGH"}
                and pressure <= 14
                and rhythm <= 10
            )

        return False

    def _reading_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reading_strength": match.get("reading_strength"),
            "reading_label": match.get("reading_label"),
            "match_temperature": match.get("match_temperature"),
            "score_context": match.get("score_context"),
            "late_game_risk": match.get("late_game_risk"),
            "resolved_match_risk": match.get("resolved_match_risk"),
            "overextended_risk": match.get("overextended_risk"),
            "momentum_warning": match.get("momentum_warning"),
            "reading_advice": match.get("reading_advice"),
        }

    def _next_goal_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "next_goal_bias": match.get("next_goal_bias"),
            "next_goal_confidence": match.get("next_goal_confidence"),
            "score_hold_probability": match.get("score_hold_probability"),
            "next_goal_status": match.get("next_goal_status"),
            "next_goal_warning": match.get("next_goal_warning"),
            "home_next_goal_pressure": match.get("home_next_goal_pressure"),
            "away_next_goal_pressure": match.get("away_next_goal_pressure"),
            "next_goal_support": match.get("next_goal_support"),
            "next_goal_helper_advice": match.get("next_goal_helper_advice"),
            "next_goal_helper_warning": match.get("next_goal_helper_warning"),
        }

    def _auxiliary_live_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timeline_ready": match.get("timeline_ready"),
            "timeline_snapshots": match.get("timeline_snapshots"),
            "delta_3m": match.get("delta_3m"),
            "delta_5m": match.get("delta_5m"),
            "delta_10m": match.get("delta_10m"),
            "pressure_trend": match.get("pressure_trend"),
            "rhythm_trend": match.get("rhythm_trend"),
            "goal_threat_trend": match.get("goal_threat_trend"),
            "late_reactivation": match.get("late_reactivation"),
            "chaos_mode": match.get("chaos_mode"),
            "signal_life_status": match.get("signal_life_status"),
            "timeline_summary": match.get("timeline_summary"),
            "deep_analysis_enabled": match.get("deep_analysis_enabled"),
            "deep_projection_bias": match.get("deep_projection_bias"),
            "deep_projection_confidence": match.get("deep_projection_confidence"),
            "deep_projection_window": match.get("deep_projection_window"),
            "late_goal_risk": match.get("late_goal_risk"),
            "retention_risk": match.get("retention_risk"),
            "retention_risk_label": match.get("retention_risk_label"),
            "deep_pressure_trend": match.get("deep_pressure_trend"),
            "deep_rhythm_trend": match.get("deep_rhythm_trend"),
            "deep_goal_threat_trend": match.get("deep_goal_threat_trend"),
            "deep_signal_life_status": match.get("deep_signal_life_status"),
            "deep_late_reactivation": match.get("deep_late_reactivation"),
            "deep_chaos_mode": match.get("deep_chaos_mode"),
            "deep_fake_pressure_detected": match.get("deep_fake_pressure_detected"),
            "deep_pressure_without_depth": match.get("deep_pressure_without_depth"),
            "deep_event_profile": match.get("deep_event_profile"),
            "deep_tactical_alerts": match.get("deep_tactical_alerts"),
            "deep_analysis_summary": match.get("deep_analysis_summary"),
            "final_decision": match.get("final_decision"),
            "final_decision_reason": match.get("final_decision_reason"),
            "final_decision_confidence": match.get("final_decision_confidence"),
            "final_decision_market": match.get("final_decision_market"),
            "should_enter": match.get("should_enter"),
            "should_observe": match.get("should_observe"),
            "should_wait": match.get("should_wait"),
            "should_no_reentry": match.get("should_no_reentry"),
            "should_avoid": match.get("should_avoid"),
            "player_analysis_enabled": match.get("player_analysis_enabled"),
            "player_data_available": match.get("player_data_available"),
            "player_attacking_side": match.get("player_attacking_side"),
            "player_vulnerability_side": match.get("player_vulnerability_side"),
            "player_pressure_signal": match.get("player_pressure_signal"),
            "player_fatigue_signal": match.get("player_fatigue_signal"),
            "home_player_profile": match.get("home_player_profile"),
            "away_player_profile": match.get("away_player_profile"),
            "key_live_players": match.get("key_live_players"),
            "player_analysis_summary": match.get("player_analysis_summary"),
        }

    def _build_signal(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        analyst: Dict[str, Any],
        opportunity: Dict[str, Any],
        market: Dict[str, Any],
        value: Dict[str, Any],
    ) -> Dict[str, Any]:
        match_id = match.get("match_id")
        market_type = opportunity.get("market")
        signal_key = self._build_signal_key(match_id, market_type)

        signal_score = self._calculate_signal_score(
            ai=ai,
            context=context,
            value=value,
            rank=opportunity.get("rank"),
            market_type=market_type,
        )

        signal = {
            "signal_id": signal_key,
            "signal_key": signal_key,
            "match_id": match_id,
            "match_name": match.get("match_name") or self._build_match_name(match),
            "market": market_type,
            "minute": self._extract_minute(match),
            "rank": opportunity.get("rank"),
            "odds": market.get("odds"),
            "line": market.get("line"),
            "bookmaker": market.get("bookmaker"),
            "ai_score": ai.get("ai_score"),
            "goal_probability": ai.get("goal_probability"),
            "over_probability": ai.get("over_probability"),
            "under_probability": ai.get("under_probability"),
            "risk_score": risk.get("risk_score", ai.get("risk_score")),
            "risk_level": risk.get("risk_level", ai.get("risk_level")),
            "risk_flags": risk.get("risk_flags", []),
            "signal_score": signal_score,
            "tactical_state": tactical.get("tactical_state"),
            "tactical_bias": tactical.get("tactical_bias"),
            "tempo_label": tactical.get("tempo_label"),
            "market_alignment": tactical.get("market_alignment"),
            "window_phase": window.get("phase"),
            "window_reason": window.get("reason"),
            "data_quality": context.get("data_quality"),
            "game_quality": context.get("game_quality"),
            "dominance": context.get("dominance"),
            "attack_side": context.get("attack_side"),
            "context_state": context.get("context_state"),
            "live_decay_factor": context.get("live_decay_factor"),
            "cooling_detected": context.get("cooling_detected"),
            "under_transition_score": context.get("under_transition_score"),
            "momentum_label": ai.get("momentum_label"),
            "value_edge": value.get("edge"),
            "value_category": value.get("value_category"),
            "market_status": market.get("market_status"),
            "opportunity_reason": opportunity.get("reason"),
            "analyst_label": analyst.get("analyst_label"),
            "recommended_market": analyst.get("recommended_market"),
            "technical_summary": analyst.get("technical_summary"),
            "consensus_score": (analyst.get("consensus") or {}).get("consensus_score"),
            "result_prediction": ai.get("result_prediction"),
            "winner_prediction": ai.get("winner_prediction"),
            "signal_mode": "MARKET" if market.get("market_status") == "VALID" else "INTERNAL",
            "score": match.get("score"),
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
            "shots": match.get("shots"),
            "shots_on_target": match.get("shots_on_target"),
            "corners": match.get("corners"),
            "dangerous_attacks": match.get("dangerous_attacks"),
            "xg": match.get("xg") or match.get("xG"),
            "xG": match.get("xG") or match.get("xg"),
            "league": match.get("league"),
            "country": match.get("country"),
            "home_name": match.get("home_name") or match.get("home_team") or match.get("home"),
            "away_name": match.get("away_name") or match.get("away_team") or match.get("away"),
            "home_logo": match.get("home_logo") or match.get("home_team_logo") or match.get("local_logo"),
            "away_logo": match.get("away_logo") or match.get("away_team_logo") or match.get("visitor_logo"),
            "league_logo": match.get("league_logo") or match.get("competition_logo"),
            "country_flag": match.get("country_flag") or match.get("flag") or match.get("league_flag"),
            "home_team_logo": match.get("home_team_logo") or match.get("home_logo"),
            "away_team_logo": match.get("away_team_logo") or match.get("away_logo"),
            "local_logo": match.get("local_logo") or match.get("home_logo"),
            "visitor_logo": match.get("visitor_logo") or match.get("away_logo"),
            "competition_logo": match.get("competition_logo") or match.get("league_logo"),
            "league_flag": match.get("league_flag") or match.get("country_flag"),
            "flag": match.get("flag") or match.get("country_flag"),
        }

        signal.update(self._reading_fields(match))
        signal.update(self._next_goal_fields(match))
        signal.update(self._auxiliary_live_fields(match))
        return signal

    def _build_opportunity_payload(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        analyst: Dict[str, Any],
        opportunity: Dict[str, Any],
        market: Dict[str, Any] | None,
        value: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        market_type = opportunity.get("market")
        match_id = match.get("match_id")

        payload = {
            "opportunity_id": self._build_signal_key(match_id, market_type or "OBSERVE"),
            "match_id": match_id,
            "match_name": match.get("match_name") or self._build_match_name(match),
            "minute": self._extract_minute(match),
            "type": opportunity.get("type"),
            "rank": opportunity.get("rank"),
            "market": market_type,
            "ai_score": ai.get("ai_score"),
            "goal_probability": ai.get("goal_probability"),
            "over_probability": ai.get("over_probability"),
            "under_probability": ai.get("under_probability"),
            "risk_score": risk.get("risk_score", ai.get("risk_score")),
            "risk_level": risk.get("risk_level", ai.get("risk_level")),
            "risk_flags": risk.get("risk_flags", []),
            "tactical_state": tactical.get("tactical_state"),
            "tactical_bias": tactical.get("tactical_bias"),
            "tempo_label": tactical.get("tempo_label"),
            "market_alignment": tactical.get("market_alignment"),
            "window_phase": window.get("phase"),
            "window_reason": window.get("reason"),
            "data_quality": context.get("data_quality"),
            "game_quality": context.get("game_quality"),
            "context_state": context.get("context_state"),
            "live_decay_factor": context.get("live_decay_factor"),
            "cooling_detected": context.get("cooling_detected"),
            "under_transition_score": context.get("under_transition_score"),
            "dominance": context.get("dominance"),
            "attack_side": context.get("attack_side"),
            "odds": market.get("odds") if market else None,
            "line": market.get("line") if market else None,
            "market_status": market.get("market_status") if market else "PENDING",
            "value_edge": value.get("edge") if value else None,
            "value_category": value.get("value_category") if value else None,
            "analyst_label": analyst.get("analyst_label"),
            "recommended_market": analyst.get("recommended_market"),
            "technical_summary": analyst.get("technical_summary"),
            "consensus_score": (analyst.get("consensus") or {}).get("consensus_score"),
            "reason": opportunity.get("reason"),
            "score": match.get("score"),
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
            "shots": match.get("shots"),
            "shots_on_target": match.get("shots_on_target"),
            "corners": match.get("corners"),
            "dangerous_attacks": match.get("dangerous_attacks"),
            "xg": match.get("xg") or match.get("xG"),
            "xG": match.get("xG") or match.get("xg"),
            "league": match.get("league"),
            "country": match.get("country"),
            "home_name": match.get("home_name") or match.get("home_team") or match.get("home"),
            "away_name": match.get("away_name") or match.get("away_team") or match.get("away"),
            "home_logo": match.get("home_logo") or match.get("home_team_logo") or match.get("local_logo"),
            "away_logo": match.get("away_logo") or match.get("away_team_logo") or match.get("visitor_logo"),
            "league_logo": match.get("league_logo") or match.get("competition_logo"),
            "country_flag": match.get("country_flag") or match.get("flag") or match.get("league_flag"),
            "home_team_logo": match.get("home_team_logo") or match.get("home_logo"),
            "away_team_logo": match.get("away_team_logo") or match.get("away_logo"),
            "local_logo": match.get("local_logo") or match.get("home_logo"),
            "visitor_logo": match.get("visitor_logo") or match.get("away_logo"),
            "competition_logo": match.get("competition_logo") or match.get("league_logo"),
            "league_flag": match.get("league_flag") or match.get("country_flag"),
            "flag": match.get("flag") or match.get("country_flag"),
        }

        payload.update(self._reading_fields(match))
        payload.update(self._next_goal_fields(match))
        payload.update(self._auxiliary_live_fields(match))
        return payload

    def _block(
        self,
        match: Dict[str, Any],
        reason: str,
        context: Dict[str, Any] | None = None,
        ai: Dict[str, Any] | None = None,
        window: Dict[str, Any] | None = None,
        tactical: Dict[str, Any] | None = None,
        risk: Dict[str, Any] | None = None,
        analyst: Dict[str, Any] | None = None,
        opportunity: Dict[str, Any] | None = None,
        market: Dict[str, Any] | None = None,
        value: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "status": "BLOCKED",
            "match_id": match.get("match_id"),
            "match_name": match.get("match_name") or self._build_match_name(match),
            "minute": self._extract_minute(match),
            "reason": reason,
            "context": deepcopy(context) if context else None,
            "ai": deepcopy(ai) if ai else None,
            "window": deepcopy(window) if window else None,
            "tactical": deepcopy(tactical) if tactical else None,
            "risk": deepcopy(risk) if risk else None,
            "analyst": deepcopy(analyst) if analyst else None,
            "opportunity": deepcopy(opportunity) if opportunity else None,
            "market": deepcopy(market) if market else None,
            "value": deepcopy(value) if value else None,
        }

    def _has_minimal_stats(self, match: Dict[str, Any]) -> bool:
        totals = self._extract_totals(match)

        shots = totals["shots"]
        shots_on_target = totals["shots_on_target"]
        xg = totals["xg"]
        dangerous_attacks = totals["dangerous_attacks"]

        home = match.get("home_stats", {}) if isinstance(match.get("home_stats"), dict) else {}
        away = match.get("away_stats", {}) if isinstance(match.get("away_stats"), dict) else {}

        corners = (
            self._safe_float(match.get("corners"))
            + self._safe_float(home.get("corners"))
            + self._safe_float(away.get("corners"))
        )
        possession_home = self._safe_float(home.get("possession")) or self._safe_float(match.get("possession_home"))
        possession_away = self._safe_float(away.get("possession")) or self._safe_float(match.get("possession_away"))

        if (
            shots == 0
            and shots_on_target == 0
            and xg == 0
            and dangerous_attacks == 0
            and corners == 0
            and possession_home == 0
            and possession_away == 0
        ):
            return False

        if shots_on_target > 0:
            return True
        if shots >= 4:
            return True
        if corners >= 3:
            return True
        if dangerous_attacks >= 6:
            return True
        if xg > 0:
            return True
        if possession_home > 0 and possession_away > 0:
            return True

        return False

    def _extract_totals(self, match: Dict[str, Any]) -> Dict[str, float]:
        home = match.get("home_stats", {}) if isinstance(match.get("home_stats"), dict) else {}
        away = match.get("away_stats", {}) if isinstance(match.get("away_stats"), dict) else {}

        if home or away:
            return {
                "shots": self._safe_float(home.get("shots")) + self._safe_float(away.get("shots")),
                "shots_on_target": self._safe_float(home.get("shots_on_target")) + self._safe_float(away.get("shots_on_target")),
                "xg": self._safe_float(home.get("xg")) + self._safe_float(away.get("xg")),
                "dangerous_attacks": self._safe_float(home.get("dangerous_attacks")) + self._safe_float(away.get("dangerous_attacks")),
            }

        return {
            "shots": self._safe_float(match.get("shots")),
            "shots_on_target": self._safe_float(match.get("shots_on_target")),
            "xg": self._safe_float(match.get("xg") or match.get("xG")),
            "dangerous_attacks": self._safe_float(match.get("dangerous_attacks")),
        }

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

    def _build_signal_key(self, match_id: Any, market: Any) -> str:
        return f"{str(match_id).strip()}:{str(market).strip().upper()}"

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

    def _calculate_signal_score(
        self,
        ai: Dict[str, Any],
        context: Dict[str, Any],
        value: Dict[str, Any],
        rank: str | None,
        market_type: str | None = None,
    ) -> float:
        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        edge = self._safe_float(value.get("edge")) * 100

        market = str(market_type or "").upper()
        market_probability = under_probability if market == "UNDER" else over_probability

        if market == "UNDER":
            score = (
                ai_score * 0.35
                + under_probability * 0.30
                + max(0.0, 100.0 - goal_probability) * 0.15
                + max(0.0, 20.0 - min(pressure, 20.0)) * 0.08
                + max(0.0, 15.0 - min(rhythm, 15.0)) * 0.07
                + edge * 0.05
            )
        else:
            score = (
                ai_score * 0.35
                + goal_probability * 0.25
                + market_probability * 0.20
                + min(pressure, 40) * 0.10
                + min(rhythm, 30) * 0.05
                + edge * 0.05
            )

        if rank == "PREMIUM":
            score += 5
        elif rank == "FUERTE":
            score += 3
        elif rank == "BUENA":
            score += 2
        elif rank == "OPERABLE":
            score += 1

        return round(max(0.0, min(score, 100.0)), 2)

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
