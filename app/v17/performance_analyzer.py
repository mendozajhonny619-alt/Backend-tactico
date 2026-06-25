"""
PerformanceAnalyzer: Analyzes model performance in production (out-of-sample).
Phase 3 - Compares live predictions vs actual outcomes.

V17 update:
- Keeps the original production-performance analysis intact.
- Adds competition-aware summaries for World Cup, national teams and major tournaments.
- Adds probability calibration indicators such as Brier score and confidence buckets.
- Adds safer retraining recommendations without changing the public interface.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.v17.ml.prediction_model import PredictionModel


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().upper()
    return text in {"1", "TRUE", "YES", "Y", "SI", "SÍ"}


def normalize_text(value: Any, default: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text if text else default


class PerformanceAnalyzer:
    """
    Analyzes how a model performs on live data.

    Tracks:
    - Accuracy vs actual outcomes.
    - Performance by league and market category.
    - Performance by competition tier and special tournament flags.
    - Brier score and confidence calibration buckets.
    - Degradation detection and retraining recommendations.
    """

    def __init__(self, model: PredictionModel):
        """
        Initialize analyzer.

        Args:
            model: PredictionModel to analyze.
        """
        self.model = model
        self.analysis_date = datetime.utcnow().isoformat() + "Z"
        self.results: Dict[str, Any] = {}

    def analyze_performance(
        self,
        model_feedback: List[Dict[str, Any]],
        analysis_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze model performance on live feedback data.

        Args:
            model_feedback: List of dicts with:
                - "fixture_id": str
                - "market": str (OVER/UNDER)
                - "league": str
                - "predicted_class": str (WON/LOST/VOID)
                - "predicted_probability": float [0, 1]
                - "actual_result": str (WON/LOST/VOID/UNRESOLVED)
                - "timestamp": ISO datetime str
                - optional competition metadata:
                    competition_tier, competition_weight, world_cup_flag,
                    national_team_flag, major_tournament_flag
            analysis_period_days: Days to analyze from most recent.

        Returns:
            Performance analysis dict.
        """
        if not model_feedback:
            return {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "status": "ANALYSIS_NO_DATA",
                "message": "No feedback data available",
            }

        try:
            cutoff = datetime.utcnow() - timedelta(days=analysis_period_days)
            recent_feedback = []

            for fb in model_feedback:
                if self._is_recent_feedback(fb, cutoff):
                    recent_feedback.append(fb)

            if not recent_feedback:
                return {
                    "model_id": self.model.model_id,
                    "market": self.model.market,
                    "status": "ANALYSIS_NO_RECENT_DATA",
                    "analysis_period_days": analysis_period_days,
                }

            correct = 0
            total = 0

            tp = {"WON": 0, "LOST": 0, "VOID": 0}
            fp = {"WON": 0, "LOST": 0, "VOID": 0}
            fn = {"WON": 0, "LOST": 0, "VOID": 0}

            league_stats: Dict[str, Dict[str, Any]] = {}
            market_cat_stats: Dict[str, Dict[str, Any]] = {}
            competition_tier_stats: Dict[str, Dict[str, Any]] = {}
            competition_flag_stats: Dict[str, Dict[str, Any]] = {}
            confidence_buckets: Dict[str, Dict[str, Any]] = {}

            brier_values: List[float] = []
            high_confidence_total = 0
            high_confidence_correct = 0
            elite_total = 0
            elite_correct = 0
            world_cup_total = 0
            world_cup_correct = 0

            for fb in recent_feedback:
                predicted = normalize_text(fb.get("predicted_class"), "UNKNOWN")
                actual = normalize_text(fb.get("actual_result"), "UNKNOWN")
                league = normalize_text(fb.get("league"), "UNKNOWN")
                market_cat = normalize_text(fb.get("market_category"), "GENERAL")
                competition_tier = normalize_text(fb.get("competition_tier"), "UNKNOWN")
                predicted_probability = safe_float(fb.get("predicted_probability"), 0.0)

                if actual in {"UNRESOLVED", "UNKNOWN", "PENDING", "NONE"}:
                    continue

                total += 1
                is_correct = predicted == actual

                if is_correct:
                    correct += 1
                    if actual in tp:
                        tp[actual] += 1
                else:
                    if predicted in fp:
                        fp[predicted] += 1
                    if actual in fn:
                        fn[actual] += 1

                if predicted_probability >= 0.75:
                    high_confidence_total += 1
                    if is_correct:
                        high_confidence_correct += 1

                if competition_tier in {
                    "WORLD_CUP_ELITE",
                    "NATIONAL_TEAM_ELITE",
                    "INTERNATIONAL_CLUB_ELITE",
                    "MAJOR_TOURNAMENT",
                }:
                    elite_total += 1
                    if is_correct:
                        elite_correct += 1

                if safe_bool(fb.get("world_cup_flag")) or competition_tier == "WORLD_CUP_ELITE":
                    world_cup_total += 1
                    if is_correct:
                        world_cup_correct += 1

                self._add_group_result(league_stats, league, is_correct)
                self._add_group_result(market_cat_stats, market_cat, is_correct)
                self._add_group_result(competition_tier_stats, competition_tier, is_correct)

                for flag_name in [
                    "world_cup_flag",
                    "national_team_flag",
                    "major_tournament_flag",
                ]:
                    if safe_bool(fb.get(flag_name)):
                        self._add_group_result(
                            competition_flag_stats,
                            flag_name.upper(),
                            is_correct,
                        )

                bucket = self._confidence_bucket(predicted_probability)
                self._add_group_result(confidence_buckets, bucket, is_correct)

                brier = self._brier_component(
                    predicted=predicted,
                    actual=actual,
                    predicted_probability=predicted_probability,
                )
                if brier is not None:
                    brier_values.append(brier)

            self._finalize_group_stats(league_stats)
            self._finalize_group_stats(market_cat_stats)
            self._finalize_group_stats(competition_tier_stats)
            self._finalize_group_stats(competition_flag_stats)
            self._finalize_group_stats(confidence_buckets)

            overall_accuracy = float(correct / total) if total > 0 else 0.0
            high_confidence_accuracy = (
                float(high_confidence_correct / high_confidence_total)
                if high_confidence_total > 0
                else 0.0
            )
            elite_accuracy = float(elite_correct / elite_total) if elite_total > 0 else 0.0
            world_cup_accuracy = (
                float(world_cup_correct / world_cup_total)
                if world_cup_total > 0
                else 0.0
            )
            brier_score = (
                float(sum(brier_values) / len(brier_values))
                if brier_values
                else None
            )

            degradation_alert = self._detect_degradation(
                total=total,
                overall_accuracy=overall_accuracy,
                high_confidence_total=high_confidence_total,
                high_confidence_accuracy=high_confidence_accuracy,
                brier_score=brier_score,
            )

            recommendation = self._recommendation(
                total=total,
                overall_accuracy=overall_accuracy,
                high_confidence_total=high_confidence_total,
                high_confidence_accuracy=high_confidence_accuracy,
                elite_total=elite_total,
                elite_accuracy=elite_accuracy,
                brier_score=brier_score,
                degradation_alert=degradation_alert,
            )

            if degradation_alert:
                next_retraining = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
            else:
                next_retraining = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

            self.results = {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "analysis_date": self.analysis_date,
                "status": "ANALYSIS_COMPLETE",
                "analysis_period_days": analysis_period_days,
                "live_predictions_count": total,
                "accuracy_vs_actual": overall_accuracy,
                "high_confidence_predictions_count": high_confidence_total,
                "high_confidence_accuracy": high_confidence_accuracy,
                "elite_competition_predictions_count": elite_total,
                "elite_competition_accuracy": elite_accuracy,
                "world_cup_predictions_count": world_cup_total,
                "world_cup_accuracy": world_cup_accuracy,
                "brier_score": brier_score,
                "performance_by_league": league_stats,
                "performance_by_market_category": market_cat_stats,
                "performance_by_competition_tier": competition_tier_stats,
                "performance_by_competition_flag": competition_flag_stats,
                "performance_by_confidence_bucket": confidence_buckets,
                "classification_counts": {
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                },
                "degradation_alert": degradation_alert,
                "recommendation": recommendation,
                "next_retraining_suggested": next_retraining,
            }

            return self.results

        except Exception as e:
            return {
                "model_id": self.model.model_id,
                "market": self.model.market,
                "status": "ANALYSIS_ERROR",
                "error": str(e),
            }

    def get_results(self) -> Dict[str, Any]:
        """Get latest analysis results."""
        return self.results

    def to_json_serializable(self) -> Dict[str, Any]:
        """Get JSON-serializable analysis results."""
        return self.results

    def _is_recent_feedback(self, feedback: Dict[str, Any], cutoff: datetime) -> bool:
        try:
            ts_str = str(feedback.get("timestamp") or "").strip()
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1]
            ts = datetime.fromisoformat(ts_str)
            return ts >= cutoff
        except Exception:
            return True

    def _add_group_result(
        self,
        store: Dict[str, Dict[str, Any]],
        key: str,
        is_correct: bool,
    ) -> None:
        key = normalize_text(key)
        if key not in store:
            store[key] = {"total": 0, "correct": 0, "accuracy": 0.0}
        store[key]["total"] += 1
        if is_correct:
            store[key]["correct"] += 1

    def _finalize_group_stats(self, store: Dict[str, Dict[str, Any]]) -> None:
        for data in store.values():
            total = int(data.get("total") or 0)
            correct = int(data.get("correct") or 0)
            data["accuracy"] = float(correct / total) if total > 0 else 0.0

    def _confidence_bucket(self, probability: float) -> str:
        if probability >= 0.90:
            return "P90_100"
        if probability >= 0.80:
            return "P80_89"
        if probability >= 0.70:
            return "P70_79"
        if probability >= 0.60:
            return "P60_69"
        if probability >= 0.50:
            return "P50_59"
        return "P00_49"

    def _brier_component(
        self,
        predicted: str,
        actual: str,
        predicted_probability: float,
    ) -> Optional[float]:
        if predicted not in {"WON", "LOST"}:
            return None
        if actual not in {"WON", "LOST"}:
            return None

        probability = max(0.0, min(1.0, predicted_probability))
        observed = 1.0 if predicted == actual else 0.0
        return (probability - observed) ** 2

    def _detect_degradation(
        self,
        total: int,
        overall_accuracy: float,
        high_confidence_total: int,
        high_confidence_accuracy: float,
        brier_score: Optional[float],
    ) -> bool:
        if total >= 20 and overall_accuracy < 0.55:
            return True
        if high_confidence_total >= 10 and high_confidence_accuracy < 0.60:
            return True
        if brier_score is not None and total >= 20 and brier_score > 0.32:
            return True
        return False

    def _recommendation(
        self,
        total: int,
        overall_accuracy: float,
        high_confidence_total: int,
        high_confidence_accuracy: float,
        elite_total: int,
        elite_accuracy: float,
        brier_score: Optional[float],
        degradation_alert: bool,
    ) -> str:
        if total < 20:
            return "Too few live predictions. Continue collecting data."

        if degradation_alert:
            return "Model accuracy or calibration is degrading. Retraining recommended soon."

        if overall_accuracy < 0.60:
            return "Model performance borderline. Monitor closely and avoid increasing exposure."

        if high_confidence_total >= 10 and high_confidence_accuracy < overall_accuracy:
            return "High-confidence predictions are underperforming. Review calibration before trusting premium signals."

        if elite_total >= 10 and elite_accuracy < 0.60:
            return "Elite competition performance is weak. Review World Cup / major tournament features."

        if brier_score is not None and brier_score > 0.25:
            return "Accuracy is acceptable but probability calibration needs monitoring."

        return "Model performance acceptable. Continue monitoring."