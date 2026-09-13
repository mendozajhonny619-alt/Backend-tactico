from datetime import datetime
from typing import Any, Dict, List

from worker import get_last_live_matches
from app.engines.tactical_engine import TacticalEngine
from app.engines.risk_engine import RiskEngine
from app.services.match_window_engine import MatchWindowEngine
from app.services.match_opportunity_service import MatchOpportunityService


class OpportunityDashboardService:
    @staticmethod
    def get_opportunities():
        live_matches = get_last_live_matches() or []

        observe_items: List[Dict[str, Any]] = []
        rejected_items: List[Dict[str, Any]] = []
        over_candidates: List[Dict[str, Any]] = []
        under_candidates: List[Dict[str, Any]] = []

        for match in live_matches:
            try:
                if not match.get("home") or not match.get("away"):
                    continue

                tactica = TacticalEngine.analizar_momentum(match)
                predictor = TacticalEngine.predictor_gol_inminente(match)
                riesgo = RiskEngine.evaluar_riesgo(
                    match,
                    match.get("market", "OVER_MATCH_DYNAMIC")
                )
                window_data = MatchWindowEngine.evaluar(match)

                opportunity = MatchOpportunityService.evaluar(
                    match,
                    tactica,
                    predictor,
                    riesgo,
                    window_data
                )

                item = OpportunityDashboardService._build_item(
                    match=match,
                    tactica=tactica,
                    predictor=predictor,
                    riesgo=riesgo,
                    window_data=window_data,
                    opportunity=opportunity,
                )

                otype = opportunity.get("type", "REJECTED")

                if otype == "OVER_CANDIDATE":
                    over_candidates.append(item)
                elif otype == "UNDER_CANDIDATE":
                    under_candidates.append(item)
                elif otype == "OBSERVE":
                    observe_items.append(item)
                else:
                    rejected_items.append(item)

            except Exception:
                continue

        over_candidates = sorted(
            over_candidates,
            key=lambda x: (
                x.get("opportunity_strength", 0),
                x.get("ai_score", 0),
                x.get("goal_probability", 0),
                x.get("over_probability", 0),
            ),
            reverse=True,
        )[:6]

        under_candidates = sorted(
            under_candidates,
            key=lambda x: (
                x.get("opportunity_strength", 0),
                -x.get("goal_probability", 0),
                -x.get("over_probability", 0),
            ),
            reverse=True,
        )[:6]

        observe_items = sorted(
            observe_items,
            key=lambda x: (
                x.get("opportunity_strength", 0),
                x.get("ai_score", 0),
                x.get("goal_probability", 0),
                x.get("over_probability", 0),
            ),
            reverse=True,
        )[:12]

        rejected_items = sorted(
            rejected_items,
            key=lambda x: (
                x.get("minute", 0),
                x.get("ai_score", 0),
            ),
            reverse=True,
        )[:20]

        return {
            "ok": True,
            "summary": {
                "live_matches": len(live_matches),
                "over_candidates": len(over_candidates),
                "under_candidates": len(under_candidates),
                "observe": len(observe_items),
                "rejected": len(rejected_items),
            },
            "sections": {
                "over_candidates": over_candidates,
                "under_candidates": under_candidates,
                "observe": observe_items,
                "rejected": rejected_items,
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _build_item(
        match: Dict[str, Any],
        tactica: Dict[str, Any],
        predictor: Dict[str, Any],
        riesgo: Dict[str, Any],
        window_data: Dict[str, Any],
        opportunity: Dict[str, Any],
    ) -> Dict[str, Any]:
        home = match.get("home", "N/A")
        away = match.get("away", "N/A")

        return {
            "match_id": match.get("match_id") or match.get("id"),
            "partido": match.get("partido") or f"{home} vs {away}",
            "home": home,
            "away": away,
            "league": match.get("league", "Desconocida"),
            "country": match.get("country", "Desconocido"),
            "minute": int(match.get("minute", 0) or 0),
            "score": match.get("score", "0-0"),
            "ai_score": float(match.get("ai_score", 0) or 0),
            "goal_probability": float(match.get("goal_probability", 0) or 0),
            "over_probability": float(match.get("over_probability", 0) or 0),
            "momentum_label": match.get("momentum_label", "ESTABLE"),
            "risk_level": match.get("risk_level", "MEDIO"),
            "risk_score": float(riesgo.get("risk_score", 0) or 0),
            "match_state": tactica.get("match_state", match.get("match_state", "SIN_DATO")),
            "match_state_reason": tactica.get("match_state_reason", "Sin lectura"),
            "intensity_score": float(tactica.get("intensity_score", 0) or 0),
            "gol_inminente": bool(predictor.get("gol_inminente", False)),
            "confianza_ventana": float(predictor.get("confianza_ventana", 0) or 0),
            "ventana_minutos": int(predictor.get("ventana_minutos", 0) or 0),
            "window_phase": window_data.get("phase", "N/A"),
            "window_reason": window_data.get("reason", "N/A"),
            "publish_over": bool(window_data.get("publish_over", False)),
            "publish_under": bool(window_data.get("publish_under", False)),
            "shots": float(match.get("shots", 0) or 0),
            "shots_on_target": float(match.get("shots_on_target", 0) or 0),
            "corners": float(match.get("corners", 0) or 0),
            "dangerous_attacks": float(match.get("dangerous_attacks", 0) or 0),
            "xG": float(match.get("xG", 0) or 0),
            "data_quality": match.get("data_quality", "LOW"),
            "opportunity_type": opportunity.get("type", "REJECTED"),
            "opportunity_side": opportunity.get("side", "NONE"),
            "opportunity_strength": float(opportunity.get("strength", 0) or 0),
            "opportunity_reasons": opportunity.get("reasons", []),
      }
