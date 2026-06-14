from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.v17.ai.contradiction_judge import ContradictionJudge
from app.v17.ai.decision_explainer_ai import DecisionExplainerAI
from app.v17.ai.entry_timing_ai import EntryTimingAI
from app.v17.ai.league_volatility_ai import LeagueVolatilityAI
from app.v17.ai.market_ai import MarketAI
from app.v17.ai.master_decision_ai import MasterDecisionAI
from app.v17.ai.match_maturity_ai import MatchMaturityAI
from app.v17.ai.match_prediction_ai import MatchPredictionAI
from app.v17.ai.match_reader_ai import MatchReaderAI
from app.v17.ai.over_candidate_ai import OverCandidateAI
from app.v17.ai.panel_decision_ai import PanelDecisionAI
from app.v17.ai.pre_match_profile_ai import PreMatchProfileAI
from app.v17.ai.risk_ai import RiskAI
from app.v17.ai.signal_activation_ai import SignalActivationAI
from app.v17.services.prediction_feature_builder import PredictionFeatureBuilder
from app.v17.services.prediction_feature_store import PredictionFeatureStore
from app.v17.services.training_data_pipeline import TrainingDataPipeline
from app.v17.ml.model_registry import ModelRegistry
from app.v17.services.model_prediction_service import ModelPredictionService
from app.v17.ai.signal_narrative_ai import SignalNarrativeAI
from app.v17.ai.signal_promotion_ai import SignalPromotionAI
from app.v17.ai.tactical_ai import TacticalAI
from app.v17.core.clock_guard import ClockGuard
from app.v17.core.context_reader import ContextReader
from app.v17.core.data_quality_guard import DataQualityGuard
from app.v17.core.live_snapshot_store import LiveSnapshotStore
from app.v17.services.pre_match_data_service import PreMatchDataService
from app.v17.services.signal_history_service import SignalHistoryService
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

    Esta versión mantiene la estructura que ya funcionaba y agrega dos capas seguras:

    1. SignalActivationAI
       Revisa si una observación alta, sobre todo OVER, puede subir a candidato temprano
       o candidato fuerte sin romper la lógica principal.

    2. MatchPredictionAI
       Agrega predicción live del partido, resultado probable, escenario, próximo gol
       y mercado proyectado.

    Ambas capas están protegidas con try/except para que, si fallan, el sistema siga
    mostrando partidos, señales, observaciones y candidatos normalmente.
    """

    def __init__(self) -> None:
        self.snapshot_store = LiveSnapshotStore()
        self.clock_guard = ClockGuard()
        self.data_quality_guard = DataQualityGuard()
        self.context_reader = ContextReader()

        self.pre_match_data_service = PreMatchDataService()
        self.pre_match_profile_ai = PreMatchProfileAI()

        self.tactical_ai = TacticalAI()
        self.market_ai = MarketAI()
        self.risk_ai = RiskAI()
        self.contradiction_judge = ContradictionJudge()

        self.prediction_feature_builder = PredictionFeatureBuilder()
        self.prediction_feature_store = PredictionFeatureStore()
        self.training_data_pipeline = TrainingDataPipeline(self.prediction_feature_store)
        
        # Phase 3: Model prediction infrastructure
        from pathlib import Path
        storage_dir = str(Path(__file__).parent.parent.parent / "v17" / "storage")
        self.model_registry = ModelRegistry(storage_dir)
        self.model_prediction_service = ModelPredictionService(
            self.model_registry,
            feedback_storage_dir=storage_dir
        )
        
        self.over_candidate_ai = OverCandidateAI()
        self.league_volatility_ai = LeagueVolatilityAI()
        self.master_decision_ai = MasterDecisionAI()
        self.decision_explainer_ai = DecisionExplainerAI()
        self.match_reader_ai = MatchReaderAI()
        self.panel_decision_ai = PanelDecisionAI()
        self.match_maturity_ai = MatchMaturityAI()
        self.entry_timing_ai = EntryTimingAI()
        self.signal_narrative_ai = SignalNarrativeAI()
        self.signal_promotion_ai = SignalPromotionAI()
        self.signal_activation_ai = SignalActivationAI()
        self.match_prediction_ai = MatchPredictionAI()

        self.signal_lifecycle = SignalLifecycle()
        self.signal_ranker = SignalRanker()
        self.signal_history_service = SignalHistoryService()

    def process_live_matches(self, raw_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        updated_at = utc_now_iso()

        normalized_matches = self.snapshot_store.update_many(raw_matches or [])
        analyzed: List[Dict[str, Any]] = []

        for match in normalized_matches:
            analyzed_item = self.analyze_match(match)
            if analyzed_item:
                analyzed.append(analyzed_item)

        ranked = self.signal_ranker.rank(analyzed)

        signal_results = self._safe_history_results()
        signal_history_summary = self._safe_history_summary()

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
            "signal_results": signal_results,
            "results": signal_results,
            "signal_history_summary": signal_history_summary,
            "history_summary": signal_history_summary,
        }

    def analyze_match(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(match, dict):
            return None

        pre_match_profile = self._evaluate_pre_match_profile(match)

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

        feature_payload = self.prediction_feature_builder.build(
            match=match,
            pre_match_profile=pre_match_profile,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            clock=clock,
            data_quality=data_quality,
        )
        self.prediction_feature_store.save_feature_vector(feature_payload)
        
        # Phase 3: Make model prediction in parallel (doesn't affect decision logic)
        self._make_model_prediction(match, feature_payload)

        contradiction = self.contradiction_judge.evaluate(
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
        )

        over_candidate = self.over_candidate_ai.evaluate(
            match=match,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
        )

        league_volatility = self.league_volatility_ai.evaluate(
            match=match,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            over_candidate=over_candidate,
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

        decision_explanation = self.decision_explainer_ai.explain(
            match=match,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            master=master,
        )

        master = self._apply_decision_explainer_guard(
            master=master,
            decision_explanation=decision_explanation,
        )

        match_reader = self.match_reader_ai.evaluate(
            match=match,
            clock=clock,
            data_quality=data_quality,
            context=context,
            tactical=tactical,
            market=market,
            risk=risk,
            contradiction=contradiction,
            over_candidate=over_candidate,
            league_volatility=league_volatility,
            decision_explanation=decision_explanation,
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
            over_candidate=over_candidate,
            league_volatility=league_volatility,
            match_reader=match_reader,
            master=master,
            decision_explanation=decision_explanation,
            pre_match_profile=pre_match_profile,
        )

        panel_decision = self.panel_decision_ai.evaluate(base_signal)

        base_signal = {
            **base_signal,
            **panel_decision,
        }

        match_maturity = self.match_maturity_ai.evaluate(
            signal=base_signal,
            match_reader=match_reader,
        )

        base_signal = {
            **base_signal,
            **match_maturity,
        }

        base_signal = self._apply_match_maturity_guard(base_signal)

        base_signal.update(
            self.panel_decision_ai.evaluate(base_signal)
        )

        entry_timing = self.entry_timing_ai.evaluate(
            signal=base_signal,
            match_reader=match_reader,
        )

        base_signal = {
            **base_signal,
            **entry_timing,
        }

        narrative = self.signal_narrative_ai.build(
            signal=base_signal,
            match_reader=match_reader,
        )

        base_signal = {
            **base_signal,
            **narrative,
        }

        promotion = self.signal_promotion_ai.evaluate(
            signal=base_signal,
            match_reader=match_reader,
        )

        base_signal = {
            **base_signal,
            **promotion,
        }

        base_signal = self._apply_signal_promotion_guard(base_signal)

        base_signal = self._safe_apply_signal_activation(base_signal)

        base_signal = self._safe_apply_match_prediction(base_signal)

        # Guardia final V17: evita que módulos posteriores publiquen si reloj,
        # datos, contradicción o vida útil no permiten operar.
        base_signal = self._apply_v17_authority_guard(base_signal)

        narrative_after_prediction = self.signal_narrative_ai.build(
            signal=base_signal,
            match_reader=match_reader,
        )

        base_signal = {
            **base_signal,
            **narrative_after_prediction,
        }

        lifecycle = self.signal_lifecycle.evaluate(base_signal)

        final_signal = {
            **base_signal,
            **lifecycle,
        }

        # Segunda pasada: ahora incluye la evaluación de vida útil de la señal.
        final_signal = self._apply_v17_authority_guard(final_signal)

        if lifecycle.get("no_reentry"):
            final_signal["can_publish"] = False
            final_signal["should_observe"] = False
            final_signal["should_block"] = True
            final_signal["master_status"] = "NO_REENTRY"
            final_signal["master_rank"] = "BLOCKED"
            final_signal["master_action"] = "NO_OPERAR"
            final_signal["master_reason"] = "La señal expiró por vida útil. No se permite reentrada automática."
            final_signal["promotion_level"] = "BLOCKED"
            final_signal["activation_level"] = "BLOCKED"
            final_signal["prediction_mode"] = "BLOCKED_PREDICTION"
            final_signal["prediction_scenario"] = "SIGNAL_EXPIRED"
            final_signal["promotion_panel_label"] = "SEÑAL EXPIRADA"
            final_signal["activation_label"] = "SEÑAL EXPIRADA"
            final_signal["promotion_action"] = "NO_OPERAR"
            final_signal["activation_action"] = "NO_OPERAR"
            final_signal["promotion_can_publish"] = False
            final_signal["activation_can_publish"] = False
            final_signal["promotion_should_observe"] = False
            final_signal["activation_should_observe"] = False
            final_signal["promotion_is_main_signal"] = False
            final_signal["promotion_is_top_signal"] = False
            final_signal["panel_signal_type"] = "SEÑAL EXPIRADA"
            final_signal["panel_promotion_label"] = "SEÑAL EXPIRADA"
            final_signal["panel_activation_label"] = "SEÑAL EXPIRADA"
            final_signal["panel_promotion_reason"] = "La señal expiró por vida útil. No se permite reentrada automática."
            final_signal["panel_activation_reason"] = "La señal expiró por vida útil. No se permite reentrada automática."
            final_signal["prediction_panel_message"] = "La señal expiró por vida útil. No se permite reentrada automática."
            final_signal["hard_blockers"] = list(
                set(final_signal.get("hard_blockers", []) + ["NO_REENTRY"])
            )

            final_signal.update(
                self.panel_decision_ai.evaluate(final_signal)
            )

            final_signal.update(
                self.entry_timing_ai.evaluate(
                    signal=final_signal,
                    match_reader=match_reader,
                )
            )

            final_signal.update(
                self.signal_narrative_ai.build(
                    signal=final_signal,
                    match_reader=match_reader,
                )
            )

        self._update_prediction_feature_store(final_signal)

        history_result = self._register_signal_history(final_signal)

        final_signal = {
            **final_signal,
            **history_result,
        }

        return final_signal

    def _apply_v17_authority_guard(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guardia final de autoridad V17.

        Evita que PromotionAI, ActivationAI, PanelDecisionAI o PredictionAI
        publiquen una señal cuando capas críticas ya pidieron espera,
        bloqueo o degradación.

        Esta capa no crea señales nuevas ni cambia el análisis táctico.
        Solo protege la decisión final frente a condiciones críticas.
        """
        guarded = dict(signal)

        hard_blockers = list(guarded.get("hard_blockers", []) or [])
        soft_warnings = list(guarded.get("soft_warnings", []) or [])

        clock_can_enter = bool(guarded.get("clock_can_enter", True))
        data_valid = bool(guarded.get("data_valid", True))
        contradiction_status = str(guarded.get("contradiction_status") or "").upper()
        signal_expired = bool(guarded.get("signal_expired"))
        no_reentry = bool(guarded.get("no_reentry"))
        critical_block = bool(guarded.get("critical_block"))

        authority_reasons: List[str] = []

        if not clock_can_enter:
            authority_reasons.append("CLOCK_GUARD_NO_ENTER")

        if not data_valid:
            authority_reasons.append("DATA_QUALITY_NOT_VALID")

        if contradiction_status == "CRITICAL_CONTRADICTION":
            authority_reasons.append("CRITICAL_CONTRADICTION")

        if signal_expired or no_reentry:
            authority_reasons.append("SIGNAL_LIFECYCLE_NO_REENTRY")

        if critical_block:
            authority_reasons.append("CRITICAL_BLOCK_ACTIVE")

        if not authority_reasons:
            return guarded

        guarded["can_publish"] = False
        guarded["published"] = False
        guarded["should_observe"] = True
        guarded["should_block"] = False

        if "SIGNAL_LIFECYCLE_NO_REENTRY" in authority_reasons:
            guarded["should_observe"] = False
            guarded["should_block"] = True
            guarded["master_status"] = "NO_REENTRY"
            guarded["master_rank"] = "BLOCKED"
            guarded["master_action"] = "NO_OPERAR"
            guarded["master_reason"] = "V17 Authority Guard bloqueó la señal por vida útil expirada."

        elif "CRITICAL_CONTRADICTION" in authority_reasons:
            guarded["master_status"] = "WAIT_CONFIRMATION"
            guarded["master_rank"] = "OBSERVE"
            guarded["master_action"] = "ESPERAR_CONFIRMACION"
            guarded["master_reason"] = "V17 Authority Guard degradó la señal por contradicción crítica."

        elif "CLOCK_GUARD_NO_ENTER" in authority_reasons:
            guarded["master_status"] = "WAIT_CONFIRMATION"
            guarded["master_rank"] = "OBSERVE"
            guarded["master_action"] = "ESPERAR_RELOJ"
            guarded["master_reason"] = "V17 Authority Guard exige confirmación del reloj antes de operar."

        elif "DATA_QUALITY_NOT_VALID" in authority_reasons:
            guarded["master_status"] = "WAIT_CONFIRMATION"
            guarded["master_rank"] = "OBSERVE"
            guarded["master_action"] = "ESPERAR_DATOS"
            guarded["master_reason"] = "V17 Authority Guard exige datos válidos antes de operar."

        guarded["hard_blockers"] = sorted(set(hard_blockers + authority_reasons))
        guarded["soft_warnings"] = sorted(set(soft_warnings + ["V17_AUTHORITY_GUARD_APPLIED"]))
        guarded["authority_guard_reasons"] = authority_reasons
        guarded["authority_guard_applied"] = True

        return guarded

    def _safe_apply_signal_activation(self, base_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica SignalActivationAI sin poner en riesgo el motor.

        Si falla, conserva la señal original y solo agrega un error interno.
        """
        try:
            activation = self.signal_activation_ai.evaluate(base_signal)

            if isinstance(activation, dict):
                base_signal = {
                    **base_signal,
                    **activation,
                }

                base_signal = self._apply_signal_activation_guard(base_signal)

            return base_signal

        except Exception as exc:
            safe_signal = dict(base_signal)
            safe_signal["activation_error"] = type(exc).__name__
            safe_signal["activation_level"] = safe_signal.get("activation_level") or "ACTIVATION_ERROR_SAFE"
            safe_signal["activation_label"] = safe_signal.get("activation_label") or "ACTIVACIÓN NO DISPONIBLE"
            safe_signal["panel_activation_label"] = safe_signal.get("panel_activation_label") or "ACTIVACIÓN NO DISPONIBLE"
            safe_signal["panel_activation_reason"] = (
                "SignalActivationAI no pudo ejecutarse, pero la señal principal continúa funcionando."
            )
            return safe_signal

    def _safe_apply_match_prediction(self, base_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica MatchPredictionAI sin poner en riesgo el motor.

        Si falla, conserva la señal original y agrega campos de predicción segura.
        """
        try:
            prediction = self.match_prediction_ai.evaluate(base_signal)

            if isinstance(prediction, dict):
                return {
                    **base_signal,
                    **prediction,
                }

            safe_signal = dict(base_signal)
            safe_signal["prediction_error"] = "INVALID_PREDICTION_RESPONSE"
            safe_signal["prediction_mode"] = "PREDICTION_ERROR_SAFE"
            safe_signal["prediction_scenario"] = "PREDICTION_NOT_AVAILABLE"
            safe_signal["prediction_panel_message"] = (
                "La predicción live no devolvió una respuesta válida, pero la señal principal continúa funcionando."
            )
            return safe_signal

        except Exception as exc:
            safe_signal = dict(base_signal)
            safe_signal["prediction_error"] = type(exc).__name__
            safe_signal["prediction_mode"] = "PREDICTION_ERROR_SAFE"
            safe_signal["prediction_scenario"] = "PREDICTION_NOT_AVAILABLE"
            safe_signal["prediction_market"] = safe_signal.get("panel_market") or safe_signal.get("market") or "OBSERVE"
            safe_signal["prediction_score"] = safe_signal.get("scoreline") or safe_signal.get("current_score")
            safe_signal["prediction_alternative_score"] = safe_signal.get("scoreline") or safe_signal.get("current_score")
            safe_signal["prediction_next_goal_probability"] = "UNKNOWN"
            safe_signal["prediction_confidence"] = 0
            safe_signal["prediction_panel_message"] = (
                "La predicción live no pudo calcularse, pero la señal principal continúa funcionando."
            )
            return safe_signal

    def _update_prediction_feature_store(self, signal: Dict[str, Any]) -> None:
        try:
            fixture_id = str(signal.get("fixture_id") or signal.get("match_id") or "").strip()
            api_minute = safe_int(signal.get("api_minute") or signal.get("entry_minute"), 0)
            prediction_snapshot = {
                "prediction_market": signal.get("prediction_market"),
                "prediction_confidence": signal.get("prediction_confidence"),
                "prediction_scenario": signal.get("prediction_scenario"),
                "prediction_mode": signal.get("prediction_mode"),
                "prediction_next_goal_probability": signal.get("prediction_next_goal_probability"),
                "prediction_score": signal.get("prediction_score"),
                "prediction_alternative_score": signal.get("prediction_alternative_score"),
                "prediction_halftime_score": signal.get("prediction_halftime_score"),
                "prediction_final_score": signal.get("prediction_final_score"),
                "prediction_score_scenarios": signal.get("prediction_score_scenarios"),
                "prediction_market_alignment": signal.get("prediction_market_alignment"),
                "prediction_panel_message": signal.get("prediction_panel_message"),
            }
            self.prediction_feature_store.update_prediction_snapshot(
                fixture_id=fixture_id,
                api_minute=api_minute,
                prediction_snapshot=prediction_snapshot,
                signal_key=str(signal.get("signal_key") or signal.get("signal_id") or ""),
            )
        except Exception:
            pass

    def _register_signal_history(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.signal_history_service.register_signal(signal)

            if not isinstance(result, dict):
                return {
                    "history_ok": False,
                    "history_error": "INVALID_HISTORY_RESPONSE",
                }

            return result

        except Exception as exc:
            return {
                "history_ok": False,
                "history_error": type(exc).__name__,
            }

    def _make_model_prediction(
        self,
        match: Dict[str, Any],
        feature_payload: Dict[str, Any]
    ) -> None:
        """
        Phase 3: Make ML model prediction in parallel as metadata.
        
        Runs safely without affecting decision logic.
        Stores prediction for later recording when signal resolves.
        """
        try:
            fixture_id = str(match.get("fixture_id") or match.get("match_id") or "").strip()
            market = str(match.get("market") or "OVER").upper()
            signal_key = str(match.get("signal_key") or match.get("signal_id") or "")
            
            # Extract feature vector
            feature_vector = feature_payload.get("feature_vector", {})
            
            # Make model prediction (returns dict or empty if model not ready)
            model_prediction = self.model_prediction_service.make_prediction(
                market=market,
                feature_vector=feature_vector,
                signal_key=signal_key
            )
            
            # Store metadata in feature store if prediction was made
            if model_prediction.get("has_prediction"):
                try:
                    api_minute = safe_int(match.get("api_minute") or match.get("entry_minute"), 0)
                    model_snapshot = {
                        "model_id": model_prediction.get("model_id"),
                        "predicted_class": model_prediction.get("predicted_class"),
                        "predicted_probability": model_prediction.get("predicted_probability"),
                        "probabilities": model_prediction.get("probabilities", {}),
                        "prediction_timestamp": model_prediction.get("prediction_timestamp")
                    }
                    
                    # Store as metadata (feature store will handle if row doesn't exist yet)
                    self.prediction_feature_store.update_prediction_snapshot(
                        fixture_id=fixture_id,
                        api_minute=api_minute,
                        prediction_snapshot=model_snapshot,
                        signal_key=signal_key
                    )
                except Exception:
                    pass  # Don't break signal generation if storage fails
        
        except Exception:
            pass  # Model prediction failure doesn't affect signal generation

    def _safe_history_results(self) -> List[Dict[str, Any]]:
        try:
            return self.signal_history_service.get_results(
                limit=120,
                include_observation=False,
            )
        except Exception:
            return []

    def _safe_history_summary(self) -> Dict[str, Any]:
        try:
            return self.signal_history_service.get_summary()
        except Exception:
            return {
                "total_records": 0,
                "pending": 0,
                "won": 0,
                "lost": 0,
                "expired": 0,
                "cancelled": 0,
                "unknown": 0,
                "strong_candidates": 0,
                "main_signals": 0,
                "top_signals": 0,
                "observations": 0,
            }

    def _evaluate_pre_match_profile(self, match: Dict[str, Any]) -> Dict[str, Any]:
        try:
            pre_match_package = self.pre_match_data_service.get_pre_match_package(match)

            pre_match_profile = self.pre_match_profile_ai.analyze(
                pre_match_package=pre_match_package,
                live_match=match,
            )

            return pre_match_profile if isinstance(pre_match_profile, dict) else {}

        except Exception as exc:
            return {
                "pre_match_profile_version": "V17_PRE_MATCH_PROFILE_AI_ERROR_SAFE",
                "pre_match_available": False,
                "pre_match_ok": False,
                "pre_match_source": "ERROR_SAFE_FALLBACK",
                "pre_match_cache_status": "ERROR",
                "pre_match_error": type(exc).__name__,
                "league_goal_profile": "UNKNOWN_LEAGUE",
                "team_goal_profile": "UNKNOWN_TEAMS",
                "first_half_profile": "UNKNOWN_FIRST_HALF",
                "second_half_profile": "UNKNOWN_SECOND_HALF",
                "first_half_goal_risk": "UNKNOWN_FIRST_HALF_GOAL_RISK",
                "second_half_goal_risk": "UNKNOWN_SECOND_HALF_GOAL_RISK",
                "under_early_risk": "UNKNOWN_UNDER_EARLY_RISK",
                "over_support_pre_match": "UNKNOWN",
                "under_support_pre_match": "UNKNOWN",
                "over_pre_match_score": 0,
                "under_pre_match_score": 0,
                "pre_match_panel_note": "No se pudo cargar memoria previa. La lectura live continúa sin contexto prepartido.",
                "pre_match_recommended_behavior": "LIVE_DECIDES_WITHOUT_PRE_MATCH_CONTEXT",
                "pre_match_support_points": [],
                "pre_match_caution_points": [
                    "Memoria previa no disponible. No aumentar confianza solo por marcador."
                ],
            }

    def _apply_signal_activation_guard(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        guarded = dict(signal)

        activation_level = str(guarded.get("activation_level") or "").upper()
        activation_market = str(guarded.get("activation_market") or "").upper()
        activation_score = guarded.get("activation_score")
        activation_label = str(guarded.get("activation_label") or "")
        activation_reason = str(guarded.get("activation_reason") or "")

        activation_warnings = list(guarded.get("activation_warnings", []) or [])
        activation_blockers = list(guarded.get("activation_blockers", []) or [])

        if activation_market:
            guarded["promotion_market"] = activation_market
            guarded["panel_market"] = activation_market
            guarded["market"] = activation_market

        if activation_score is not None:
            guarded["activation_final_score"] = activation_score

        if activation_label:
            guarded["panel_activation_label"] = activation_label
            guarded["panel_signal_type"] = activation_label
            guarded["panel_label"] = activation_label

        if activation_reason:
            guarded["panel_activation_reason"] = activation_reason
            guarded["panel_promotion_reason"] = activation_reason

        guarded["soft_warnings"] = sorted(
            set(
                list(guarded.get("soft_warnings", []) or [])
                + activation_warnings
            )
        )

        guarded["hard_blockers"] = sorted(
            set(
                list(guarded.get("hard_blockers", []) or [])
                + activation_blockers
            )
        )

        if guarded.get("activation_should_block") or activation_level == "BLOCKED":
            guarded["can_publish"] = False
            guarded["should_observe"] = False
            guarded["should_block"] = True
            guarded["master_status"] = "BLOCKED_BY_ACTIVATION"
            guarded["master_rank"] = "BLOCKED"
            guarded["master_action"] = "NO_OPERAR"
            guarded["master_reason"] = activation_reason or "SignalActivationAI bloqueó la señal."
            guarded["promotion_level"] = "BLOCKED"
            guarded["panel_section"] = "BLOCKED"
            guarded["panel_signal_type"] = activation_label or "BLOQUEADO"
            guarded["panel_label"] = activation_label or "BLOQUEADO"
            return guarded

        if activation_level == "TOP_SIGNAL":
            guarded["can_publish"] = True
            guarded["should_observe"] = False
            guarded["should_block"] = False
            guarded["master_status"] = "TOP_SIGNAL"
            guarded["master_rank"] = "TOP_SIGNAL"
            guarded["master_action"] = "PRIORIZAR_TOP_SIGNAL"
            guarded["master_reason"] = activation_reason
            guarded["promotion_level"] = "TOP_SIGNAL"
            guarded["elite_rank"] = "TOP_SIGNAL"
            guarded["panel_section"] = "TOP_SIGNAL"
            guarded["panel_signal_type"] = activation_label or "TOP SIGNAL"
            guarded["panel_label"] = activation_label or "TOP SIGNAL"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(activation_score, 0),
                92,
            )
            return guarded

        if activation_level == "MAIN_SIGNAL":
            guarded["can_publish"] = True
            guarded["should_observe"] = False
            guarded["should_block"] = False
            guarded["master_status"] = "MAIN_SIGNAL"
            guarded["master_rank"] = "MAIN_SIGNAL"
            guarded["master_action"] = "MOSTRAR_SEÑAL_PRINCIPAL"
            guarded["master_reason"] = activation_reason
            guarded["promotion_level"] = "MAIN_SIGNAL"
            guarded["elite_rank"] = "MAIN_SIGNAL"
            guarded["panel_section"] = "TOP_SIGNAL"
            guarded["panel_signal_type"] = activation_label or "SEÑAL PRINCIPAL"
            guarded["panel_label"] = activation_label or "SEÑAL PRINCIPAL"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(activation_score, 0),
                84,
            )
            return guarded

        if activation_level == "STRONG_CANDIDATE":
            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "STRONG_CANDIDATE"
            guarded["master_rank"] = "STRONG_CANDIDATE"
            guarded["master_action"] = "SEGUIR_CANDIDATO_FUERTE"
            guarded["master_reason"] = activation_reason
            guarded["promotion_level"] = "STRONG_CANDIDATE"
            guarded["elite_rank"] = "STRONG_CANDIDATE"
            guarded["panel_section"] = "STRONG_CANDIDATE"
            guarded["panel_signal_type"] = activation_label or "CANDIDATO FUERTE"
            guarded["panel_label"] = activation_label or "CANDIDATO FUERTE"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(activation_score, 0),
                74,
            )
            return guarded

        if activation_level == "EARLY_OVER_CANDIDATE":
            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "EARLY_OVER_CANDIDATE"
            guarded["master_rank"] = "EARLY_OVER_CANDIDATE"
            guarded["master_action"] = "SEGUIR_OVER_CANDIDATO_TEMPRANO"
            guarded["master_reason"] = activation_reason
            guarded["promotion_level"] = "EARLY_OVER_CANDIDATE"
            guarded["elite_rank"] = "EARLY_OVER_CANDIDATE"
            guarded["panel_section"] = "OVER_EARLY_CANDIDATE"
            guarded["panel_signal_type"] = activation_label or "OVER CANDIDATO TEMPRANO"
            guarded["panel_label"] = activation_label or "OVER CANDIDATO TEMPRANO"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(activation_score, 0),
                68,
            )
            return guarded

        if activation_level == "HIGH_OBSERVATION":
            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "HIGH_OBSERVATION"
            guarded["master_rank"] = "HIGH_OBSERVATION"
            guarded["master_action"] = "MANTENER_OBSERVACION_ALTA"
            guarded["master_reason"] = activation_reason
            guarded["promotion_level"] = "HIGH_OBSERVATION"
            guarded["elite_rank"] = "HIGH_OBSERVATION"
            guarded["panel_section"] = "HIGH_OBSERVATION"
            guarded["panel_signal_type"] = activation_label or "OBSERVACIÓN ALTA"
            guarded["panel_label"] = activation_label or "OBSERVACIÓN ALTA"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(activation_score, 0),
                58,
            )
            return guarded

        return guarded

    def _apply_signal_promotion_guard(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        guarded = dict(signal)

        promotion_level = str(guarded.get("promotion_level") or "OBSERVE_ONLY").upper()
        promotion_market = str(guarded.get("promotion_market") or "").upper()
        promotion_label = str(guarded.get("promotion_panel_label") or "")
        promotion_reason = str(guarded.get("promotion_reason") or "")
        promotion_priority = safe_int(guarded.get("promotion_priority"), 30)

        hard_blockers = list(guarded.get("hard_blockers", []) or [])
        promotion_blockers = list(guarded.get("promotion_blockers", []) or [])
        promotion_warnings = list(guarded.get("promotion_warnings", []) or [])

        existing_block = bool(guarded.get("should_block"))
        master_status = str(guarded.get("master_status") or "").upper()
        master_action = str(guarded.get("master_action") or "").upper()

        critical_block_active = (
            existing_block
            or "BLOCKED" in master_status
            or master_action in {"NO_OPERAR", "NO_BET", "AVOID"}
            or bool(promotion_blockers)
        )

        if promotion_level == "BLOCKED" or critical_block_active:
            block_reason = (
                guarded.get("panel_activation_reason")
                or guarded.get("activation_reason")
                or promotion_reason
                or "La señal presenta bloqueo crítico y no debe promoverse."
            )

            guarded["promotion_level"] = "BLOCKED"
            guarded["promotion_action"] = "NO_OPERAR"
            guarded["promotion_panel_label"] = "SEÑAL BLOQUEADA"
            guarded["panel_promotion_label"] = "SEÑAL BLOQUEADA"
            guarded["panel_signal_type"] = "SEÑAL BLOQUEADA"
            guarded["panel_label"] = "SEÑAL BLOQUEADA"
            guarded["promotion_reason"] = block_reason
            guarded["panel_promotion_reason"] = block_reason

            guarded["can_publish"] = False
            guarded["should_observe"] = False
            guarded["should_block"] = True
            guarded["master_status"] = "BLOCKED_BY_PROMOTION"
            guarded["master_rank"] = "BLOCKED"
            guarded["master_action"] = "NO_OPERAR"
            guarded["master_reason"] = block_reason

            guarded["hard_blockers"] = sorted(set(hard_blockers + promotion_blockers))
            guarded["soft_warnings"] = sorted(
                set(list(guarded.get("soft_warnings", []) or []) + promotion_warnings)
            )
            guarded["promotion_priority"] = 0

            return guarded

        if promotion_level == "TOP_SIGNAL":
            promotion_label = promotion_label or f"{promotion_market or 'OVER'} TOP SIGNAL"
            promotion_reason = promotion_reason or (
                "La señal alcanza nivel TOP porque el soporte live, la madurez, "
                "el riesgo y la fase del partido coinciden con suficiente fuerza."
            )

            guarded["can_publish"] = True
            guarded["should_observe"] = False
            guarded["should_block"] = False
            guarded["master_status"] = "TOP_SIGNAL"
            guarded["master_rank"] = "TOP_SIGNAL"
            guarded["master_action"] = "PRIORIZAR_TOP_SIGNAL"
            guarded["master_reason"] = promotion_reason
            guarded["elite_rank"] = "TOP_SIGNAL"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(guarded.get("promotion_score"), 0),
                90,
            )

        elif promotion_level == "MAIN_SIGNAL":
            promotion_label = promotion_label or f"{promotion_market or 'OVER'} SEÑAL PRINCIPAL"
            promotion_reason = promotion_reason or (
                "La señal sube a señal principal porque supera el umbral operativo "
                "y no presenta bloqueos críticos."
            )

            guarded["can_publish"] = True
            guarded["should_observe"] = False
            guarded["should_block"] = False
            guarded["master_status"] = "MAIN_SIGNAL"
            guarded["master_rank"] = "MAIN_SIGNAL"
            guarded["master_action"] = "MOSTRAR_SEÑAL_PRINCIPAL"
            guarded["master_reason"] = promotion_reason
            guarded["elite_rank"] = "MAIN_SIGNAL"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(guarded.get("promotion_score"), 0),
                80,
            )

        elif promotion_level == "STRONG_CANDIDATE":
            promotion_label = promotion_label or f"{promotion_market or 'OVER'} CANDIDATO FUERTE"
            promotion_reason = promotion_reason or (
                "La señal sube a candidato fuerte porque tiene soporte relevante, "
                "aunque todavía requiere seguimiento antes de considerarse top."
            )

            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "STRONG_CANDIDATE"
            guarded["master_rank"] = "STRONG_CANDIDATE"
            guarded["master_action"] = "SEGUIR_CANDIDATO_FUERTE"
            guarded["master_reason"] = promotion_reason
            guarded["elite_rank"] = "STRONG_CANDIDATE"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(guarded.get("promotion_score"), 0),
                70,
            )

        elif promotion_level == "EARLY_OVER_CANDIDATE":
            promotion_label = "OVER CANDIDATO TEMPRANO"
            promotion_reason = (
                "La lectura OVER sube a candidato temprano porque existe OVER WATCH activo, "
                "volumen ofensivo medible y riesgo de ruptura antes de una confirmación tardía."
            )

            guarded["promotion_market"] = "OVER"
            guarded["promotion_action"] = "MOSTRAR_COMO_OVER_CANDIDATO_TEMPRANO"
            guarded["promotion_panel_label"] = promotion_label
            guarded["panel_promotion_label"] = promotion_label
            guarded["panel_signal_type"] = promotion_label
            guarded["panel_label"] = promotion_label
            guarded["promotion_reason"] = promotion_reason
            guarded["panel_promotion_reason"] = promotion_reason

            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "EARLY_OVER_CANDIDATE"
            guarded["master_rank"] = "EARLY_OVER_CANDIDATE"
            guarded["master_action"] = "SEGUIR_OVER_CANDIDATO_TEMPRANO"
            guarded["master_reason"] = promotion_reason
            guarded["elite_rank"] = "EARLY_OVER_CANDIDATE"
            guarded["elite_score"] = max(
                safe_int(guarded.get("elite_score"), 0),
                safe_int(guarded.get("promotion_score"), 0),
                68,
            )
            guarded["promotion_priority"] = max(promotion_priority, 62)

            guarded["soft_warnings"] = sorted(
                set(list(guarded.get("soft_warnings", []) or []) + promotion_warnings)
            )

            return guarded

        elif promotion_level == "WAIT_REVALIDATION":
            promotion_label = promotion_label or f"{promotion_market or 'SEÑAL'} EN REVALIDACIÓN"
            promotion_reason = promotion_reason or "La señal requiere revalidación antes de subir."

            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = "WAIT_REVALIDATION"
            guarded["master_rank"] = "REVALIDATION"
            guarded["master_action"] = "ESPERAR_REVALIDACION"
            guarded["master_reason"] = promotion_reason

        else:
            if promotion_market == "OVER":
                promotion_label = promotion_label or "OVER EN OBSERVACIÓN"
            elif promotion_market == "UNDER":
                promotion_label = promotion_label or "UNDER EN OBSERVACIÓN"
            else:
                promotion_label = promotion_label or "OBSERVACIÓN"

            promotion_reason = promotion_reason or guarded.get("master_reason") or (
                "La señal permanece en observación porque no reúne respaldo suficiente para subir."
            )

            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False
            guarded["master_status"] = guarded.get("master_status") or "OBSERVE"
            guarded["master_rank"] = guarded.get("master_rank") or "OBSERVE"
            guarded["master_action"] = guarded.get("master_action") or "OBSERVAR"
            guarded["master_reason"] = guarded.get("master_reason") or promotion_reason

        guarded["promotion_panel_label"] = promotion_label
        guarded["panel_signal_type"] = promotion_label
        guarded["panel_promotion_label"] = promotion_label
        guarded["panel_label"] = promotion_label
        guarded["panel_promotion_reason"] = promotion_reason
        guarded["promotion_reason"] = promotion_reason
        guarded["promotion_priority"] = promotion_priority

        guarded["soft_warnings"] = sorted(
            set(list(guarded.get("soft_warnings", []) or []) + promotion_warnings)
        )

        return guarded

    def _apply_match_maturity_guard(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        guarded = dict(signal)

        should_demote = bool(guarded.get("match_maturity_should_demote"))
        no_strong_under = bool(guarded.get("match_maturity_no_strong_under"))
        entry_permission = str(guarded.get("match_maturity_entry_permission") or "")
        corrected_rank = str(guarded.get("match_maturity_corrected_rank") or "")
        panel_label = str(guarded.get("match_maturity_panel_label") or "")
        panel_note = str(guarded.get("match_maturity_panel_note") or "")

        if not should_demote and not no_strong_under:
            return guarded

        soft_warnings = list(guarded.get("soft_warnings", []) or [])
        maturity_warnings = list(guarded.get("match_maturity_warnings", []) or [])

        soft_warnings.append("MATCH_MATURITY_GUARD")

        for warning in maturity_warnings:
            soft_warnings.append(str(warning))

        guarded["soft_warnings"] = sorted(set(soft_warnings))

        guarded["can_publish"] = False
        guarded["should_observe"] = True

        if entry_permission == "BLOCK_ENTRY":
            guarded["should_block"] = True
            guarded["master_status"] = "BLOCKED_BY_MATURITY"
            guarded["master_rank"] = "BLOCKED_BY_MATURITY"
            guarded["master_action"] = "NO_OPERAR"
            guarded["master_reason"] = (
                "MatchMaturityAI bloqueó la entrada. "
                f"{panel_note}"
            )

        elif entry_permission == "WAIT_REVALIDATION":
            guarded["should_block"] = False
            guarded["master_status"] = "WAIT_REVALIDATION"
            guarded["master_rank"] = corrected_rank or "REVALIDATION"
            guarded["master_action"] = "ESPERAR_REVALIDACION"
            guarded["master_reason"] = (
                "MatchMaturityAI degradó la señal a revalidación. "
                f"{panel_note}"
            )

        elif entry_permission == "PANORAMA_ONLY":
            guarded["should_block"] = False
            guarded["master_status"] = "PANORAMA_ONLY"
            guarded["master_rank"] = corrected_rank or "PANORAMA"
            guarded["master_action"] = "SOLO_PANORAMA"
            guarded["master_reason"] = (
                "MatchMaturityAI detectó panorama futbolístico, "
                "pero todavía no autorizó entrada. "
                f"{panel_note}"
            )

        else:
            guarded["should_block"] = False
            guarded["master_status"] = "OBSERVE"
            guarded["master_rank"] = corrected_rank or "OBSERVATION"
            guarded["master_action"] = "OBSERVAR"
            guarded["master_reason"] = (
                "MatchMaturityAI envió la señal a observación. "
                f"{panel_note}"
            )

        guarded["candidate_level"] = guarded.get("candidate_level") or "MATURITY_REVALIDATION"
        guarded["recommended_panel_message"] = panel_note
        guarded["main_reading"] = panel_note

        if panel_label:
            guarded["panel_maturity_label"] = panel_label

        hard_blockers = list(guarded.get("hard_blockers", []) or [])

        if entry_permission == "BLOCK_ENTRY":
            hard_blockers.append("MATCH_MATURITY_BLOCK")

        guarded["hard_blockers"] = sorted(set(hard_blockers))

        return guarded

    def _apply_decision_explainer_guard(
        self,
        master: Dict[str, Any],
        decision_explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        guarded = dict(master)

        decision_valid = bool(decision_explanation.get("decision_valid", True))
        recommended_demotion = decision_explanation.get("recommended_demotion")
        logic_status = str(decision_explanation.get("logic_status") or "")

        if decision_valid:
            return guarded

        if recommended_demotion == "WAIT_CONFIRMATION":
            old_reason = str(guarded.get("master_reason") or "")

            guarded["master_status"] = "WAIT_CONFIRMATION"
            guarded["master_rank"] = "OBSERVE"
            guarded["master_action"] = "ESPERAR_CONFIRMACION"
            guarded["can_publish"] = False
            guarded["should_observe"] = True
            guarded["should_block"] = False

            guarded["master_reason"] = (
                "La auditoría lógica V17 degradó la señal a observación. "
                f"Estado lógico: {logic_status}. "
                f"Motivo previo: {old_reason}"
            )

            soft_warnings = list(guarded.get("soft_warnings", []) or [])
            soft_warnings.append("DECISION_EXPLAINER_DEMOTION")

            for warning in decision_explanation.get("logic_warnings", []) or []:
                soft_warnings.append(str(warning))

            guarded["soft_warnings"] = sorted(set(soft_warnings))

        return guarded

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
        over_candidate: Dict[str, Any],
        league_volatility: Dict[str, Any],
        match_reader: Dict[str, Any],
        master: Dict[str, Any],
        decision_explanation: Dict[str, Any],
        pre_match_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pre_match_profile = pre_match_profile or {}

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

        suggested_market = str(
            master.get("master_market")
            or market.get("suggested_market")
            or "NO_BET"
        ).upper()

        main_reading = self._build_main_reading(
            suggested_market=suggested_market,
            decision_explanation=decision_explanation,
            match_reader=match_reader,
        )

        what_is_missing = self._build_missing_text(
            master=master,
            clock=clock,
            data_quality=data_quality,
            risk=risk,
            contradiction=contradiction,
            decision_explanation=decision_explanation,
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

            "home_logo": match.get("home_logo") or match.get("home_team_logo") or match.get("local_logo"),
            "away_logo": match.get("away_logo") or match.get("away_team_logo") or match.get("visitor_logo"),
            "league_logo": match.get("league_logo") or match.get("competition_logo"),
            "country_flag": match.get("country_flag") or match.get("league_flag") or match.get("flag"),

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

            "shots": match.get("shots", 0),
            "shots_on_target": match.get("shots_on_target", 0),
            "corners": match.get("corners", 0),
            "xg": match.get("xg") or match.get("xG") or 0,
            "xG": match.get("xg") or match.get("xG") or 0,
            "dangerous_attacks": match.get("dangerous_attacks", 0),
            "red_cards": match.get("red_cards", 0),
            "possession_home": match.get("possession_home", 0),
            "possession_away": match.get("possession_away", 0),

            "data_quality": match.get("data_quality") or data_quality.get("data_quality"),
            "scan_phase": match.get("scan_phase"),
            "scan_reason": match.get("scan_reason"),
            "stats_source": match.get("stats_source"),
            "can_publish_signal": match.get("can_publish_signal"),
            "can_observe_signal": match.get("can_observe_signal"),
            "is_scannable": match.get("is_scannable"),

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

            "decision_valid": decision_explanation.get("decision_valid"),
            "logic_status": decision_explanation.get("logic_status"),
            "candidate_level": decision_explanation.get("candidate_level"),
            "recommended_demotion": decision_explanation.get("recommended_demotion"),
            "logic_warnings": decision_explanation.get("logic_warnings", []),

            "majority_support": decision_explanation.get("majority_support"),
            "support_score": decision_explanation.get("support_score"),
            "support_ratio": decision_explanation.get("support_ratio"),
            "non_critical_missing_count": decision_explanation.get("non_critical_missing_count"),
            "critical_block": decision_explanation.get("critical_block"),

            "why_selected": decision_explanation.get("why_selected"),
            "why_not_over": decision_explanation.get("why_not_over"),
            "why_not_under": decision_explanation.get("why_not_under"),
            "support_points": decision_explanation.get("support_points", []),
            "missing_points": decision_explanation.get("missing_points", []),
            "recommended_panel_message": decision_explanation.get("recommended_panel_message"),
            "explain_scores": decision_explanation.get("explain_scores", {}),

            "over_candidate_level": over_candidate.get("over_candidate_level"),
            "over_candidate_active": over_candidate.get("over_candidate_active"),
            "over_majority_support": over_candidate.get("over_majority_support"),
            "over_support_score": over_candidate.get("over_support_score"),
            "over_support_total": over_candidate.get("over_support_total"),
            "over_support_ratio": over_candidate.get("over_support_ratio"),
            "over_market_gap": over_candidate.get("over_market_gap"),
            "over_volume_profile": over_candidate.get("over_volume_profile", {}),
            "over_blockers": over_candidate.get("over_blockers", []),
            "over_support_points": over_candidate.get("over_support_points", []),
            "over_missing_points": over_candidate.get("over_missing_points", []),
            "why_over_candidate": over_candidate.get("why_over_candidate"),
            "why_over_not_ready": over_candidate.get("why_over_not_ready"),

            "league_context_group": league_volatility.get("league_context_group"),
            "league_volatility_level": league_volatility.get("league_volatility_level"),
            "league_half_context": league_volatility.get("league_half_context"),
            "league_minute_phase": league_volatility.get("league_minute_phase"),
            "league_panel_modifier": league_volatility.get("league_panel_modifier"),
            "league_confidence_adjustment": league_volatility.get("league_confidence_adjustment"),
            "league_publish_modifier": league_volatility.get("league_publish_modifier"),
            "league_revalidation_required": league_volatility.get("league_revalidation_required"),
            "league_warning": league_volatility.get("league_warning"),
            "league_late_game_reading": league_volatility.get("league_late_game_reading"),
            "league_first_half_reading": league_volatility.get("league_first_half_reading"),
            "league_over_permission": league_volatility.get("league_over_permission"),
            "league_under_permission": league_volatility.get("league_under_permission"),
            "league_reason": league_volatility.get("league_reason"),
            "league_support_points": league_volatility.get("league_support_points", []),
            "league_caution_points": league_volatility.get("league_caution_points", []),

            "pre_match_profile_version": pre_match_profile.get("pre_match_profile_version"),
            "pre_match_available": pre_match_profile.get("pre_match_available"),
            "pre_match_source": pre_match_profile.get("pre_match_source"),
            "pre_match_ok": pre_match_profile.get("pre_match_ok"),
            "pre_match_cache_status": pre_match_profile.get("pre_match_cache_status"),
            "pre_match_fixture_id": pre_match_profile.get("pre_match_fixture_id"),
            "pre_match_league": pre_match_profile.get("pre_match_league"),
            "pre_match_country": pre_match_profile.get("pre_match_country"),
            "pre_match_home_team": pre_match_profile.get("pre_match_home_team"),
            "pre_match_away_team": pre_match_profile.get("pre_match_away_team"),

            "league_goal_profile": pre_match_profile.get("league_goal_profile"),
            "team_goal_profile": pre_match_profile.get("team_goal_profile"),
            "first_half_profile": pre_match_profile.get("first_half_profile"),
            "second_half_profile": pre_match_profile.get("second_half_profile"),
            "first_half_goal_risk": pre_match_profile.get("first_half_goal_risk"),
            "second_half_goal_risk": pre_match_profile.get("second_half_goal_risk"),
            "under_early_risk": pre_match_profile.get("under_early_risk"),

            "over_support_pre_match": pre_match_profile.get("over_support_pre_match"),
            "under_support_pre_match": pre_match_profile.get("under_support_pre_match"),
            "over_pre_match_score": pre_match_profile.get("over_pre_match_score"),
            "under_pre_match_score": pre_match_profile.get("under_pre_match_score"),

            "pre_match_avg_total_goals": pre_match_profile.get("pre_match_avg_total_goals"),
            "pre_match_avg_first_half_goals": pre_match_profile.get("pre_match_avg_first_half_goals"),
            "pre_match_avg_second_half_goals": pre_match_profile.get("pre_match_avg_second_half_goals"),

            "home_recent_goal_profile": pre_match_profile.get("home_recent_goal_profile"),
            "away_recent_goal_profile": pre_match_profile.get("away_recent_goal_profile"),
            "league_recent_goal_profile": pre_match_profile.get("league_recent_goal_profile"),

            "home_recent_over_15_rate": pre_match_profile.get("home_recent_over_15_rate"),
            "away_recent_over_15_rate": pre_match_profile.get("away_recent_over_15_rate"),
            "home_recent_over_25_rate": pre_match_profile.get("home_recent_over_25_rate"),
            "away_recent_over_25_rate": pre_match_profile.get("away_recent_over_25_rate"),
            "home_recent_btts_rate": pre_match_profile.get("home_recent_btts_rate"),
            "away_recent_btts_rate": pre_match_profile.get("away_recent_btts_rate"),
            "league_recent_over_25_rate": pre_match_profile.get("league_recent_over_25_rate"),
            "league_recent_btts_rate": pre_match_profile.get("league_recent_btts_rate"),

            "pre_match_support_points": pre_match_profile.get("pre_match_support_points", []),
            "pre_match_caution_points": pre_match_profile.get("pre_match_caution_points", []),
            "pre_match_recommended_behavior": pre_match_profile.get("pre_match_recommended_behavior"),
            "pre_match_panel_note": pre_match_profile.get("pre_match_panel_note"),

            "match_reader_version": match_reader.get("match_reader_version"),
            "football_game_phase": match_reader.get("football_game_phase"),
            "football_game_state": match_reader.get("football_game_state"),
            "football_dominant_reading": match_reader.get("football_dominant_reading"),
            "football_alternative_reading": match_reader.get("football_alternative_reading"),
            "football_confidence": match_reader.get("football_confidence"),
            "football_warning_level": match_reader.get("football_warning_level"),
            "football_story": match_reader.get("football_story"),
            "football_support_points": match_reader.get("football_support_points", []),
            "football_caution_points": match_reader.get("football_caution_points", []),
            "football_league_note": match_reader.get("football_league_note"),
            "football_real_offensive_volume": match_reader.get("football_real_offensive_volume"),
            "football_pressure_type": match_reader.get("football_pressure_type"),

            **clock,
            **data_quality,
            **context,
            **tactical,
            **market,
            **risk,
            **contradiction,
        }

    def _build_main_reading(
        self,
        suggested_market: str,
        decision_explanation: Dict[str, Any],
        match_reader: Dict[str, Any],
    ) -> str:
        football_story = match_reader.get("football_story")
        if football_story:
            return str(football_story)

        panel_message = decision_explanation.get("recommended_panel_message")
        if panel_message:
            return str(panel_message)

        if suggested_market == "OVER":
            return "El partido muestra posibilidad de más goles, condicionado a presión real y reloj confiable."

        if suggested_market == "UNDER":
            return "El partido muestra tendencia de cierre, retención o baja profundidad ofensiva."

        if suggested_market == "OBSERVE":
            return "El partido tiene señales parciales, pero todavía requiere confirmación."

        return "No existe ventaja suficiente para operar."

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
        decision_explanation: Dict[str, Any],
    ) -> str:
        hard_blockers = master.get("hard_blockers") or []
        secondary = master.get("failed_secondary_filters") or []
        warnings = master.get("soft_warnings") or []

        missing_points = decision_explanation.get("missing_points") or []
        logic_warnings = decision_explanation.get("logic_warnings") or []

        if hard_blockers:
            return "Bloqueo crítico: " + ", ".join(map(str, hard_blockers[:4]))

        if logic_warnings:
            return "Auditoría V17: " + ", ".join(map(str, logic_warnings[:3]))

        if missing_points:
            return "Falta: " + ", ".join(map(str, missing_points[:3]))

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
