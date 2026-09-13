"""
PredictionModel: Encapsulates ML model for binary/multiclass prediction.
Phase 3 - Parallel ML infrastructure for V17.

Uses LogisticRegression for interpretability and stability.
MODEL_NOT_READY state if training examples < 300.
"""

import inspect
import json
import pickle
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import numpy as np


class SingleClassClassifier:
    """Lightweight classifier used when training data contains a single class.

    Implemented at module level so instances are picklable for persistence.
    """
    def __init__(self, label: int):
        self.classes_ = np.array([int(label)], dtype=int)
        self.label_ = int(label)

    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.full(shape=(len(X),), fill_value=self.label_, dtype=int)

    def predict_proba(self, X):
        # single column of probability 1.0 for the single class
        return np.ones((len(X), 1), dtype=float)


class PredictionModel:
    """
    Encapsulates a trained model for predicting signal outcomes.
    
    Attributes:
        model_id: Unique identifier (UUID)
        market: Target market (OVER, UNDER)
        version: Timestamp of model creation
        trained_on_count: Number of training examples used
        status: MODEL_READY, MODEL_NOT_READY, MODEL_ERROR
        accuracy_on_training: Training set accuracy (if trained)
        feature_names: Ordered list of feature names used
        _model: sklearn LogisticRegression instance
        _scaler: sklearn StandardScaler for feature normalization
        metadata: Additional metadata dict
    """
    
    # Status constants
    STATUS_READY = "MODEL_READY"
    STATUS_NOT_READY = "MODEL_NOT_READY"
    STATUS_ERROR = "MODEL_ERROR"
    
    # Minimum training examples threshold
    MIN_TRAINING_EXAMPLES = 300
    
    # Outcome classes
    CLASSES = ["WON", "LOST", "VOID"]
    CLASS_INDICES = {cls: idx for idx, cls in enumerate(CLASSES)}

    # V17 competition intelligence features.
    # These features are optional and backward-compatible: if older training
    # examples do not contain them, they are injected with 0.0.
    COMPETITION_FEATURE_NAMES = [
        "competition_weight",
        "world_cup_flag",
        "national_team_flag",
        "major_tournament_flag",
        "competition_tier_world_cup_elite",
        "competition_tier_international_club_elite",
        "competition_tier_national_team_elite",
        "competition_tier_priority_league",
        "competition_tier_country_review",
    ]
    
    def __init__(
        self,
        market: str,
        model_id: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new PredictionModel.
        
        Args:
            market: "OVER" or "UNDER"
            model_id: UUID (auto-generated if not provided)
            version: ISO timestamp (auto-generated if not provided)
            metadata: Optional metadata dict
        """
        self.market = market
        self.model_id = model_id or str(uuid.uuid4())
        self.version = version or datetime.utcnow().isoformat() + "Z"
        self.trained_on_count = 0
        self.status = self.STATUS_NOT_READY
        self.accuracy_on_training = 0.0
        self.feature_names: List[str] = []
        self.metadata = metadata or {}
        
        # ML components (initialized on training)
        self._model: Optional[LogisticRegression] = None
        self._scaler: Optional[StandardScaler] = None
    
    def train(
        self,
        training_examples: List[Dict[str, Any]],
        feature_names: List[str]
    ) -> bool:
        """
        Train the model on a set of examples.
        
        Args:
            training_examples: List of dicts with keys:
                - "feature_vector": dict of feature_name -> value
                - "label": "WON", "LOST", or "VOID"
            feature_names: Ordered list of features to use
        
        Returns:
            True if training successful, False otherwise
        """
        try:
            # Validate minimum examples
            if len(training_examples) < self.MIN_TRAINING_EXAMPLES:
                self.status = self.STATUS_NOT_READY
                self.trained_on_count = len(training_examples)
                return False
            
            # Make feature schema stable and compatible with the new V17
            # competition intelligence fields.
            feature_names = self._normalize_feature_names(
                feature_names=feature_names,
                training_examples=training_examples,
            )

            # Extract features and labels
            X = []
            y = []
            valid_count = 0
            
            for example in training_examples:
                try:
                    features = example.get("feature_vector", {})
                    label = example.get("label")
                    
                    # Skip invalid examples
                    if label not in self.CLASSES:
                        continue
                    
                    # Build feature vector in correct order
                    feature_values = []
                    for fname in feature_names:
                        val = features.get(fname, 0.0)
                        try:
                            feature_values.append(float(val))
                        except (ValueError, TypeError):
                            feature_values.append(0.0)
                    
                    X.append(feature_values)
                    y.append(self.CLASS_INDICES[label])
                    valid_count += 1
                
                except Exception:
                    continue
            
            # Verify we have enough valid examples
            if valid_count < self.MIN_TRAINING_EXAMPLES:
                self.status = self.STATUS_NOT_READY
                self.trained_on_count = valid_count
                return False
            
            # Convert to numpy arrays
            X = np.array(X)
            y = np.array(y)
            
            # Fit scaler and normalize features
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)
            
            # Choose classifier based on available classes
            unique_classes = np.unique(y)
            if len(unique_classes) == 1:
                # Use module-level SingleClassClassifier so instances are picklable
                self._model = SingleClassClassifier(unique_classes[0])
            else:
                model_kwargs = {
                    "max_iter": 1000,
                    "solver": "lbfgs",
                    "random_state": 42,
                    "C": 1.0,
                }
                if "multi_class" in inspect.signature(LogisticRegression.__init__).parameters:
                    model_kwargs["multi_class"] = "multinomial"

                self._model = LogisticRegression(**model_kwargs)

            self._model.fit(X_scaled, y)
            
            # Compute training accuracy
            train_pred = self._model.predict(X_scaled)
            self.accuracy_on_training = float(np.mean(train_pred == y))
            
            # Update state
            self.feature_names = feature_names
            self.trained_on_count = valid_count
            self.status = self.STATUS_READY
            self.version = datetime.utcnow().isoformat() + "Z"
            self.metadata.update(self._build_training_metadata(
                training_examples=training_examples,
                valid_count=valid_count,
                feature_names=feature_names,
                y=y,
            ))
            
            return True
        
        except Exception as e:
            self.status = self.STATUS_ERROR
            self.metadata["error"] = str(e)
            return False
    
    def predict(self, feature_vector: Dict[str, Any]) -> Dict[str, float]:
        """
        Make a prediction for a feature vector.
        
        Returns:
            Dict with keys "WON", "LOST", "VOID" and probability values,
            or empty dict if model not ready.
        """
        if self.status != self.STATUS_READY or self._model is None or self._scaler is None:
            return {}
        
        try:
            # Build feature vector in correct order
            feature_vector = self._with_competition_feature_defaults(feature_vector or {})
            feature_values = []
            for fname in self.feature_names:
                val = feature_vector.get(fname, 0.0)
                try:
                    feature_values.append(float(val))
                except (ValueError, TypeError):
                    feature_values.append(0.0)
            
            # Normalize and predict
            X = np.array([feature_values])
            X_scaled = self._scaler.transform(X)
            probabilities = self._model.predict_proba(X_scaled)[0]
            classes = getattr(self._model, "classes_", None)
            
            # Return as dict with fallback for missing classes
            result = {}
            for cls, target_idx in self.CLASS_INDICES.items():
                if classes is not None and target_idx in classes:
                    class_pos = int(np.where(classes == target_idx)[0][0])
                    result[cls] = float(probabilities[class_pos])
                else:
                    result[cls] = 0.0
            
            return result
        
        except Exception:
            return {}
    
    def _normalize_feature_names(
        self,
        feature_names: List[str],
        training_examples: List[Dict[str, Any]],
    ) -> List[str]:
        """Return a stable feature list with optional V17 competition fields.

        This does not remove old features and does not require old datasets to
        contain the new fields. Missing values are filled with 0.0.
        """
        normalized: List[str] = []
        seen = set()

        for name in feature_names or []:
            text = str(name or "").strip()
            if not text or text in seen:
                continue
            normalized.append(text)
            seen.add(text)

        available = set()
        for example in training_examples or []:
            features = example.get("feature_vector", {}) if isinstance(example, dict) else {}
            if isinstance(features, dict):
                available.update(str(k) for k in features.keys())

        for name in self.COMPETITION_FEATURE_NAMES:
            if name in seen:
                continue
            # Always include competition_weight because it defaults to 0 and
            # becomes useful as soon as the pipeline starts storing it.
            if name == "competition_weight" or name in available:
                normalized.append(name)
                seen.add(name)

        return normalized

    def _with_competition_feature_defaults(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add safe defaults for optional competition features."""
        result = dict(features or {})

        for name in self.COMPETITION_FEATURE_NAMES:
            result.setdefault(name, 0.0)

        return result

    def _build_training_metadata(
        self,
        training_examples: List[Dict[str, Any]],
        valid_count: int,
        feature_names: List[str],
        y: np.ndarray,
    ) -> Dict[str, Any]:
        """Build lightweight metadata for audit, registry and dashboard."""
        by_competition_tier: Dict[str, int] = {}
        world_cup_examples = 0
        national_team_examples = 0
        major_tournament_examples = 0

        for example in training_examples or []:
            if not isinstance(example, dict):
                continue

            features = example.get("feature_vector", {}) or {}
            metadata = example.get("metadata", {}) or {}

            tier = str(
                metadata.get("competition_tier")
                or features.get("competition_tier")
                or "UNKNOWN"
            ).upper()
            by_competition_tier[tier] = by_competition_tier.get(tier, 0) + 1

            if self._truthy(metadata.get("world_cup_flag") or features.get("world_cup_flag")):
                world_cup_examples += 1

            if self._truthy(metadata.get("national_team_flag") or features.get("national_team_flag")):
                national_team_examples += 1

            if self._truthy(metadata.get("major_tournament_flag") or features.get("major_tournament_flag")):
                major_tournament_examples += 1

        class_distribution: Dict[str, int] = {}
        for label_name, label_idx in self.CLASS_INDICES.items():
            class_distribution[label_name] = int(np.sum(y == label_idx))

        return {
            "training_valid_count": valid_count,
            "feature_count": len(feature_names),
            "competition_feature_names": [
                name for name in self.COMPETITION_FEATURE_NAMES if name in feature_names
            ],
            "by_competition_tier": by_competition_tier,
            "world_cup_examples": world_cup_examples,
            "national_team_examples": national_team_examples,
            "major_tournament_examples": major_tournament_examples,
            "class_distribution": class_distribution,
        }

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return float(value) > 0
        text = str(value or "").strip().upper()
        return text in {"1", "TRUE", "YES", "Y", "SI", "SÍ"}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary (for storage)."""
        return {
            "model_id": self.model_id,
            "market": self.market,
            "version": self.version,
            "trained_on_count": self.trained_on_count,
            "status": self.status,
            "accuracy_on_training": self.accuracy_on_training,
            "feature_names": self.feature_names,
            "metadata": self.metadata,
            "model_state": pickle.dumps(self._model).hex() if self._model else None,
            "scaler_state": pickle.dumps(self._scaler).hex() if self._scaler else None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PredictionModel":
        """Deserialize model from dictionary."""
        model = PredictionModel(
            market=data["market"],
            model_id=data["model_id"],
            version=data["version"],
            metadata=data.get("metadata", {})
        )
        
        model.trained_on_count = data.get("trained_on_count", 0)
        model.status = data.get("status", PredictionModel.STATUS_NOT_READY)
        model.accuracy_on_training = data.get("accuracy_on_training", 0.0)
        model.feature_names = data.get("feature_names", [])
        
        # Restore model and scaler
        if data.get("model_state"):
            try:
                model._model = pickle.loads(bytes.fromhex(data["model_state"]))
            except Exception:
                pass
        
        if data.get("scaler_state"):
            try:
                model._scaler = pickle.loads(bytes.fromhex(data["scaler_state"]))
            except Exception:
                pass
        
        return model
    
    def to_json_serializable(self) -> Dict[str, Any]:
        """Return JSON-serializable representation (without model state)."""
        return {
            "model_id": self.model_id,
            "market": self.market,
            "version": self.version,
            "trained_on_count": self.trained_on_count,
            "status": self.status,
            "accuracy_on_training": self.accuracy_on_training,
            "feature_names": self.feature_names,
            "metadata": self.metadata
        }