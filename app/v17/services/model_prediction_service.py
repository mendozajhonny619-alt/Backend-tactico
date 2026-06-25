"""
ModelPredictionService: Orchestrates model predictions and feedback recording.
Phase 3 - Safely integrates model predictions into signal pipeline without affecting decisions.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.v17.ml.prediction_model import PredictionModel
from app.v17.ml.model_registry import ModelRegistry


class ModelPredictionService:
    """
    Manages model predictions in production.
    
    Responsibilities:
    - Get active model for a market
    - Make predictions on feature vectors
    - Record feedback when signals resolve
    - Track prediction history for performance analysis
    """
    
    def __init__(self, model_registry: ModelRegistry, feedback_storage_dir: str = None):
        """
        Initialize service.
        
        Args:
            model_registry: ModelRegistry instance
            feedback_storage_dir: Path to store feedback (optional)
        """
        self.model_registry = model_registry
        self.feedback_storage_dir = feedback_storage_dir
        self.prediction_history: Dict[str, Dict[str, Any]] = {}
    
    def make_prediction(
        self,
        market: str,
        feature_vector: Dict[str, Any],
        signal_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a model prediction for a feature vector.
        
        Args:
            market: "OVER" or "UNDER"
            feature_vector: Dict of feature_name -> value
            signal_key: Optional signal identifier for tracking
            metadata: Optional match/signal metadata for later feedback analysis
        
        Returns:
            Dict with:
            - "has_prediction": bool
            - "model_id": str (if prediction made)
            - "market": str
            - "predicted_class": str (WON/LOST/VOID)
            - "probabilities": Dict[class, probability]
            - "prediction_timestamp": ISO datetime
            Or empty dict if model not ready
        """
        try:
            # Get active model
            model = self.model_registry.get_active_model(market)
            if model is None:
                return {
                    "has_prediction": False,
                    "reason": f"No active model for {market}"
                }
            
            if model.status != PredictionModel.STATUS_READY:
                return {
                    "has_prediction": False,
                    "reason": f"Model status is {model.status}"
                }
            
            # Make prediction
            probabilities = model.predict(feature_vector)
            if not probabilities:
                return {
                    "has_prediction": False,
                    "reason": "Model prediction failed"
                }
            
            # Determine predicted class (highest probability)
            predicted_class = max(probabilities, key=probabilities.get)
            predicted_probability = probabilities[predicted_class]
            
            # Build result
            metadata = metadata or {}
            result = {
                "has_prediction": True,
                "model_id": model.model_id,
                "market": market,
                "predicted_class": predicted_class,
                "probabilities": probabilities,
                "predicted_probability": predicted_probability,
                "prediction_timestamp": datetime.utcnow().isoformat() + "Z",
                # V17 competition intelligence metadata. These fields are optional
                # and do not affect the live decision. They are stored for later
                # performance analysis, especially for World Cup / elite tournaments.
                "competition_tier": metadata.get("competition_tier"),
                "competition_weight": metadata.get("competition_weight"),
                "world_cup_flag": metadata.get("world_cup_flag"),
                "national_team_flag": metadata.get("national_team_flag"),
                "major_tournament_flag": metadata.get("major_tournament_flag"),
                "league_filter_status": metadata.get("league_filter_status"),
                "league_filter_reason": metadata.get("league_filter_reason"),
            }
            
            # Store in history if signal_key provided
            if signal_key:
                self.prediction_history[signal_key] = result
            
            return result
        
        except Exception as e:
            return {
                "has_prediction": False,
                "error": str(e)
            }
    
    def record_feedback(
        self,
        signal_key: str,
        fixture_id: str,
        league: str,
        market: str,
        market_category: str,
        actual_result: str,
        current_score: Optional[str] = None,
        current_total_goals: Optional[int] = None,
        competition_tier: Optional[str] = None,
        competition_weight: Optional[float] = None,
        world_cup_flag: Optional[bool] = None,
        national_team_flag: Optional[bool] = None,
        major_tournament_flag: Optional[bool] = None,
        league_filter_status: Optional[str] = None,
        league_filter_reason: Optional[str] = None
    ) -> bool:
        """
        Record feedback when a signal resolves.
        
        Args:
            signal_key: Signal identifier
            fixture_id: Match fixture ID
            league: League name
            market: "OVER" or "UNDER"
            market_category: Category (e.g., "NEXT_GOAL", "HALFTIME")
            actual_result: "WON", "LOST", "VOID", or "UNRESOLVED"
            current_score: Score at resolution
            current_total_goals: Total goals at resolution
            competition_tier: Optional competition tier from LeagueFilter
            competition_weight: Optional competition weight from LeagueFilter
            world_cup_flag: Whether the signal belongs to World Cup context
            national_team_flag: Whether the signal belongs to national teams
            major_tournament_flag: Whether the signal belongs to a major tournament
            league_filter_status: LeagueFilter status at ingestion
            league_filter_reason: LeagueFilter reason at ingestion
        
        Returns:
            True if feedback recorded successfully
        """
        try:
            # Get prediction from history
            prediction = self.prediction_history.get(signal_key, {})
            
            feedback = {
                "signal_key": signal_key,
                "fixture_id": fixture_id,
                "league": league,
                "market": market,
                "market_category": market_category,
                "model_id": prediction.get("model_id"),
                "predicted_class": prediction.get("predicted_class"),
                "predicted_probability": prediction.get("predicted_probability"),
                "probabilities": prediction.get("probabilities", {}),
                "actual_result": actual_result,
                "current_score": current_score,
                "current_total_goals": current_total_goals,
                "competition_tier": competition_tier or prediction.get("competition_tier"),
                "competition_weight": competition_weight if competition_weight is not None else prediction.get("competition_weight"),
                "world_cup_flag": world_cup_flag if world_cup_flag is not None else prediction.get("world_cup_flag"),
                "national_team_flag": national_team_flag if national_team_flag is not None else prediction.get("national_team_flag"),
                "major_tournament_flag": major_tournament_flag if major_tournament_flag is not None else prediction.get("major_tournament_flag"),
                "league_filter_status": league_filter_status or prediction.get("league_filter_status"),
                "league_filter_reason": league_filter_reason or prediction.get("league_filter_reason"),
                "feedback_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Store feedback (will be read by PerformanceAnalyzer)
            if self.feedback_storage_dir:
                self._append_feedback(feedback)
            
            return True
        
        except Exception as e:
            print(f"Warning: Failed to record feedback: {e}")
            return False
    
    def _append_feedback(self, feedback: Dict[str, Any]):
        """Append feedback to JSONL file."""
        try:
            from pathlib import Path
            feedback_file = Path(self.feedback_storage_dir) / "model_feedback.jsonl"
            with open(feedback_file, 'a') as f:
                f.write(json.dumps(feedback) + "\n")
        except Exception as e:
            print(f"Warning: Failed to append feedback: {e}")
    
    def get_feedback_for_analysis(self) -> List[Dict[str, Any]]:
        """
        Read all feedback for performance analysis.
        
        Returns:
            List of feedback dicts
        """
        feedback = []
        try:
            if not self.feedback_storage_dir:
                return feedback
            
            from pathlib import Path
            feedback_file = Path(self.feedback_storage_dir) / "model_feedback.jsonl"
            if feedback_file.exists():
                with open(feedback_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                feedback.append(json.loads(line))
                            except Exception:
                                pass
        except Exception:
            pass
        
        return feedback
    

    def get_feedback_summary_by_competition(self) -> Dict[str, Any]:
        """
        Summarize stored model feedback by competition tier.

        This is intentionally read-only and safe: it does not affect live decisions.
        It helps evaluate whether the ML layer performs differently in World Cup,
        elite tournaments, national-team matches, and standard leagues.
        """
        feedback = self.get_feedback_for_analysis()
        summary: Dict[str, Dict[str, Any]] = {}

        for row in feedback:
            tier = str(row.get("competition_tier") or "UNKNOWN").upper()
            if tier not in summary:
                summary[tier] = {
                    "total": 0,
                    "won": 0,
                    "lost": 0,
                    "void": 0,
                    "unresolved": 0,
                    "world_cup": 0,
                    "national_team": 0,
                    "major_tournament": 0,
                }

            bucket = summary[tier]
            bucket["total"] += 1

            actual = str(row.get("actual_result") or "UNRESOLVED").upper()
            if actual == "WON":
                bucket["won"] += 1
            elif actual == "LOST":
                bucket["lost"] += 1
            elif actual == "VOID":
                bucket["void"] += 1
            else:
                bucket["unresolved"] += 1

            if bool(row.get("world_cup_flag")):
                bucket["world_cup"] += 1
            if bool(row.get("national_team_flag")):
                bucket["national_team"] += 1
            if bool(row.get("major_tournament_flag")):
                bucket["major_tournament"] += 1

        for bucket in summary.values():
            resolved = bucket["won"] + bucket["lost"]
            bucket["accuracy"] = round((bucket["won"] / resolved) * 100, 2) if resolved else 0.0

        return summary

    def clear_prediction_history(self):
        """Clear in-memory prediction history (for long-running processes)."""
        self.prediction_history.clear()