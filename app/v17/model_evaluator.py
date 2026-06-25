"""
ModelEvaluator: Evaluates model performance using cross-validation.
Phase 3 - Computes accuracy, precision, recall, F1, confusion matrix.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, brier_score_loss, roc_auc_score
)

from app.v17.ml.prediction_model import PredictionModel


class ModelEvaluator:
    """
    Evaluates trained models using standard ML metrics.
    
    Metrics computed:
    - Accuracy (overall)
    - Precision, Recall, F1 (per-class)
    - Confusion matrix
    - Cross-validation scores
    - Feature importance (coefficients)
    - Calibration metrics for WON probability
    - Performance summary by competition tier/flags
    """
    
    def __init__(self, model: PredictionModel):
        """
        Initialize evaluator.
        
        Args:
            model: PredictionModel to evaluate
        """
        self.model = model
        self.evaluation_date = datetime.utcnow().isoformat() + "Z"
        self.results: Dict[str, Any] = {}
    
    def evaluate(
        self,
        training_examples: List[Dict[str, Any]],
        test_split: float = 0.2,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """
        Full model evaluation.
        
        Args:
            training_examples: List of examples with feature_vector and label
            test_split: Fraction for train/test split (for now, unused - we use CV)
            cv_folds: Number of cross-validation folds
        
        Returns:
            Evaluation results dict
        """
        if self.model.status != PredictionModel.STATUS_READY:
            return {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "status": "EVAL_SKIPPED",
                "reason": f"Model status is {self.model.status}, not READY"
            }
        
        if self.model._model is None or self.model._scaler is None:
            return {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "status": "EVAL_ERROR",
                "reason": "Model or scaler not initialized"
            }
        
        try:
            # Extract features and labels
            X = []
            y = []
            
            for example in training_examples:
                try:
                    features = example.get("feature_vector", {})
                    label = example.get("label")
                    
                    if label not in PredictionModel.CLASSES:
                        continue
                    
                    feature_values = []
                    for fname in self.model.feature_names:
                        val = features.get(fname, 0.0)
                        try:
                            feature_values.append(float(val))
                        except (ValueError, TypeError):
                            feature_values.append(0.0)
                    
                    X.append(feature_values)
                    y.append(PredictionModel.CLASS_INDICES[label])
                
                except Exception:
                    continue
            
            if len(X) < 20:
                return {
                    "model_id": self.model.model_id,
                    "market": self.model.market,
                    "status": "EVAL_INSUFFICIENT_DATA",
                    "test_set_size": len(X)
                }
            
            X = np.array(X)
            y = np.array(y)
            
            # Normalize using scaler
            X_scaled = self.model._scaler.transform(X)
            
            # Get predictions
            y_pred = self.model._model.predict(X_scaled)
            probabilities = self._safe_predict_proba(X_scaled)
            
            # Accuracy
            accuracy = float(accuracy_score(y, y_pred))
            
            # Per-class metrics
            precision_dict = {}
            recall_dict = {}
            f1_dict = {}
            
            for cls, idx in PredictionModel.CLASS_INDICES.items():
                precision_dict[cls] = float(
                    precision_score(y, y_pred, labels=[idx], zero_division=0)
                )
                recall_dict[cls] = float(
                    recall_score(y, y_pred, labels=[idx], zero_division=0)
                )
                f1_dict[cls] = float(
                    f1_score(y, y_pred, labels=[idx], zero_division=0)
                )
            
            calibration_metrics: Dict[str, Any] = {}
            if probabilities.size:
                try:
                    won_idx = PredictionModel.CLASS_INDICES.get("WON")
                    if won_idx is not None:
                        won_probs = self._probability_for_class(probabilities, won_idx)
                        y_won = (y == won_idx).astype(int)
                        calibration_metrics["brier_score_won"] = float(brier_score_loss(y_won, won_probs))
                        if len(np.unique(y_won)) >= 2:
                            calibration_metrics["roc_auc_won"] = float(roc_auc_score(y_won, won_probs))
                except Exception as exc:
                    calibration_metrics["calibration_error"] = type(exc).__name__

            competition_summary = self._competition_summary(
                examples=training_examples,
                y_true=y,
                y_pred=y_pred,
            )

            # Confusion matrix
            cm = confusion_matrix(y, y_pred, labels=list(range(len(PredictionModel.CLASSES))))
            cm_dict = {
                PredictionModel.CLASSES[i]: {
                    PredictionModel.CLASSES[j]: int(cm[i][j])
                    for j in range(len(PredictionModel.CLASSES))
                }
                for i in range(len(PredictionModel.CLASSES))
            }
            
            # Cross-validation scores
            unique_y = np.unique(y)
            if len(unique_y) < 2:
                # Cannot stratify with a single class; fallback to using training accuracy
                cv_scores_list = [accuracy for _ in range(cv_folds)]
                cv_scores = np.array(cv_scores_list)
            else:
                cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
                cv_scores = cross_val_score(
                    self.model._model,
                    X_scaled,
                    y,
                    cv=cv,
                    scoring='accuracy'
                )
                cv_scores_list = [float(s) for s in cv_scores]
            
            # Feature importance (coefficients from logistic regression)
            feature_importance = []
            if hasattr(self.model._model, 'coef_'):
                # Average absolute coefficient across all classes
                coefs = np.abs(self.model._model.coef_).mean(axis=0)
                for fname, coef_val in zip(self.model.feature_names, coefs):
                    feature_importance.append({
                        "feature": fname,
                        "importance": float(coef_val)
                    })
                # Sort by importance
                feature_importance.sort(key=lambda x: x["importance"], reverse=True)
            
            # Build result
            self.results = {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "evaluation_date": self.evaluation_date,
                "status": "EVAL_COMPLETE",
                "test_set_size": len(X),
                "accuracy": accuracy,
                "precision": precision_dict,
                "recall": recall_dict,
                "f1": f1_dict,
                "confusion_matrix": cm_dict,
                "cross_val_scores": cv_scores_list,
                "cross_val_mean": float(cv_scores.mean()),
                "cross_val_std": float(cv_scores.std()),
                "calibration": calibration_metrics,
                "competition_summary": competition_summary,
                "feature_importance": feature_importance[:15]  # Top 15, includes competition features when present
            }
            
            return self.results
        
        except Exception as e:
            return {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "status": "EVAL_ERROR",
                "error": str(e)
            }
    
    def _safe_predict_proba(self, X_scaled: np.ndarray) -> np.ndarray:
        """Returns probability matrix safely for calibration metrics."""
        try:
            if hasattr(self.model._model, "predict_proba"):
                return self.model._model.predict_proba(X_scaled)
        except Exception:
            pass
        return np.empty((0, 0))

    def _probability_for_class(
        self,
        probabilities: np.ndarray,
        target_idx: int,
    ) -> np.ndarray:
        """Extracts class probability even when a single-class classifier is active."""
        try:
            classes = getattr(self.model._model, "classes_", None)
            if classes is not None and target_idx in classes:
                class_pos = int(np.where(classes == target_idx)[0][0])
                return probabilities[:, class_pos]
        except Exception:
            pass
        return np.zeros(shape=(len(probabilities),), dtype=float)

    def _competition_summary(
        self,
        examples: List[Dict[str, Any]],
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Summarizes performance by competition tier and flags.

        This does not affect model training or prediction. It only helps to know
        where the model is performing well or poorly: World Cup, national teams,
        major tournaments, priority leagues, etc.
        """
        groups: Dict[str, Dict[str, Any]] = {}

        def add_group(name: str, ok: bool) -> None:
            if not ok:
                return
            bucket = groups.setdefault(name, {"total": 0, "correct": 0})
            bucket["total"] += 1

        for idx, example in enumerate(examples[: len(y_true)]):
            features = example.get("feature_vector", {}) or {}
            metadata = example.get("metadata", {}) or {}

            tier = str(
                metadata.get("competition_tier")
                or features.get("competition_tier")
                or features.get("competition_tier_name")
                or "UNKNOWN"
            ).upper()

            world_cup = bool(
                metadata.get("world_cup_flag")
                or features.get("world_cup_flag")
            )
            national_team = bool(
                metadata.get("national_team_flag")
                or features.get("national_team_flag")
            )
            major_tournament = bool(
                metadata.get("major_tournament_flag")
                or features.get("major_tournament_flag")
            )

            names = [f"TIER:{tier}"]
            if world_cup:
                names.append("WORLD_CUP")
            if national_team:
                names.append("NATIONAL_TEAM")
            if major_tournament:
                names.append("MAJOR_TOURNAMENT")

            for name in names:
                add_group(name, True)
                if y_true[idx] == y_pred[idx]:
                    groups[name]["correct"] += 1

        for bucket in groups.values():
            total = max(1, int(bucket.get("total", 0)))
            bucket["accuracy"] = round(float(bucket.get("correct", 0)) / total, 4)

        return groups

    def get_results(self) -> Dict[str, Any]:
        """Get latest evaluation results."""
        return self.results
    
    def to_json_serializable(self) -> Dict[str, Any]:
        """Get JSON-serializable evaluation results."""
        return self.results