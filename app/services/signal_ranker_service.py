from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


class SignalRankerService:
    """
    Ordena, reclasifica y prioriza señales finales.
    """

    RANK_PRIORITY = {
        "PREMIUM": 6,
        "FUERTE": 5,
        "BUENA": 4,
        "OPERABLE": 3,
        "OBSERVACION": 2,
        "NO_BET": 0,
    }

    HARD_PUBLISH_RANKS = {"PREMIUM", "FUERTE"}
    MEDIUM_PUBLISH_RANKS = {"BUENA"}
    SOFT_PUBLISH_RANKS = {"OPERABLE"}

    MAX_PUBLISHED = 6
    MAX_MEDIUM_PUBLISHED = 3
    MAX_SOFT_PUBLISHED = 2

    def rank(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        normalized = self._extract_and_normalize(candidates)
        reclassified = [self._reclassify_signal(signal) for signal in normalized]
        deduped = self._deduplicate(reclassified)
        sorted_candidates = self._sort_candidates(deduped)

        premium_strong = [
            signal for signal in sorted_candidates
            if signal.get("rank") in self.HARD_PUBLISH_RANKS
        ]

        medium = [
            signal for signal in sorted_candidates
            if signal.get("rank") in self.MEDIUM_PUBLISH_RANKS
        ]

        soft = [
            signal for signal in sorted_candidates
            if signal.get("rank") in self.SOFT_PUBLISH_RANKS
        ]

        published: List[Dict[str, Any]] = []

        published.extend(premium_strong[: self.MAX_PUBLISHED])

        remaining_slots = self.MAX_PUBLISHED - len(published)
        if remaining_slots > 0:
            published.extend(medium[: min(self.MAX_MEDIUM_PUBLISHED, remaining_slots)])

        remaining_slots = self.MAX_PUBLISHED - len(published)
        if remaining_slots > 0:
            published.extend(soft[: min(self.MAX_SOFT_PUBLISHED, remaining_slots)])

        return self._sort_candidates(published)[: self.MAX_PUBLISHED]

    def _extract_and_normalize(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for item in candidates:
            if not isinstance(item, dict):
                continue

            signal = item.get("signal") if "signal" in item else item
            if not isinstance(signal, dict):
                continue

            match_id = signal.get("match_id")
            market = signal.get("market")

            if match_id is None or not market:
                continue

            signal = deepcopy(signal)
            signal["signal_key"] = signal.get("signal_key") or self._build_signal_key(match_id, market)

            signal["rank"] = str(signal.get("rank") or "NO_BET").upper()
            signal["market"] = str(signal.get("market") or "").upper()

            signal["signal_score"] = self._safe_float(signal.get("signal_score"))
            signal["ai_score"] = self._safe_float(signal.get("ai_score"))
            signal["goal_probability"] = self._safe_float(signal.get("goal_probability"))
            signal["over_probability"] = self._safe_float(signal.get("over_probability"))
            signal["under_probability"] = self._safe_float(signal.get("under_probability"))
            signal["risk_score"] = self._safe_float(signal.get("risk_score"))
            signal["value_edge"] = self._safe_float(signal.get("value_edge"))
            signal["odds"] = self._safe_float(signal.get("odds"))
            signal["minute"] = self._safe_int(signal.get("minute"))

            signal["risk_level"] = str(signal.get("risk_level") or "").upper()
            signal["context_state"] = str(
                signal.get("context_state")
                or signal.get("match_state")
                or ""
            ).upper()
            signal["data_quality"] = str(signal.get("data_quality") or "").upper()
            signal["game_quality"] = str(signal.get("game_quality") or "").upper()

            normalized.append(signal)

        return normalized

    def _reclassify_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = deepcopy(signal)

        market = str(signal.get("market") or "").upper()
        ai_score = self._safe_float(signal.get("ai_score"))
        signal_score = self._safe_float(signal.get("signal_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))
        risk_level = str(signal.get("risk_level") or "").upper()
        context_state = str(signal.get("context_state") or "").upper()
        data_quality = str(signal.get("data_quality") or "").upper()
        game_quality = str(signal.get("game_quality") or "").upper()
        minute = self._safe_int(signal.get("minute"))

        is_over = self._is_over_market(market)
        market_probability = over_probability if is_over else under_probability

        if risk_level == "ALTO" and risk_score >= 7.8:
            signal["rank"] = "OBSERVACION"
            signal["rank_reason"] = "RISK_TOO_HIGH_FOR_SIGNAL"
            return signal

        if ai_score < 50 or signal_score < 50:
            signal["rank"] = "OBSERVACION"
            signal["rank_reason"] = "LOW_INTERNAL_SCORE"
            return signal

        playable_context = context_state in {
            "TIBIO",
            "CALIENTE",
            "MUY_CALIENTE",
            "CONTROLADO",
        }

        strong_context = context_state in {
            "CALIENTE",
            "MUY_CALIENTE",
            "TIBIO",
        }

        good_quality = data_quality in {"MEDIUM", "HIGH"} or game_quality in {"MEDIUM", "HIGH"}

        if (
            ai_score >= 76
            and signal_score >= 76
            and goal_probability >= 82
            and market_probability >= 82
            and risk_score <= 7.0
            and strong_context
        ):
            signal["rank"] = "PREMIUM"
            signal["rank_reason"] = "ELITE_SIGNAL_ALIGNMENT"
            return signal

        if (
            ai_score >= 68
            and signal_score >= 68
            and goal_probability >= 76
            and market_probability >= 76
            and risk_score <= 7.2
            and playable_context
        ):
            signal["rank"] = "FUERTE"
            signal["rank_reason"] = "STRONG_SIGNAL_ALIGNMENT"
            return signal

        if (
            ai_score >= 62
            and signal_score >= 62
            and goal_probability >= 68
            and market_probability >= 66
            and risk_score <= 7.4
            and playable_context
        ):
            signal["rank"] = "BUENA"
            signal["rank_reason"] = "GOOD_SIGNAL_ALIGNMENT"
            return signal

        if (
            ai_score >= 56
            and signal_score >= 56
            and goal_probability >= 60
            and market_probability >= 58
            and 15 <= minute <= 88
        ):
            signal["rank"] = "OPERABLE"
            signal["rank_reason"] = "OPERABLE_BUT_NOT_STRONG"
            return signal

        signal["rank"] = "OBSERVACION"
        signal["rank_reason"] = "NOT_ENOUGH_FOR_ACTIVE_SIGNAL"
        return signal

    def _deduplicate(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best_by_key: Dict[str, Dict[str, Any]] = {}

        for signal in candidates:
            key = signal["signal_key"]
            current_best = best_by_key.get(key)

            if current_best is None:
                best_by_key[key] = signal
                continue

            if self._is_better(signal, current_best):
                best_by_key[key] = signal

        return list(best_by_key.values())

    def _sort_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda x: (
                self.RANK_PRIORITY.get(x.get("rank", "NO_BET"), 0),
                self._final_power_score(x),
                x.get("signal_score", 0.0),
                x.get("ai_score", 0.0),
                x.get("goal_probability", 0.0),
                -x.get("risk_score", 999.0),
            ),
            reverse=True,
        )

    def _is_better(self, candidate: Dict[str, Any], current: Dict[str, Any]) -> bool:
        candidate_rank = self.RANK_PRIORITY.get(candidate.get("rank", "NO_BET"), 0)
        current_rank = self.RANK_PRIORITY.get(current.get("rank", "NO_BET"), 0)

        if candidate_rank != current_rank:
            return candidate_rank > current_rank

        return self._final_power_score(candidate) > self._final_power_score(current)

    def _final_power_score(self, signal: Dict[str, Any]) -> float:
        market = str(signal.get("market") or "").upper()

        ai_score = self._safe_float(signal.get("ai_score"))
        signal_score = self._safe_float(signal.get("signal_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))
        value_edge = self._safe_float(signal.get("value_edge"))

        is_over = self._is_over_market(market)
        market_probability = over_probability if is_over else under_probability

        score = (
            signal_score * 0.35
            + ai_score * 0.25
            + goal_probability * 0.18
            + market_probability * 0.17
            + min(value_edge * 100, 15) * 0.05
            - risk_score * 2.0
        )

        return round(max(0.0, min(score, 100.0)), 2)

    def _is_over_market(self, market: str) -> bool:
        text = str(market or "").upper()
        return (
            "OVER" in text
            or "ENCIMA" in text
            or "MAS" in text
            or "MÁS" in text
        )

    def _build_signal_key(self, match_id: Any, market: str) -> str:
        return f"{str(match_id).strip()}:{str(market).strip().upper()}"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
