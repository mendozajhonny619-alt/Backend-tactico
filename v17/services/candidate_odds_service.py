from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from app.config.config import Config

logger = logging.getLogger(__name__)


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


class CandidateOddsService:
    """Consulta cuotas live solo cuando el motor ya detectó un candidato.

    Fuente primaria: API-Football /odds/live?fixture=...
    El parser es tolerante a cambios de estructura y extrae mercados totals.
    """

    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self, ttl_seconds: int = 45) -> None:
        self.api_key = Config.API_FOOTBALL_KEY
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cooldown_until = 0.0

    def enrich(
        self,
        match: Dict[str, Any],
        market: str,
        model_probability: float = 0.0,
    ) -> Dict[str, Any]:
        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "").strip()
        direction = str(market or "").upper()
        current_total = int(sf(match.get("home_score"))) + int(sf(match.get("away_score")))
        target_line = current_total + 0.5

        if direction not in {"OVER", "UNDER"}:
            return self._empty("INVALID_MARKET", direction, target_line)
        if not Config.CANDIDATE_ODDS_ENABLED:
            return self._empty("DISABLED", direction, target_line)
        if not fixture_id or not self.api_key:
            return self._from_existing_match(match, direction, target_line, model_probability)

        now = time.time()
        cached = self._cache.get(fixture_id)
        if cached and now - cached.get("at", 0) < self.ttl_seconds:
            raw = cached.get("data", [])
        elif now < self._cooldown_until:
            return self._from_existing_match(match, direction, target_line, model_probability, "RATE_LIMIT_COOLDOWN")
        else:
            try:
                response = requests.get(
                    f"{self.BASE_URL}/odds/live",
                    headers={"x-apisports-key": self.api_key},
                    params={"fixture": fixture_id},
                    timeout=7,
                )
                if response.status_code == 429:
                    self._cooldown_until = now + 300
                    return self._from_existing_match(match, direction, target_line, model_probability, "RATE_LIMIT_429")
                if response.status_code != 200:
                    return self._from_existing_match(match, direction, target_line, model_probability, f"HTTP_{response.status_code}")
                body = response.json()
                raw = body.get("response") or []
                self._cache[fixture_id] = {"at": now, "data": raw}
            except Exception as exc:
                logger.debug("candidate odds unavailable fixture=%s: %s", fixture_id, exc)
                return self._from_existing_match(match, direction, target_line, model_probability, type(exc).__name__)

        candidates = self._extract_totals(raw, direction)
        if not candidates:
            return self._from_existing_match(match, direction, target_line, model_probability, "NO_TOTALS_FOUND")

        candidates.sort(
            key=lambda x: (
                abs(sf(x.get("line"), target_line) - target_line),
                -sf(x.get("odds"), 0.0),
            )
        )
        selected = candidates[0]
        odds = sf(selected.get("odds"), 0.0)
        implied = (100.0 / odds) if odds > 1.0 else 0.0
        edge = model_probability - implied if model_probability > 0 and implied > 0 else 0.0

        return {
            "odds_available": odds > 1.0,
            "odds_source": "API_FOOTBALL_LIVE_ODDS",
            "odds_status": "OK" if odds > 1.0 else "INVALID_ODDS",
            "market_direction": direction,
            "line": sf(selected.get("line"), target_line),
            "odds": odds,
            "bookmaker": selected.get("bookmaker"),
            "implied_probability": round(implied, 2),
            "model_probability_for_value": round(model_probability, 2),
            "value_edge": round(edge, 2),
            "has_positive_value": bool(edge >= Config.EDGE_MINIMO * 100) if model_probability > 0 else False,
            "target_line": target_line,
        }

    def _extract_totals(self, raw: Any, direction: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for node in self._walk(raw):
            if not isinstance(node, dict):
                continue
            text = " ".join(
                str(node.get(k) or "")
                for k in ("name", "value", "label", "bet", "market", "title")
            ).upper()
            if direction not in text:
                continue
            odd = sf(node.get("odd") or node.get("odds") or node.get("price"), 0.0)
            if odd <= 1.0:
                continue
            line = self._parse_line(text)
            if line is None:
                line = sf(node.get("handicap") or node.get("point") or node.get("line"), 0.0)
            if line <= 0:
                continue
            rows.append({
                "line": line,
                "odds": odd,
                "bookmaker": node.get("bookmaker") or node.get("bookmaker_name") or node.get("provider"),
                "raw_text": text[:160],
            })
        return rows

    def _walk(self, value: Any) -> Iterable[Any]:
        if isinstance(value, dict):
            yield value
            for v in value.values():
                yield from self._walk(v)
        elif isinstance(value, list):
            for item in value:
                yield from self._walk(item)

    @staticmethod
    def _parse_line(text: str) -> Optional[float]:
        match = re.search(r"(?:OVER|UNDER)\s*([0-9]+(?:[\.,][0-9]+)?)", text, flags=re.I)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", "."))
        except Exception:
            return None

    def _from_existing_match(
        self,
        match: Dict[str, Any],
        direction: str,
        target_line: float,
        model_probability: float,
        reason: str = "MATCH_FALLBACK",
    ) -> Dict[str, Any]:
        odds = sf(match.get("odds") or match.get("odd") or match.get("cuota"), 0.0)
        line = sf(match.get("line") or match.get("market_line"), target_line)
        implied = 100.0 / odds if odds > 1.0 else 0.0
        edge = model_probability - implied if model_probability > 0 and implied > 0 else 0.0
        return {
            "odds_available": odds > 1.0,
            "odds_source": "MATCH_ATTACHED" if odds > 1.0 else "NONE",
            "odds_status": reason,
            "market_direction": direction,
            "line": line,
            "odds": odds,
            "bookmaker": match.get("bookmaker"),
            "implied_probability": round(implied, 2),
            "model_probability_for_value": round(model_probability, 2),
            "value_edge": round(edge, 2),
            "has_positive_value": bool(edge >= Config.EDGE_MINIMO * 100) if model_probability > 0 else False,
            "target_line": target_line,
        }

    @staticmethod
    def _empty(reason: str, direction: str, target_line: float) -> Dict[str, Any]:
        return {
            "odds_available": False,
            "odds_source": "NONE",
            "odds_status": reason,
            "market_direction": direction,
            "line": target_line,
            "odds": 0.0,
            "implied_probability": 0.0,
            "value_edge": 0.0,
            "has_positive_value": False,
            "target_line": target_line,
        }
