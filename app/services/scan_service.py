from __future__ import annotations

from copy import deepcopy
from datetime import datetime
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
from app.services.league_stability_engine import LeagueStabilityEngine
from app.services.team_memory_engine import TeamMemoryEngine
from app.services.next_goal_intelligence_engine import NextGoalIntelligenceEngine

from app.engines.market_engine import MarketEngine
from app.engines.value_engine import ValueEngine
from app.engines.risk_engine import RiskEngine
from app.engines.tactical_engine import TacticalEngine
from app.engines.match_analyst_engine import MatchAnalystEngine
from app.engines.next_goal_side_engine import NextGoalSideEngine
from app.services.sports_ai_agent import SportsAIAgent
from app.services.tactical_memory_service import TacticalMemoryService
from app.services.pre_match_intelligence_engine import PreMatchIntelligenceEngine
from app.services.adaptive_learning_engine import AdaptiveLearningEngine


class ScanService:
    """
    Corazón operativo del sistema.

    Protocolo alineado JHONNY ELITE V16:
    - Escanea partidos en vivo.
    - Clasifica OVER / UNDER / OBSERVE / NO_BET.
    - No deja vacío el panel por sobre-filtro.
    - Publica máximo 6 señales.
    - Respeta reloj live.
    - Respeta decisión maestra.
    - No convierte INTERNAL_ONLY en entrada real.
    - Mantiene oportunidades observables aunque no sean publicables.
    - Pasa al panel visual lectura de riesgo, decisión final, reloj y resultado probable.
    """

    MAX_PUBLISHED_SIGNALS = 6

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

        self.league_stability_engine = LeagueStabilityEngine()
        self.team_memory_engine = TeamMemoryEngine()
        self.next_goal_intelligence_engine = NextGoalIntelligenceEngine()
        self.sports_ai_agent = SportsAIAgent()
        self.tactical_memory_service = TacticalMemoryService()
        self.pre_match_intelligence_engine = PreMatchIntelligenceEngine()
        self.adaptive_learning_engine = AdaptiveLearningEngine()

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

        ranked = self.ranker.rank(candidates)
        published = ranked[: self.MAX_PUBLISHED_SIGNALS]

        sections = self._build_opportunity_sections(opportunities)

        return {
            "published_signals": published,
            "signals": published,
            "candidates": candidates,
            "opportunities": opportunities,
            "sections": sections,
            "blocked": blocked,
            "stats": {
                "scanned_matches": len(live_matches or []),
                "publishable_candidates": len(candidates),
                "opportunities_count": len(opportunities),
                "blocked_matches": len(blocked),
                "published_count": len(published),
                "max_published_signals": self.MAX_PUBLISHED_SIGNALS,
                "over_candidates": len(sections["over_candidates"]),
                "under_candidates": len(sections["under_candidates"]),
                "observe": len(sections["observe"]),
                "no_bet": len(sections["no_bet"]),
                "rejected": len(sections["rejected"]),
            },
        }

    def _process_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        match = self.scan_enhancer.enhance(match or {})

        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")

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
            return self._block(
                match,
                "BLOCK_INVALID_WINDOW",
                context=context,
                window=window,
            )

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

        if self._is_clock_not_operable(match, context):
            return self._observe(
                match=match,
                context=context,
                ai=ai,
                window=window,
                reason="CLOCK_NOT_OPERABLE_OBSERVATION",
            )

        if match.get("is_scannable") is False:
            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="MATCH_NOT_SCANNABLE",
                )

        if not self._has_minimal_stats(match):
            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="LOW_STATS_OBSERVATION",
                )

        if str(context.get("data_quality") or "LOW").upper() == "LOW":
            if not self._should_continue_despite_low_data(match, context, ai):
                return self._observe(
                    match=match,
                    context=context,
                    ai=ai,
                    window=window,
                    reason="LOW_DATA_OBSERVATION",
                )

        ai_score = self._safe_float(ai.get("ai_score"))

        if ai_score < 42:
            return self._observe(
                match=match,
                context=context,
                ai=ai,
                window=window,
                reason="AI_SCORE_TOO_LOW_OBSERVATION",
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

        tactical = self.tactical_engine.evaluate(
            context=context,
            window=window,
        )

        if not risk.get("is_risk_acceptable", False):
            return self._observe(
                match=match,
                context=context,
                ai=ai,
                window=window,
                tactical=tactical,
                risk=risk,
                reason="RISK_UNDER_REVIEW",
            )

        opportunity = self.opportunity_service.evaluate(
            match=match,
            context=context,
            ai=ai,
            window=window,
        )

        opportunity["market"] = self._normalize_market_type(opportunity.get("market"))
        opportunity["market_type"] = opportunity.get("market")

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

        if opportunity.get("type") == "OBSERVE":
            if self._should_promote_observe_to_internal_signal(
                match,
                context,
                ai,
            ):
                promoted_opportunity = {
                    "type": "OVER_CANDIDATE",
                    "rank": "BUENA",
                    "market": "OVER",
                    "market_type": "OVER",
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

        if market:
            market["market_type"] = self._normalize_market_type(
                market.get("market_type")
                or market.get("market")
                or opportunity.get("market")
            )

        if not market.get("is_valid", False):
            if self._should_emit_internal_signal(
                ai,
                context,
                opportunity,
                allow_operable=True,
            ):
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

            payload["block_reason"] = market.get(
                "reason",
                "BLOCK_NO_REAL_MARKET",
            )

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
            if self._should_emit_internal_signal(
                ai,
                context,
                opportunity,
                allow_operable=True,
            ):
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

            payload["block_reason"] = (
                value.get("reason")
                or value.get("status", "BLOCK_NO_VALUE")
            )

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

        if not gate.get("approved", False):
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

            payload["block_reason"] = gate.get(
                "reason",
                "BLOCK_GATE_REJECT",
            )

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

        if not signal.get("should_enter", True):
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

        memory_context = self.tactical_memory_service.build_memory_context(match)

        league_stability = self.league_stability_engine.evaluate(
            league=match.get("league"),
            country=match.get("country"),
            data_quality=context.get("data_quality"),
            history_items=memory_context.get("league_history", []),
        )

        next_goal_ai = self.next_goal_intelligence_engine.analyze(
            match=match,
            context=context,
            ai=ai,
        )

        team_memory_home = self.team_memory_engine.get_memory(
            str(
                match.get("home_name")
                or match.get("home_team")
                or match.get("home")
                or "HOME"
            )
        )

        team_memory_away = self.team_memory_engine.get_memory(
            str(
                match.get("away_name")
                or match.get("away_team")
                or match.get("away")
                or "AWAY"
            )
        )

        pre_match_ai = self.pre_match_intelligence_engine.analyze(
            match=match,
            home_history=memory_context.get("home_history", []),
            away_history=memory_context.get("away_history", []),
            league_history=memory_context.get("league_history", []),
        )

        adaptive_learning = self.adaptive_learning_engine.analyze(
            history=memory_context.get("league_history", []),
            match=match,
        )

        sports_ai_agent = self.sports_ai_agent.think(
            match=match,
            context=context,
            ai=ai,
            league_stability=league_stability,
            next_goal_ai=next_goal_ai,
            deep_analysis=deep_analysis,
            team_memory_home=team_memory_home,
            team_memory_away=team_memory_away,
        )

        sports_ai_context = {
            "sports_ai_context_enabled": True,
            "sports_ai_layer": "LIVE_CONTEXTUAL_AUXILIARY",
            "sports_ai_advice": self._sports_ai_advice(
                league_stability=league_stability,
                next_goal_ai=next_goal_ai,
                deep_analysis=deep_analysis,
            ),
        }

        bookmakers = match.get("bookmakers") or []

        match["has_real_odds"] = bool(bookmakers)
        match["bookmakers_count"] = len(bookmakers)

        real_totals = self._count_real_total_markets(bookmakers)

        match["real_total_markets"] = real_totals
        match["real_market_available"] = real_totals > 0

        if real_totals > 0:
            match["market_source"] = "REAL_ODDS"
        else:
            match["market_source"] = "INTERNAL_ENGINE"

        match["odds_last_update"] = datetime.utcnow().isoformat()

        match.update(timeline)
        match.update(deep_analysis)
        match.update(player_analysis)
        match.update(league_stability)
        match.update(next_goal_ai)

        match["team_memory_home"] = team_memory_home
        match["team_memory_away"] = team_memory_away

        match.update(adaptive_learning)
        match.update(sports_ai_agent)
        match.update(sports_ai_context)
        match.update(memory_context.get("memory_summary", {}))
        match.update(pre_match_ai)

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
        """
        Señal interna no equivale a entrada real.

        Para evitar falsas entradas, INTERNAL_ONLY se manda al FinalDecisionEngine
        como mercado no validado y value no confirmado. Si la decisión maestra
        no autoriza ENTER, queda como oportunidad observable.
        """
        fake_market = {
            "is_valid": False,
            "market_type": opportunity.get("market"),
            "market": opportunity.get("market"),
            "line": "AUTO",
            "odds": None,
            "bookmaker": "INTERNAL",
            "market_status": "INTERNAL_ONLY",
            "reason": "INTERNAL_ONLY_NO_REAL_MARKET",
            "raw_market": None,
        }

        fake_value = {
            "is_value": False,
            "edge": 0.0,
            "value_category": "INTERNAL_OBSERVATION",
            "status": "INTERNAL_ONLY_NO_VALUE_CONFIRMATION",
            "reason": "INTERNAL_ONLY_NO_REAL_VALUE",
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
        signal["market_status"] = "INTERNAL_ONLY"
        signal["should_enter"] = False

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

        if action == "DOWNGRADE" and new_rank in {
            "PREMIUM",
            "FUERTE",
            "BUENA",
            "OPERABLE",
        }:
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

    def _should_hold_by_final_decision(self, final_decision: Dict[str, Any]) -> bool:
        decision = str(final_decision.get("final_decision") or "").upper()

        return decision in {
            "OBSERVE",
            "WAIT",
            "NO_REENTRY",
            "AVOID",
        }

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

        payload["block_reason"] = final_decision.get(
            "final_decision_reason",
            "FINAL_DECISION_HOLD",
        )

        payload["final_decision_status"] = final_decision.get("final_decision")
        payload.update(final_decision)

        return {
            "status": "OPPORTUNITY",
            "opportunity": payload,
        }

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
            "market_type": None,
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
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")
        market_type = self._normalize_market_type(opportunity.get("market"))
        signal_key = self._build_signal_key(match_id, market_type)
        now_iso = datetime.now().isoformat(timespec="seconds")
        current_minute = self._extract_minute(match)

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
            "fixture_id": match.get("fixture_id") or match_id,
            "id": signal_key,
            "live_status": "ACTIVE",
            "history_status": "PUBLISHED",
            "created_at": now_iso,
            "sync_updated_at": now_iso,

            "match_name": match.get("match_name") or self._build_match_name(match),
            "market": market_type,
            "market_type": market.get("market_type") or market_type,
            "market_line": market.get("line"),
            "market_odds": market.get("odds"),

            "minute": current_minute,
            "minuto": current_minute,
            "current_minute": current_minute,

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
            "current_score": match.get("score"),
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

            "has_real_odds": match.get("has_real_odds", False),
            "real_market_available": match.get("real_market_available", False),
            "real_total_markets": match.get("real_total_markets", 0),
            "bookmakers_count": match.get("bookmakers_count", 0),
            "market_source": match.get("market_source", "INTERNAL_ENGINE"),
            "bookmakers": deepcopy(match.get("bookmakers") or []),
            "odds_event_id": match.get("odds_event_id"),
            "odds_source": match.get("odds_source"),
            "odds_match_name": match.get("odds_match_name"),
            "odds_attached": match.get("odds_attached", False),
            "odds_last_update": match.get("odds_last_update"),
        }

        signal.update(self._clock_fields(match))
        signal.update(self._reading_fields(match))
        signal.update(self._next_goal_fields(match))
        signal.update(self._auxiliary_live_fields(match))
        signal.update(self._final_decision_fields(match))

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
        market_type = self._normalize_market_type(opportunity.get("market"))
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")
        current_minute = self._extract_minute(match)

        payload = {
            "opportunity_id": self._build_signal_key(
                match_id,
                market_type or "OBSERVE",
            ),

            "match_id": match_id,
            "fixture_id": match.get("fixture_id") or match_id,

            "match_name": match.get("match_name") or self._build_match_name(match),

            "minute": current_minute,
            "minuto": current_minute,
            "current_minute": current_minute,

            "type": opportunity.get("type"),
            "rank": opportunity.get("rank"),

            "market": market_type,
            "market_type": market_type,

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
            "window_allowed": window.get("allowed"),
            "allow_over": window.get("allow_over"),
            "allow_under": window.get("allow_under"),

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
            "bookmaker": market.get("bookmaker") if market else None,

            "market_status": market.get("market_status") if market else "PENDING",

            "value_edge": value.get("edge") if value else None,
            "value_category": value.get("value_category") if value else None,
            "value_status": value.get("status") if value else None,
            "is_value": value.get("is_value") if value else False,

            "analyst_label": analyst.get("analyst_label"),
            "recommended_market": analyst.get("recommended_market"),
            "technical_summary": analyst.get("technical_summary"),
            "consensus_score": (analyst.get("consensus") or {}).get("consensus_score"),

            "reason": opportunity.get("reason"),

            "score": match.get("score"),
            "current_score": match.get("score"),
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

            "has_real_odds": match.get("has_real_odds", False),
            "real_market_available": match.get("real_market_available", False),
            "real_total_markets": match.get("real_total_markets", 0),
            "bookmakers_count": match.get("bookmakers_count", 0),
            "market_source": match.get("market_source", "INTERNAL_ENGINE"),
            "bookmakers": deepcopy(match.get("bookmakers") or []),
            "odds_event_id": match.get("odds_event_id"),
            "odds_source": match.get("odds_source"),
            "odds_match_name": match.get("odds_match_name"),
            "odds_attached": match.get("odds_attached", False),
            "odds_last_update": match.get("odds_last_update"),
        }

        payload.update(self._clock_fields(match))
        payload.update(self._reading_fields(match))
        payload.update(self._next_goal_fields(match))
        payload.update(self._auxiliary_live_fields(match))
        payload.update(self._final_decision_fields(match))

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
            "match_id": match.get("match_id") or match.get("fixture_id") or match.get("id"),
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
            "has_real_odds": match.get("has_real_odds", False),
            "real_market_available": match.get("real_market_available", False),
            "bookmakers_count": match.get("bookmakers_count", 0),
            **self._clock_fields(match),
        }

    def _should_continue_despite_low_data(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> bool:
        if self._is_clock_not_operable(match, context):
            return False

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
            and pressure >= 8
            and rhythm >= 5
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
        if self._is_clock_not_operable(match, context):
            return False

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
        market_type = self._normalize_market_type(opportunity.get("market"))
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

        possession_home = (
            self._safe_float(home.get("possession"))
            or self._safe_float(match.get("possession_home"))
        )

        possession_away = (
            self._safe_float(away.get("possession"))
            or self._safe_float(match.get("possession_away"))
        )

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

    def _fallback_risk_from_ai(self, ai: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "risk_score": ai.get("risk_score"),
            "risk_level": ai.get("risk_level"),
            "risk_flags": [],
        }

    def _count_real_total_markets(self, bookmakers: List[Dict[str, Any]]) -> int:
        total = 0

        for bookmaker in bookmakers or []:
            if not isinstance(bookmaker, dict):
                continue

            markets = bookmaker.get("markets")

            if not isinstance(markets, list):
                continue

            for market in markets:
                if not isinstance(market, dict):
                    continue

                key = str(market.get("key") or market.get("name") or "").upper()

                if "TOTAL" in key or "OVER" in key or "UNDER" in key:
                    total += 1

        return total

    def _sports_ai_advice(
        self,
        league_stability: Dict[str, Any],
        next_goal_ai: Dict[str, Any],
        deep_analysis: Dict[str, Any],
    ) -> str:
        stability = str(
            league_stability.get("league_stability_level")
            or league_stability.get("stability_level")
            or ""
        ).upper()

        danger = str(league_stability.get("danger_level") or "").upper()

        next_goal_bias = str(next_goal_ai.get("next_goal_bias_ai") or "").upper()
        next_goal_confidence = self._safe_float(next_goal_ai.get("next_goal_confidence_ai"))
        fake_pressure = bool(next_goal_ai.get("next_goal_fake_pressure"))

        deep_bias = str(deep_analysis.get("deep_projection_bias") or "").upper()
        deep_confidence = self._safe_float(deep_analysis.get("deep_projection_confidence"))

        if stability in {"PELIGROSA", "INESTABLE"} or danger in {"ALTO", "EXTREMO"}:
            return "IA contextual: liga riesgosa. Requiere confirmación live fuerte antes de operar."

        if fake_pressure:
            return "IA contextual: posible presión falsa. No confiar sin tiros claros, xG o eventos ofensivos reales."

        if deep_bias in {"OVER", "OVER_WATCH"} and deep_confidence >= 70:
            return "IA contextual: lectura ofensiva favorable, pero mantener validación por riesgo y ventana."

        if deep_bias == "UNDER" and deep_confidence >= 70:
            return "IA contextual: partido con tendencia de retención. Vigilar enfriamiento y baja profundidad."

        if next_goal_bias in {"HOME", "AWAY"} and next_goal_confidence >= 70:
            return f"IA contextual: sesgo de próximo gol hacia {next_goal_bias}, confirmar con momentum reciente."

        return "IA contextual: sin ventaja fuerte. Mantener observación."

    def _build_opportunity_sections(
        self,
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        sections = {
            "over_candidates": [],
            "under_candidates": [],
            "observe": [],
            "no_bet": [],
            "rejected": [],
        }

        for item in opportunities or []:
            item_type = str(item.get("type") or "").upper()
            market = self._normalize_market_type(item.get("market"))

            if item_type in {"NO_BET"}:
                sections["no_bet"].append(item)
            elif item_type in {"REJECTED"}:
                sections["rejected"].append(item)
            elif market == "OVER":
                sections["over_candidates"].append(item)
            elif market == "UNDER":
                sections["under_candidates"].append(item)
            else:
                sections["observe"].append(item)

        return sections

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
            "next_goal_ai_enabled": match.get("next_goal_ai_enabled"),
            "next_goal_bias_ai": match.get("next_goal_bias_ai"),
            "next_goal_confidence_ai": match.get("next_goal_confidence_ai"),
            "home_next_goal_power": match.get("home_next_goal_power"),
            "away_next_goal_power": match.get("away_next_goal_power"),
            "home_pressure_power": match.get("home_pressure_power"),
            "away_pressure_power": match.get("away_pressure_power"),
            "home_momentum_power": match.get("home_momentum_power"),
            "away_momentum_power": match.get("away_momentum_power"),
            "home_need_factor": match.get("home_need_factor"),
            "away_need_factor": match.get("away_need_factor"),
            "next_goal_fake_pressure": match.get("next_goal_fake_pressure"),
            "next_goal_window_ai": match.get("next_goal_window_ai"),
            "next_goal_advice_ai": match.get("next_goal_advice_ai"),
            "next_goal_summary_ai": match.get("next_goal_summary_ai"),
        }

    def _sports_ai_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sports_ai_context_enabled": match.get("sports_ai_context_enabled"),
            "sports_ai_layer": match.get("sports_ai_layer"),
            "sports_ai_advice": match.get("sports_ai_advice"),
            "sports_ai_summary": match.get("sports_ai_summary"),
            "sports_ai_action": match.get("sports_ai_action"),
            "sports_ai_confidence": match.get("sports_ai_confidence"),
            "sports_ai_risk_flags": match.get("sports_ai_risk_flags"),
            "league_stability_enabled": match.get("league_stability_enabled"),
            "league_stability_score": match.get("league_stability_score"),
            "league_stability_level": match.get("league_stability_level"),
            "league_stability_warnings": match.get("league_stability_warnings"),
            "league_stability_positive_factors": match.get("league_stability_positive_factors"),
            "league_history_profile": match.get("league_history_profile"),
            "league_operational_advice": match.get("league_operational_advice"),
            "volatility_score": match.get("volatility_score"),
            "chaos_score": match.get("chaos_score"),
            "consistency_score": match.get("consistency_score"),
            "danger_level": match.get("danger_level"),
            "recommendation": match.get("recommendation"),
            "analysis_summary": match.get("analysis_summary"),
            "team_memory_home": match.get("team_memory_home"),
            "team_memory_away": match.get("team_memory_away"),
            "adaptive_learning_enabled": match.get("adaptive_learning_enabled"),
            "adaptive_confidence_adjustment": match.get("adaptive_confidence_adjustment"),
            "adaptive_warning_flags": match.get("adaptive_warning_flags"),
            "adaptive_league_profile": match.get("adaptive_league_profile"),
            "adaptive_market_profile": match.get("adaptive_market_profile"),
            "adaptive_global_profile": match.get("adaptive_global_profile"),
            "adaptive_learning_summary": match.get("adaptive_learning_summary"),
            "pre_match_summary": match.get("pre_match_summary"),
            "pre_match_prediction": match.get("pre_match_prediction"),
            "pre_match_confidence": match.get("pre_match_confidence"),
            "pre_match_risk_level": match.get("pre_match_risk_level"),
        }

    def _auxiliary_live_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        fields = {
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

        fields.update(self._sports_ai_fields(match))
        return fields

    def _final_decision_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        result_projection = match.get("result_projection") or {}

        return {
            "final_decision": match.get("final_decision"),
            "final_decision_status": match.get("final_decision"),
            "master_decision_status": match.get("final_decision"),
            "final_decision_reason": match.get("final_decision_reason"),
            "final_decision_confidence": match.get("final_decision_confidence"),
            "final_decision_market": match.get("final_decision_market"),
            "final_decision_warnings": match.get("final_decision_warnings"),
            "decision_warnings": match.get("decision_warnings"),
            "alternative_reading": match.get("alternative_reading"),
            "requires_confirmation": match.get("requires_confirmation"),
            "should_enter": match.get("should_enter"),
            "should_observe": match.get("should_observe"),
            "should_wait": match.get("should_wait"),
            "should_no_reentry": match.get("should_no_reentry"),
            "should_avoid": match.get("should_avoid"),
            "result_projection": result_projection,
            "probable_result": match.get("probable_result") or result_projection.get("probable_result"),
            "alternative_result": match.get("alternative_result") or result_projection.get("alternative_result"),
            "projection_label": match.get("projection_label") or result_projection.get("projection_label"),
        }

    def _clock_fields(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "clock_reference_minute": match.get("clock_reference_minute"),
            "clock_reference_epoch": match.get("clock_reference_epoch"),
            "clock_reference_at": match.get("clock_reference_at"),
            "clock_reference_iso": match.get("clock_reference_iso"),
            "clock_changed": match.get("clock_changed"),
            "clock_stale": match.get("clock_stale"),
            "clock_frozen": match.get("clock_frozen"),
            "is_stale": match.get("is_stale"),
            "is_clock_frozen": match.get("is_clock_frozen"),
            "minute_lag_detected": match.get("minute_lag_detected"),
            "same_snapshot_seconds": match.get("same_snapshot_seconds"),
            "data_age_seconds": match.get("data_age_seconds"),
            "live_clock_status": match.get("live_clock_status"),
            "live_clock_source": match.get("live_clock_source"),
            "can_operate_by_clock": match.get("can_operate_by_clock"),
            "clock_warning": match.get("clock_warning"),
            "api_minute": match.get("api_minute"),
            "source_minute": match.get("source_minute"),
            "display_minute": match.get("display_minute"),
            "estimated_minute": match.get("estimated_minute"),
            "minute_confidence": match.get("minute_confidence"),
        }

    def _is_clock_not_operable(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> bool:
        context = context or {}

        can_operate = self._first_existing(
            match.get("can_operate_by_clock"),
            context.get("can_operate_by_clock"),
        )

        if can_operate is False:
            return True

        flags = [
            match.get("clock_frozen"),
            match.get("is_clock_frozen"),
            match.get("minute_frozen"),
            match.get("minute_lag_detected"),
            context.get("clock_frozen"),
            context.get("is_clock_frozen"),
            context.get("minute_frozen"),
            context.get("minute_lag_detected"),
        ]

        if any(bool(x) for x in flags):
            return True

        status = str(
            match.get("live_clock_status")
            or context.get("live_clock_status")
            or ""
        ).upper()

        if status in {
            "CLOCK_FROZEN",
            "MINUTE_LAG_DETECTED",
            "LOW_CONFIDENCE_CLOCK",
            "OFFLINE",
            "DELAYED",
        }:
            return True

        age = self._safe_float(
            match.get("data_age_seconds")
            or context.get("data_age_seconds")
        )

        if age >= 120:
            return True

        return False

    def _normalize_market_type(self, value: Any) -> str:
        raw = str(value or "").upper().strip()

        if not raw:
            return ""

        if "UNDER" in raw:
            return "UNDER"

        if "MENOS" in raw or "DEBAJO" in raw or "BAJA" in raw:
            return "UNDER"

        if "OVER" in raw:
            return "OVER"

        if "MÁS" in raw or "MAS" in raw or "ENCIMA" in raw or "ALTA" in raw:
            return "OVER"

        if "NEXT_GOAL" in raw or "PRÓXIMO" in raw or "PROXIMO" in raw:
            return "OVER"

        if raw in {"O", "OVER_MATCH_DYNAMIC", "OVER_NEXT_15_DYNAMIC"}:
            return "OVER"

        if raw in {"U", "UNDER_MATCH_DYNAMIC"}:
            return "UNDER"

        return raw

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("display_minute")
            or match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or match.get("api_minute")
            or match.get("source_minute")
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

        market = self._normalize_market_type(market_type)

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
                + over_probability * 0.20
                + min(pressure, 40) * 0.10
                + min(rhythm, 30) * 0.05
                + edge * 0.05
            )

        rank_text = str(rank or "").upper()

        if rank_text == "PREMIUM":
            score += 5
        elif rank_text == "FUERTE":
            score += 3
        elif rank_text == "BUENA":
            score += 2
        elif rank_text == "OPERABLE":
            score += 1

        return round(max(0.0, min(score, 100.0)), 2)

    def _first_existing(self, *values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def _safe_float(self, value: Any) -> float:
        try:
            if isinstance(value, str):
                value = value.strip().replace("%", "")
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
