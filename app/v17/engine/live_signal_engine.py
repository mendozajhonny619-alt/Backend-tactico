from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.v17.ai.contradiction_judge import ContradictionJudge
from app.v17.ai.market_ai import MarketAI
from app.v17.ai.master_decision_ai import MasterDecisionAI
from app.v17.ai.risk_ai import RiskAI
from app.v17.ai.tactical_ai import TacticalAI
from app.v17.core.clock_guard import ClockGuard
from app.v17.core.context_reader import ContextReader
from app.v17.core.data_quality_guard import DataQualityGuard
from app.v17.core.live_snapshot_store import LiveSnapshotStore
from app.v17.signals.signal_lifecycle import SignalLifecycle
from app.v17.signals.signal_ranker import SignalRanker


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


class LiveSignalEngineV17:
    """
    Motor principal V17.

    Flujo:
    1. Normaliza partidos vivos.
    2. Evalúa reloj.
    3. Evalúa calidad de datos.
    4. Lee contexto.
    5. Ejecuta IA táctica.
    6. Ejecuta IA de mercado.
    7. Ejecuta IA de riesgo.
    8. Juzga contradicciones.
    9. Toma decisión maestra.
    10. Evalúa vida útil.
    11. Rankea máximo 6 señales.
    """

    def __init__(self) -> None:
        self.snapshot_store = LiveSnapshotStore()
        self.clock_guard = ClockGuard()
        self.data_quality_guard = DataQualityGuard()
        self.context_reader = ContextReader()

        self.tactical_ai = TacticalAI()
        self.market_ai = MarketAI()
        self.risk_ai = RiskAI()
        self.contradiction_judge = ContradictionJudge()
        self.master_decision_ai = MasterDecisionAI()

        self.signal_lifecycle = SignalLifecycle()
        self.signal_ranker = SignalRanker()

    def process_live_matches(self, raw_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Entrada principal para una lista de partidos vivos.
        """

        updated_at = utc_now_iso()

        normalized_matches = self.snapshot_store.update_many(raw_matches or [])
        analyzed: List[Dict[str, Any]] = []

        for match in normalized_matches:
            analyzed_item = self.analyze_match(match)
            if analyzed_item:
                analyzed.append(analyzed_item)

        ranked = self.signal_ranker.rank(analyzed)

        return {
            "ok": True,
            "version": "V17",
            "updated_at": updated_at,
            "live_count": len(normalized_matches),
            "analyzed_count": len(analyzed),
            "top_signals": ranked.get("top_signals", []),
            "observe": ranked.get("observe", []),
            "no_bet": ranked.get("no_bet", []),
            "blocked": ranked.get("blocked", []),
            "all_analyzed": ranked.get("all_analyzed", []),
            "summary": ranked.get("summary", {}),
        }

    def analyze_match(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analiza un solo partido y devuelve un objeto limpio para dashboard/tracking.
        """

        if not isinstance(match, dict):
            return None

        clock = self.clock_guard.evaluate(match)
        data_quality = self.data_quality_guard.evaluate(match)
        context = self.context_reader.evaluate(match)
        tactical = self.tactical_ai.evaluate(match, context)
        market = self.market_ai.evaluate(match, context, tactical)
        risk = self.risk_ai.evaluate(
            match=match,
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
        )
        contradiction = self.contradiction_judge.evaluate(
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
        )
        master = self.master_decision_ai.evaluate(
            match=match,
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
        )

        base_signal = self._build_signal_object(
            match=match,
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            master=master,
        )

        lifecycle = self.signal_lifecycle.evaluate(base_signal)

        final_signal = {
            **base_signal,
            **lifecycle,
        }

        if lifecycle.get("no_reentry"):
            final_signal["can_publish"] = False
            final_signal["master_status"] = "NO_REENTRY"
            final_signal["master_action"] = "NO_OPERAR"
            final_signal["master_reason"] = "La señal expiró por vida útil. No se permite reentrada automática."
            final_signal["hard_blockers"] = list(
                set(final_signal.get("hard_blockers", []) + ["NO_REENTRY"])
            )

        return final_signal

    def _build_signal_object(
        self,
        match: Dict[str, Any],
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
        master: Dict[str, Any],
    ) -> Dict[str, Any]:
        match_id = str(match.get("match_id") or match.get("fixture_id") or "")
        home_team = match.get("home_team") or ""
        away_team = match.get("away_team") or ""

        api_minute = safe_int(clock.get("api_minute") or match.get("api_minute"), 0)

        signal_key = self._make_signal_key(
            match_id=match_id,
            market=str(master.get("master_market") or market.get("suggested_market") or "NO_BET"),
            minute=api_minute,
        )

        current_score = f"{safe_int(match.get('home_score'), 0)}-{safe_int(match.get('away_score'), 0)}"

        suggested_market = str(master.get("master_market") or market.get("suggested_market") or "NO_BET").upper()

        if suggested_market == "OVER":
            main_reading = "El partido muestra posibilidad de más goles, condicionado a presión real y reloj confiable."
        elif suggested_market == "UNDER":
            main_reading = "El partido muestra tendencia de cierre, retención o baja profundidad ofensiva."
        elif suggested_market == "OBSERVE":
            main_reading = "El partido tiene señales parciales, pero todavía requiere confirmación."
        else:
            main_reading = "No existe ventaja suficiente para operar."

        what_is_missing = self._build_missing_text(
            master=master,
            clock=clock,
            data_quality=data_quality,
            risk=risk,
            contradiction=contradiction,
        )

        return {
            "version": "V17",
            "signal_key": signal_key,
            "signal_id": signal_key,
            "match_id": match_id,
            "fixture_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "league": match.get("league") or "",
            "country": match.get("country") or "",
            "api_minute": api_minute,
            "display_minute": clock.get("display_minute", api_minute),
            "estimated_minute": clock.get("estimated_minute", api_minute),
            "home_score": safe_int(match.get("home_score"), 0),
            "away_score": safe_int(match.get("away_score"), 0),
            "scoreline": current_score,
            "current_score": current_score,
            "total_goals": safe_int(match.get("total_goals"), 0),
            "status": match.get("status") or "LIVE",
            "updated_at": utc_now_iso(),

            "suggested_market": market.get("suggested_market"),
            "market": suggested_market,
            "market_category": market.get("market_category"),
            "context_category": context.get("context_category"),

            "master_status": master.get("master_status"),
            "master_rank": master.get("master_rank"),
            "master_confidence": master.get("master_confidence"),
            "master_market": master.get("master_market"),
            "master_action": master.get("master_action"),
            "master_reason": master.get("master_reason"),

            "can_publish": master.get("can_publish", False),
            "should_observe": master.get("should_observe", False),
            "should_block": master.get("should_block", False),

            "passed_filters": master.get("passed_filters", []),
            "failed_secondary_filters": master.get("failed_secondary_filters", []),
            "hard_blockers": master.get("hard_blockers", []),
            "soft_warnings": master.get("soft_warnings", []),

            "main_reading": main_reading,
            "what_is_missing": what_is_missing,

            "probable_score": context.get("probable_score", {}),
            "result_probability_reading": context.get("probable_score", {}).get("reading"),

            **clock,
            **data_quality,
            **context,
            **tactical,
            **market,
            **risk,
            **contradiction,
        }

    def _make_signal_key(self, match_id: str, market: str, minute: int) -> str:
        bucket_minute = int(minute / 5) * 5
        return f"V17:{match_id}:{market.upper()}:{bucket_minute}"

    def _build_missing_text(
        self,
        master: Dict[str, Any],
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        risk: Dict[str, Any],
        contradiction: Dict[str, Any],
    ) -> str:
        hard_blockers = master.get("hard_blockers") or []
        secondary = master.get("failed_secondary_filters") or []
        warnings = master.get("soft_warnings") or []

        if hard_blockers:
            return "Bloqueo crítico: " + ", ".join(map(str, hard_blockers[:4]))

        if not clock.get("clock_can_enter"):
            return "Falta sincronía de reloj o confirmación del minuto live."

        if not data_quality.get("data_valid"):
            return "Faltan datos mínimos válidos del partido."

        if contradiction.get("contradiction_status") in {
            "STRONG_CONTRADICTION",
            "CRITICAL_CONTRADICTION",
        }:
            return "Existen contradicciones internas que deben resolverse."

        if risk.get("risk_status") in {"HIGH_RISK", "EXTREME_RISK"}:
            return "El riesgo operativo exige confirmación adicional."

        if secondary:
            return "Faltan filtros secundarios: " + ", ".join(map(str, secondary[:3]))

        if warnings:
            return "Advertencias activas: " + ", ".join(map(str, warnings[:3]))

        return "No falta confirmación crítica. Señal apta según mayoría de filtros."
