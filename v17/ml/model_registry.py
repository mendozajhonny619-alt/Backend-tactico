"""
ModelRegistry: Manages model lifecycle, versioning, and activation.
Phase 3 - Stores and retrieves trained models from disk.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.v17.ml.prediction_model import PredictionModel


MIN_MODEL_ACCURACY_TO_ACTIVATE = 0.55
MIN_MODEL_EXAMPLES_TO_ACTIVATE = 300


class ModelRegistry:
    """
    Manages trained models for different markets.
    
    Stores:
    - Directory: app/v17/storage/models/
    - Structure:
      models/
      ├── registry.json
      ├── OVER/
      │   └── model_*.pkl.json
      └── UNDER/
          └── model_*.pkl.json
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize registry.
        
        Args:
            storage_dir: Path to app/v17/storage/ directory
        """
        self.storage_dir = Path(storage_dir)
        self.models_dir = self.storage_dir / "models"
        self.registry_file = self.models_dir / "registry.json"
        
        # Create directories if needed
        self.models_dir.mkdir(parents=True, exist_ok=True)
        for market in ["OVER", "UNDER"]:
            (self.models_dir / market).mkdir(exist_ok=True)
        
        # Load or initialize registry
        self._registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from disk or create empty."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Initialize empty registry
        return {
            "OVER": {"active_model_id": None, "models": []},
            "UNDER": {"active_model_id": None, "models": []}
        }
    
    def _save_registry(self):
        """Save registry to disk."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self._registry, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save registry: {e}")
    
    def register_model(self, market: str, model: PredictionModel) -> str:
        """
        Register a trained model.
        
        Args:
            market: "OVER" or "UNDER"
            model: PredictionModel instance
        
        Returns:
            model_id
        """
        if market not in ["OVER", "UNDER"]:
            raise ValueError(f"Invalid market: {market}")
        
        # Save model to disk
        model_file = self.models_dir / market / f"model_{model.model_id}.json"
        try:
            with open(model_file, 'w') as f:
                json.dump(model.to_dict(), f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save model: {e}")
        
        # Register in registry
        model_metadata = {
            "model_id": model.model_id,
            "version": model.version,
            "trained_on_count": model.trained_on_count,
            "status": model.status,
            "accuracy_on_training": model.accuracy_on_training,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            # V17 competitive metadata. These fields are optional and keep
            # compatibility with older models that do not include them.
            "competition_tier": model.metadata.get("competition_tier"),
            "competition_weight": model.metadata.get("competition_weight"),
            "world_cup_flag": model.metadata.get("world_cup_flag", False),
            "national_team_flag": model.metadata.get("national_team_flag", False),
            "major_tournament_flag": model.metadata.get("major_tournament_flag", False),
            "feature_count": len(model.feature_names or []),
            "model_quality": self._model_quality(model),
            "activation_allowed": self._can_activate_model(model),
        }
        
        # Check if already exists
        existing = [m for m in self._registry[market]["models"] 
                   if m["model_id"] == model.model_id]
        if existing:
            existing[0].update(model_metadata)
        else:
            self._registry[market]["models"].append(model_metadata)
        
        self._save_registry()
        return model.model_id
    
    def set_active_model(self, market: str, model_id: str) -> bool:
        """
        Set a model as active for a market.

        V17 safety improvement:
        - The model must exist.
        - The model must load correctly from disk.
        - The model must be MODEL_READY.
        - The model must have enough examples.
        - The model must pass a minimum training-accuracy sanity check.

        This does not affect old callers: it still returns True/False.
        """
        if market not in ["OVER", "UNDER"]:
            raise ValueError(f"Invalid market: {market}")

        models = self._registry[market]["models"]
        metadata = next((m for m in models if m.get("model_id") == model_id), None)
        if not metadata:
            return False

        model = self.load_model(market, model_id)
        if not model:
            metadata["activation_allowed"] = False
            metadata["activation_block_reason"] = "MODEL_FILE_NOT_FOUND_OR_INVALID"
            self._save_registry()
            return False

        if not self._can_activate_model(model):
            metadata["activation_allowed"] = False
            metadata["activation_block_reason"] = self._activation_block_reason(model)
            metadata["model_quality"] = self._model_quality(model)
            self._save_registry()
            return False

        metadata["activation_allowed"] = True
        metadata["activation_block_reason"] = None
        metadata["activated_at"] = datetime.utcnow().isoformat() + "Z"
        metadata["model_quality"] = self._model_quality(model)

        self._registry[market]["active_model_id"] = model_id
        self._save_registry()
        return True
    
    def get_active_model(self, market: str) -> Optional[PredictionModel]:
        """
        Get the active model for a market.
        
        Args:
            market: "OVER" or "UNDER"
        
        Returns:
            PredictionModel or None if not found/ready
        """
        if market not in ["OVER", "UNDER"]:
            return None
        
        model_id = self._registry[market].get("active_model_id")
        if not model_id:
            return None
        
        return self.load_model(market, model_id)
    
    def load_model(self, market: str, model_id: str) -> Optional[PredictionModel]:
        """
        Load a model from disk.
        
        Args:
            market: "OVER" or "UNDER"
            model_id: Model ID
        
        Returns:
            PredictionModel or None if not found
        """
        if market not in ["OVER", "UNDER"]:
            return None
        
        model_file = self.models_dir / market / f"model_{model_id}.json"
        if not model_file.exists():
            return None
        
        try:
            with open(model_file, 'r') as f:
                data = json.load(f)
            return PredictionModel.from_dict(data)
        except Exception as e:
            print(f"Error loading model {model_id}: {e}")
            return None
    
    def list_models(self, market: str) -> List[Dict[str, Any]]:
        """
        List all registered models for a market.
        
        Args:
            market: "OVER" or "UNDER"
        
        Returns:
            List of model metadata dicts
        """
        if market not in ["OVER", "UNDER"]:
            return []
        
        return self._registry[market].get("models", [])
    
    def get_active_model_metadata(self, market: str) -> Optional[Dict[str, Any]]:
        """Get metadata of currently active model."""
        if market not in ["OVER", "UNDER"]:
            return None
        
        model_id = self._registry[market].get("active_model_id")
        if not model_id:
            return None
        
        models = self._registry[market]["models"]
        for m in models:
            if m["model_id"] == model_id:
                return m
        
        return None
    

    def get_models_by_competition_tier(self, market: str) -> Dict[str, Any]:
        """Group registered models by competition tier for audit/debug panels."""
        if market not in ["OVER", "UNDER"]:
            return {}

        grouped: Dict[str, Any] = {}
        for model in self._registry[market].get("models", []):
            tier = str(model.get("competition_tier") or "UNKNOWN")
            item = grouped.setdefault(tier, {"count": 0, "active": 0, "models": []})
            item["count"] += 1
            if model.get("model_id") == self._registry[market].get("active_model_id"):
                item["active"] += 1
            item["models"].append(model)

        return grouped

    def _can_activate_model(self, model: PredictionModel) -> bool:
        """Return True only when the model is safe enough to be active."""
        return (
            model.status == PredictionModel.STATUS_READY
            and int(model.trained_on_count or 0) >= MIN_MODEL_EXAMPLES_TO_ACTIVATE
            and float(model.accuracy_on_training or 0.0) >= MIN_MODEL_ACCURACY_TO_ACTIVATE
        )

    def _activation_block_reason(self, model: PredictionModel) -> str:
        if model.status != PredictionModel.STATUS_READY:
            return "MODEL_NOT_READY"
        if int(model.trained_on_count or 0) < MIN_MODEL_EXAMPLES_TO_ACTIVATE:
            return "NOT_ENOUGH_TRAINING_EXAMPLES"
        if float(model.accuracy_on_training or 0.0) < MIN_MODEL_ACCURACY_TO_ACTIVATE:
            return "ACCURACY_BELOW_MINIMUM"
        return "UNKNOWN"

    def _model_quality(self, model: PredictionModel) -> str:
        if model.status != PredictionModel.STATUS_READY:
            return "NOT_READY"

        accuracy = float(model.accuracy_on_training or 0.0)
        trained_on = int(model.trained_on_count or 0)

        if trained_on >= 1500 and accuracy >= 0.70:
            return "STRONG"
        if trained_on >= 700 and accuracy >= 0.62:
            return "GOOD"
        if trained_on >= MIN_MODEL_EXAMPLES_TO_ACTIVATE and accuracy >= MIN_MODEL_ACCURACY_TO_ACTIVATE:
            return "ACCEPTABLE"
        return "WEAK"

    def get_registry_snapshot(self) -> Dict[str, Any]:
        """Get current registry state (for debugging/API)."""
        return {
            "OVER": {
                "active_model_id": self._registry["OVER"].get("active_model_id"),
                "model_count": len(self._registry["OVER"]["models"]),
                "models": self._registry["OVER"]["models"],
                "by_competition_tier": self.get_models_by_competition_tier("OVER"),
                "activation_policy": {
                    "min_accuracy": MIN_MODEL_ACCURACY_TO_ACTIVATE,
                    "min_training_examples": MIN_MODEL_EXAMPLES_TO_ACTIVATE,
                },
            },
            "UNDER": {
                "active_model_id": self._registry["UNDER"].get("active_model_id"),
                "model_count": len(self._registry["UNDER"]["models"]),
                "models": self._registry["UNDER"]["models"],
                "by_competition_tier": self.get_models_by_competition_tier("UNDER"),
                "activation_policy": {
                    "min_accuracy": MIN_MODEL_ACCURACY_TO_ACTIVATE,
                    "min_training_examples": MIN_MODEL_EXAMPLES_TO_ACTIVATE,
                },
            }
        }