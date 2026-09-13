from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


class MarketEngine:
    """
    Valida y normaliza mercado operable para el sistema.

    Filosofía:
    - Si existe mercado real, validarlo.
    - Si no existe mercado real, permitir mercado interno provisional.
    - No inventa cuotas falsas.
    - Reconoce contexto live: reactivación, caos, retención, presión falsa y tramo final.
    """

    MIN_ODDS = 1.50
    MAX_ODDS = 2.10

    LATE_MIN_ODDS = 1.35
    LATE_MAX_ODDS = 2.60

    def evaluate(
        self,
        match: Dict[str, Any],
        market_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        match = match or {}
        normalized_market_type = self._normalize_market_type(market_type)

        if normalized_market_type not in {"OVER", "UNDER"}:
            return self._reject("MARKET_TYPE_UNKNOWN")

        market_profile = self._market_live_profile(match, normalized_market_type)

        raw_candidates = self._extract_market_candidates(match, normalized_market_type)

        if not raw_candidates:
            pending = self._build_pending_market(normalized_market_type)
            pending.update(market_profile)
            return pending

        operable_candidates = []
        rejected_reasons = []

        for candidate in raw_candidates:
            validated = self._validate_candidate(
                candidate=candidate,
                requested_market_type=normalized_market_type,
                market_profile=market_profile,
            )
            if validated["is_valid"]:
                operable_candidates.append(validated)
            else:
                rejected_reasons.append(validated.get("reason"))

        if not operable_candidates:
            if self._can_fallback_to_pending(rejected_reasons):
                pending = self._build_pending_market(normalized_market_type)
                pending.update(market_profile)
                pending["reason"] = "MARKET_PENDING_INTERNAL_AFTER_INVALID_STRUCTURE"
                return pending

            rejected = self._reject(self._pick_best_reject_reason(rejected_reasons))
            rejected.update(market_profile)
            return rejected

        best = self._pick_best_candidate(operable_candidates, market_profile)
        best["market_status"] = "VALID"
        best["reason"] = None
        best.update(market_profile)
        return best

    # ---------------------------------------------------
    # Mini análisis live del mercado
    # ---------------------------------------------------

    def _market_live_profile(
        self,
        match: Dict[str, Any],
        market_type: str,
    ) -> Dict[str, Any]:
        minute = self._safe_int(
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or match.get("minuto")
        )

        pressure = self._safe_float(match.get("pressure_index"))
        rhythm = self._safe_float(match.get("rhythm_index"))
        goal_window = self._safe_float(match.get("goal_window_score"))
        over_window = self._safe_float(match.get("over_window_score"))

        context_state = str(match.get("context_state") or "").upper()
        data_quality = str(match.get("data_quality") or "").upper()

        late_reactivation = bool(match.get("late_reactivation", False))
        chaos_mode = bool(match.get("chaos_mode", False))
        red_alert = bool(match.get("red_alert", False))
        fake_pressure_detected = bool(match.get("fake_pressure_detected", False))
        pressure_without_depth = bool(match.get("pressure_without_depth", False))
        retention_shape = bool(match.get("retention_shape", False))
        cooling_detected = bool(match.get("cooling_detected", False))
        under_transition_score = self._safe_float(match.get("under_transition_score"))
        live_decay_factor = self._safe_float(match.get("live_decay_factor") or 1.0)

        score_hold_probability = self._safe_float(match.get("score_hold_probability"))
        retention_risk = self._safe_float(match.get("retention_risk"))

        field_vision_status = str(match.get("field_vision_status") or "").upper()
        is_added_time = bool(
            match.get("is_added_time")
            or match.get("field_vision_is_added_time")
            or minute >= 90
        )

        late_pressure = self._has_late_pressure(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        warnings: List[str] = []
        positives: List[str] = []

        if late_pressure:
            positives.append("MARKET_LATE_REACTIVATION_SUPPORTED")

        if chaos_mode or red_alert:
            positives.append("MARKET_CHAOS_OR_RED_ALERT")

        if fake_pressure_detected:
            warnings.append("MARKET_FAKE_PRESSURE")

        if pressure_without_depth:
            warnings.append("MARKET_PRESSURE_WITHOUT_DEPTH")

        if retention_shape or score_hold_probability >= 70 or retention_risk >= 70:
            warnings.append("MARKET_RETENTION_RISK")

        if cooling_detected or live_decay_factor <= 0.70:
            warnings.append("MARKET_LIVE_COOLING")

        if under_transition_score >= 70:
            warnings.append("MARKET_UNDER_TRANSITION_ACTIVE")

        if market_type == "OVER":
            if late_pressure:
                live_bias = "OVER_LATE_REACTIVATION"
                recommendation = "ALLOW_OVER_IF_VALUE_OR_INTERNAL"
            elif fake_pressure_detected or pressure_without_depth or retention_shape:
                live_bias = "AGAINST_OVER"
                recommendation = "PREFER_OBSERVE_OR_UNDER"
            elif cooling_detected or under_transition_score >= 70:
                live_bias = "AGAINST_OVER"
                recommendation = "NO_OVER_WITHOUT_REACTIVATION"
            else:
                live_bias = "OVER_STANDARD"
                recommendation = "ALLOW_STANDARD_VALIDATION"

        else:
            if retention_shape or score_hold_probability >= 70 or under_transition_score >= 70:
                live_bias = "UNDER_SUPPORTED"
                recommendation = "ALLOW_UNDER_IF_VALUE_OR_INTERNAL"
            elif late_pressure and context_state in {"CALIENTE", "MUY_CALIENTE"}:
                live_bias = "AGAINST_UNDER"
                recommendation = "UNDER_NEEDS_CAUTION"
            else:
                live_bias = "UNDER_STANDARD"
                recommendation = "ALLOW_STANDARD_VALIDATION"

        status = "CLEAR"
        if warnings:
            status = "CAUTION"
        if market_type == "OVER" and any(w in warnings for w in {
            "MARKET_FAKE_PRESSURE",
            "MARKET_PRESSURE_WITHOUT_DEPTH",
            "MARKET_RETENTION_RISK",
        }):
            status = "WARNING"

        if data_quality == "LOW" and not late_pressure:
            status = "CAUTION"
            warnings.append("MARKET_LOW_DATA")

        return {
            "market_live_status": status,
            "market_live_bias": live_bias,
            "market_recommendation": recommendation,
            "market_warnings": warnings,
            "market_positive_factors": positives,
            "market_late_pressure": late_pressure,
            "market_minute": minute,
        }

    def _has_late_pressure(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
        late_reactivation: bool,
        chaos_mode: bool,
        red_alert: bool,
        field_vision_status: str,
        is_added_time: bool,
    ) -> bool:
        if minute < 76:
            return False

        if late_reactivation or chaos_mode or red_alert:
            return True

        if field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
            return True

        if (
            pressure >= 28
            and rhythm >= 15
            and (goal_window >= 22 or over_window >= 22)
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if is_added_time and pressure >= 30 and rhythm >= 16:
            return True

        return False

    # ---------------------------------------------------
    # Extracción
    # ---------------------------------------------------

    def _extract_market_candidates(
        self,
        match: Dict[str, Any],
        market_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        markets = match.get("markets")
        if isinstance(markets, list):
            for item in markets:
                parsed = self._parse_market_item(item, market_type)
                if parsed:
                    candidates.extend(parsed)

        odds = match.get("odds")
        if isinstance(odds, dict):
            parsed = self._parse_odds_dict(odds, market_type)
            if parsed:
                candidates.extend(parsed)

        bookmakers = match.get("bookmakers")
        if isinstance(bookmakers, list):
            for bookmaker in bookmakers:
                parsed = self._parse_bookmaker(bookmaker, market_type)
                if parsed:
                    candidates.extend(parsed)

        parsed_flat = self._parse_flat_market(match, market_type)
        if parsed_flat:
            candidates.extend(parsed_flat)

        return candidates

    def _parse_market_item(
        self,
        item: Dict[str, Any],
        market_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not isinstance(item, dict):
            return []

        label = str(
            item.get("market")
            or item.get("type")
            or item.get("name")
            or item.get("key")
            or ""
        ).upper()

        if not self._looks_like_total_market(label, item):
            return []

        line = item.get("line") or item.get("total") or item.get("handicap")

        outcomes = item.get("outcomes")
        if isinstance(outcomes, list):
            results = []
            for outcome in outcomes:
                parsed = self._build_candidate_from_outcome(
                    outcome=outcome,
                    fallback_line=line,
                    fallback_bookmaker=item.get("bookmaker"),
                    parent_label=label,
                )
                if parsed and self._market_type_matches(parsed["market_type"], market_type):
                    results.append(parsed)
            return results

        results = []
        for key, inferred_type in (("over", "OVER"), ("under", "UNDER")):
            side = item.get(key)
            if isinstance(side, dict):
                candidate = {
                    "market_type": inferred_type,
                    "line": self._normalize_line(side.get("line") or line or item.get("line")),
                    "odds": self._safe_float(side.get("odds") or side.get("price")),
                    "bookmaker": side.get("bookmaker") or item.get("bookmaker"),
                    "raw_market": deepcopy(item),
                }
                if self._market_type_matches(candidate["market_type"], market_type):
                    results.append(candidate)

        return results

    def _parse_odds_dict(
        self,
        odds: Dict[str, Any],
        market_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        results = []

        for key, inferred_type in (("over", "OVER"), ("under", "UNDER")):
            side = odds.get(key)
            if isinstance(side, dict):
                candidate = {
                    "market_type": inferred_type,
                    "line": self._normalize_line(side.get("line") or side.get("total")),
                    "odds": self._safe_float(side.get("odds") or side.get("price")),
                    "bookmaker": side.get("bookmaker"),
                    "raw_market": deepcopy(side),
                }
                if self._market_type_matches(candidate["market_type"], market_type):
                    results.append(candidate)

        flat_mappings = [
            ("OVER", odds.get("over_odds"), odds.get("over_line")),
            ("UNDER", odds.get("under_odds"), odds.get("under_line")),
        ]

        for inferred_type, raw_odds, raw_line in flat_mappings:
            candidate = {
                "market_type": inferred_type,
                "line": self._normalize_line(raw_line),
                "odds": self._safe_float(raw_odds),
                "bookmaker": odds.get("bookmaker"),
                "raw_market": deepcopy(odds),
            }
            if candidate["odds"] and self._market_type_matches(inferred_type, market_type):
                results.append(candidate)

        return results

    def _parse_bookmaker(
        self,
        bookmaker: Dict[str, Any],
        market_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not isinstance(bookmaker, dict):
            return []

        bookmaker_name = bookmaker.get("title") or bookmaker.get("name")
        markets = bookmaker.get("markets")
        if not isinstance(markets, list):
            return []

        results = []
        for market in markets:
            if not isinstance(market, dict):
                continue

            market_label = str(
                market.get("key") or market.get("name") or market.get("market") or ""
            ).upper()

            if not self._looks_like_total_market(market_label, market):
                continue

            outcomes = market.get("outcomes")
            if not isinstance(outcomes, list):
                continue

            fallback_line = market.get("line") or market.get("total")
            parent_label = market_label

            for outcome in outcomes:
                parsed = self._build_candidate_from_outcome(
                    outcome=outcome,
                    fallback_line=fallback_line,
                    fallback_bookmaker=bookmaker_name,
                    parent_label=parent_label,
                )
                if parsed and self._market_type_matches(parsed["market_type"], market_type):
                    results.append(parsed)

        return results

    def _parse_flat_market(
        self,
        match: Dict[str, Any],
        market_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        results = []

        direct_candidates = [
            {
                "market_type": "OVER",
                "line": self._normalize_line(match.get("over_line") or match.get("line")),
                "odds": self._safe_float(match.get("over_odds")),
                "bookmaker": match.get("bookmaker"),
                "raw_market": deepcopy(match),
            },
            {
                "market_type": "UNDER",
                "line": self._normalize_line(match.get("under_line") or match.get("line")),
                "odds": self._safe_float(match.get("under_odds")),
                "bookmaker": match.get("bookmaker"),
                "raw_market": deepcopy(match),
            },
        ]

        for candidate in direct_candidates:
            if candidate["odds"] and self._market_type_matches(candidate["market_type"], market_type):
                results.append(candidate)

        return results

    def _build_candidate_from_outcome(
        self,
        outcome: Dict[str, Any],
        fallback_line: Any,
        fallback_bookmaker: Any,
        parent_label: str,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(outcome, dict):
            return None

        name = str(outcome.get("name") or outcome.get("label") or "").upper()

        inferred_type = None
        if "OVER" in name:
            inferred_type = "OVER"
        elif "UNDER" in name:
            inferred_type = "UNDER"
        elif "OVER" in parent_label:
            inferred_type = "OVER"
        elif "UNDER" in parent_label:
            inferred_type = "UNDER"

        if not inferred_type:
            return None

        return {
            "market_type": inferred_type,
            "line": self._normalize_line(
                outcome.get("line") or outcome.get("point") or fallback_line
            ),
            "odds": self._safe_float(outcome.get("odds") or outcome.get("price")),
            "bookmaker": outcome.get("bookmaker") or fallback_bookmaker,
            "raw_market": deepcopy(outcome),
        }

    # ---------------------------------------------------
    # Validación
    # ---------------------------------------------------

    def _validate_candidate(
        self,
        candidate: Dict[str, Any],
        requested_market_type: Optional[str],
        market_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        market_type = candidate.get("market_type")
        odds = self._safe_float(candidate.get("odds"))
        line = candidate.get("line")
        bookmaker = candidate.get("bookmaker")

        late_pressure = bool(market_profile.get("market_late_pressure", False))
        live_bias = str(market_profile.get("market_live_bias") or "").upper()

        min_odds = self.LATE_MIN_ODDS if late_pressure else self.MIN_ODDS
        max_odds = self.LATE_MAX_ODDS if late_pressure else self.MAX_ODDS

        if not market_type:
            return self._reject("MARKET_TYPE_UNKNOWN")

        if requested_market_type and market_type != requested_market_type:
            return self._reject("MARKET_TYPE_MISMATCH")

        if odds <= 0:
            return self._reject("MARKET_ODDS_MISSING")

        if odds < min_odds or odds > max_odds:
            return self._reject("MARKET_ODDS_OUT_OF_RANGE")

        if line in (None, "", "NONE"):
            return self._reject("MARKET_LINE_MISSING")

        if requested_market_type == "OVER" and live_bias == "AGAINST_OVER":
            return self._reject("MARKET_CONTEXT_AGAINST_OVER")

        if requested_market_type == "UNDER" and live_bias == "AGAINST_UNDER":
            return self._reject("MARKET_CONTEXT_AGAINST_UNDER")

        return {
            "is_valid": True,
            "market_type": market_type,
            "line": str(line),
            "odds": round(odds, 3),
            "bookmaker": bookmaker,
            "market_status": "VALID",
            "reason": None,
            "raw_market": deepcopy(candidate.get("raw_market")),
        }

    def _pick_best_candidate(
        self,
        candidates: List[Dict[str, Any]],
        market_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        target = 1.80

        if market_profile.get("market_late_pressure"):
            target = 1.95

        def score(candidate: Dict[str, Any]) -> tuple[float, float]:
            odds = self._safe_float(candidate.get("odds"))
            line = self._line_distance_from_operable_center(candidate.get("line"))
            return (abs(odds - target), line)

        best = min(candidates, key=score)
        return deepcopy(best)

    def _pick_best_reject_reason(self, reasons: List[Optional[str]]) -> str:
        priority = [
            "MARKET_CONTEXT_AGAINST_OVER",
            "MARKET_CONTEXT_AGAINST_UNDER",
            "MARKET_NOT_FOUND",
            "MARKET_ODDS_MISSING",
            "MARKET_LINE_MISSING",
            "MARKET_ODDS_OUT_OF_RANGE",
            "MARKET_TYPE_UNKNOWN",
            "MARKET_TYPE_MISMATCH",
        ]
        filtered = [r for r in reasons if r]
        for item in priority:
            if item in filtered:
                return item
        return filtered[0] if filtered else "MARKET_INVALID"

    def _can_fallback_to_pending(self, reasons: List[Optional[str]]) -> bool:
        allowed = {
            "MARKET_NOT_FOUND",
            "MARKET_ODDS_MISSING",
            "MARKET_LINE_MISSING",
            "MARKET_INVALID",
        }
        filtered = {r for r in reasons if r}
        if not filtered:
            return True
        return filtered.issubset(allowed)

    def _build_pending_market(self, market_type: str) -> Dict[str, Any]:
        return {
            "is_valid": True,
            "market_type": market_type,
            "line": "AUTO",
            "odds": None,
            "bookmaker": None,
            "market_status": "PENDING",
            "reason": "MARKET_PENDING_INTERNAL",
            "raw_market": None,
        }

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------

    def _normalize_market_type(self, market_type: Optional[str]) -> Optional[str]:
        if not market_type:
            return None

        text = str(market_type).strip().upper()
        if "OVER" in text:
            return "OVER"
        if "UNDER" in text:
            return "UNDER"
        return text

    def _market_type_matches(self, candidate_type: str, requested_type: Optional[str]) -> bool:
        if requested_type is None:
            return candidate_type in {"OVER", "UNDER"}
        return candidate_type == requested_type

    def _normalize_line(self, line: Any) -> Optional[str]:
        if line is None:
            return None

        if isinstance(line, (int, float)):
            return str(float(line)).rstrip("0").rstrip(".")

        text = str(line).strip()
        if not text:
            return None

        return text

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

    def _line_distance_from_operable_center(self, line: Any) -> float:
        value = self._safe_float(line)
        if value <= 0:
            return 999.0
        return abs(value - 2.5)

    def _looks_like_total_market(self, label: str, market: Dict[str, Any]) -> bool:
        label_upper = str(label or "").upper()

        if "OVER" in label_upper or "UNDER" in label_upper:
            return True

        if "TOTAL" in label_upper or "GOALS" in label_upper:
            return True

        outcomes = market.get("outcomes")
        if isinstance(outcomes, list):
            names = [str((o or {}).get("name") or "").upper() for o in outcomes if isinstance(o, dict)]
            if any("OVER" in n for n in names) and any("UNDER" in n for n in names):
                return True

        if market.get("over") or market.get("under"):
            return True

        return False

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "is_valid": False,
            "market_type": None,
            "line": None,
            "odds": None,
            "bookmaker": None,
            "market_status": "INVALID",
            "reason": reason,
            "raw_market": None,
                }
