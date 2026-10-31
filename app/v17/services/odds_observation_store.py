"""Lightweight local history of LIVE match-goals quotes, append-only.

The API-Football live odds endpoint has no historical retrieval. This journal
captures only observed market values. It never stores API credentials, user
identity, or unverified market types. IO failure must not interrupt scanning.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Set

from app.config.config import Config

logger = logging.getLogger(__name__)


class OddsObservationStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path) if path is not None else Path(getattr(Config, "DATA_DIR", "app/v17/storage")) / "live_odds_observations.jsonl"
        self._lock = threading.RLock()
        self._seen: Set[str] = set()

    def record(self, fixture_id: str, quote: Dict[str, Any]) -> bool:
        if not bool(getattr(Config, "ODDS_HISTORY_ENABLED", True)):
            return False
        if not (quote.get("quote_is_live") and quote.get("market_verified")
                and quote.get("fixture_verified") and quote.get("market_type") == "MATCH_GOALS_TOTAL"):
            return False
        # Quote timestamp may be null; observed_at is distinct and does not
        # substitute for provider freshness in MasterDecisionAI.
        entry = {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "quote_timestamp": quote.get("odds_timestamp"),
            "fixture_id": str(fixture_id),
            "market_id": quote.get("market_id"),
            "market_type": "MATCH_GOALS_TOTAL",
            "market_period": "FT",
            "selection": quote.get("market_direction"),
            "line": quote.get("line"),
            "price": quote.get("odds"),
            "source": quote.get("odds_source"),
        }
        # Deduplicate per process without mutating a historical snapshot.
        key = "|".join(str(entry[x]) for x in (
            "fixture_id", "market_id", "selection", "line", "price", "quote_timestamp"
        ))
        with self._lock:
            if key in self._seen:
                return False
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
                self._seen.add(key)
                if len(self._seen) > 25000:
                    self._seen.clear()
                return True
            except OSError as exc:
                logger.warning("ODDS_HISTORY_WRITE_FAILED: %s", exc)
                return False
