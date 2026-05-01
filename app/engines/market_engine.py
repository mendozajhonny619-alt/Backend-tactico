from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


class MarketEngine:
    """
    Valida y normaliza mercado operable para el sistema.

    Filosofía actual:
    - Si existe mercado real, validarlo de forma estricta.
    - Si NO existe mercado real todavía, permitir mercado interno provisional
      para no matar una señal fuerte del sistema.
    - Nunca inventar cuotas fijas falsas.
    - Preparado para integrarse con The Odds API.

    Reglas base:
    - Rango válido de odds reales: 1.50 a 2.10
    - Si hay mercado real, debe devolver línea, cuota y bookmaker
    - Si no hay mercado real, puede devolver fallback:
        market_status = "PENDING"
        line = "AUTO"
        odds = None
        bookmaker = None
        reason = "MARKET_PENDING_INTERNAL"

    Soporta entradas flexibles:
    - match["markets"]
    - match["odds"]
    - match["bookmakers"]
    - estructuras simples ya normalizadas
    """

    MIN_ODDS = 1.50
    MAX_ODDS = 2.10

    def evaluate(
        self,
        match: Dict[str, Any],
        market_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_market_type = self._normalize_market_type(market_type)

        if normalized_market_type not in {"OVER", "UNDER"}:
            return self._reject("MARKET_TYPE_UNKNOWN")

        raw_candidates = self._extract_market_candidates(match, normalized_market_type)

        if not raw_candidates:
            return self._build_pending_market(normalized_market_type)

        operable_candidates = []
        rejected_reasons = []

        for candidate in raw_candidates:
            validated = self._validate_candidate(candidate, normalized_market_type)
            if validated["is_valid"]:
                operable_candidates.append(validated)
            else:
                rejected_reasons.append(validated.get("reason"))

        if not operable_candidates:
            # Si existe estructura de mercado pero aún no es operable,
            # no matamos del todo la lectura interna.
            if self._can_fallback_to_pending(rejected_reasons):
                return self._build_pending_market(normalized_market_type)

            return self._reject(self._pick_best_reject_reason(rejected_reasons))

        best = self._pick_best_candidate(operable_candidates)
        best["market_status"] = "OK"
        best["reason"] = None
        return best

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
                    "line": self._normalize_line(
                        side.get("line") or line or item.get("line")
                    ),
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
    ) -> Dict[str, Any]:
        market_type = candidate.get("market_type")
        odds = self._safe_float(candidate.get("odds"))
        line = candidate.get("line")
        bookmaker = candidate.get("bookmaker")

        if not market_type:
            return self._reject("MARKET_TYPE_UNKNOWN")

        if requested_market_type and market_type != requested_market_type:
            return self._reject("MARKET_TYPE_MISMATCH")

        if odds <= 0:
            return self._reject("MARKET_ODDS_MISSING")

        if odds < self.MIN_ODDS or odds > self.MAX_ODDS:
            return self._reject("MARKET_ODDS_OUT_OF_RANGE")

        if line in (None, "", "NONE"):
            return self._reject("MARKET_LINE_MISSING")

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

    def _pick_best_candidate(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prioriza la cuota más cercana al centro operativo del sistema.
        Centro ideal aproximado: 1.80
        """
        target = 1.80

        def score(candidate: Dict[str, Any]) -> tuple[float, float]:
            odds = self._safe_float(candidate.get("odds"))
            line = self._line_distance_from_operable_center(candidate.get("line"))
            return (abs(odds - target), line)

        best = min(candidates, key=score)
        return deepcopy(best)

    def _pick_best_reject_reason(self, reasons: List[Optional[str]]) -> str:
        priority = [
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
