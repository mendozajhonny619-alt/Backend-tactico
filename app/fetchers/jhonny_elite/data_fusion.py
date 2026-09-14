from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def sf(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except Exception:
        return default


def si(value: Any, default: int = 0) -> int:
    try:
        return int(float(value)) if value not in (None, "") else default
    except Exception:
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NormalizedMatch:
    match_id: str
    fixture_id: str
    home: str
    away: str
    league: str = ""
    country: str = ""
    competition: str = ""
    minute: int = 0
    period: str = ""
    home_score: int = 0
    away_score: int = 0
    shots: float = 0.0
    shots_on_target: float = 0.0
    dangerous_attacks: float = 0.0
    corners: float = 0.0
    possession_home: float = 0.0
    possession_away: float = 0.0
    xg: float = 0.0
    yellow_cards: float = 0.0
    red_cards: float = 0.0
    substitutions: Any = None
    events: Any = None
    lineups: Any = None
    source: str = "UNKNOWN"
    source_timestamp: Optional[str] = None
    received_timestamp: str = field(default_factory=now_iso)
    data_age: Optional[float] = None
    data_quality: str = "UNKNOWN"
    freshness: str = "UNKNOWN"
    line: Optional[float] = None
    odds: Optional[float] = None
    odds_provider: Optional[str] = None
    prematch: Dict[str, Any] = field(default_factory=dict)
    source_payloads: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProviderAdapter:
    """Provider contract. External providers must normalize before AI layers."""
    name = "GENERIC"

    def normalize(self, payload: Dict[str, Any]) -> NormalizedMatch:
        raise NotImplementedError


class ApiFootballProvider(ProviderAdapter):
    name = "API_FOOTBALL"

    def normalize(self, payload: Dict[str, Any]) -> NormalizedMatch:
        match_id = str(payload.get("match_id") or payload.get("fixture_id") or payload.get("id") or "")
        return NormalizedMatch(
            match_id=match_id,
            fixture_id=str(payload.get("fixture_id") or match_id),
            home=str(payload.get("home_team") or payload.get("home") or ""),
            away=str(payload.get("away_team") or payload.get("away") or ""),
            league=str(payload.get("league") or ""),
            country=str(payload.get("country") or ""),
            competition=str(payload.get("competition") or payload.get("league") or ""),
            minute=si(payload.get("effective_minute") or payload.get("api_minute") or payload.get("minute")),
            period=str(payload.get("period") or payload.get("status_short") or ""),
            home_score=si(payload.get("home_score")),
            away_score=si(payload.get("away_score")),
            shots=sf(payload.get("shots") or payload.get("total_shots")),
            shots_on_target=sf(payload.get("shots_on_target") or payload.get("total_shots_on")),
            dangerous_attacks=sf(payload.get("dangerous_attacks") or payload.get("total_dangerous_attacks")),
            corners=sf(payload.get("corners")),
            possession_home=sf(payload.get("possession_home")),
            possession_away=sf(payload.get("possession_away")),
            xg=sf(payload.get("xg") or payload.get("xG")),
            yellow_cards=sf(payload.get("yellow_cards")),
            red_cards=sf(payload.get("red_cards")),
            substitutions=payload.get("substitutions"),
            events=payload.get("events"),
            lineups=payload.get("lineups"),
            source=self.name,
            source_timestamp=payload.get("updated_at") or payload.get("source_timestamp"),
            data_age=payload.get("data_age_seconds"),
            data_quality=str(payload.get("data_quality") or "UNKNOWN"),
            line=payload.get("line"),
            odds=payload.get("odds"),
            odds_provider=payload.get("odds_provider"),
            prematch=payload.get("prematch") if isinstance(payload.get("prematch"), dict) else {},
            source_payloads={self.name: payload},
        )


class FlashscoreProvider(ProviderAdapter):
    """Optional adapter contract.

    No scraping implementation is bundled.  Supply data through an authorised
    connector/provider, then call normalize() with the mapped dictionary.
    """
    name = "FLASHSCORE"

    def normalize(self, payload: Dict[str, Any]) -> NormalizedMatch:
        # Accepts the common schema only; deliberately does not scrape a site.
        item = ApiFootballProvider().normalize(payload)
        item.source = self.name
        item.source_payloads = {self.name: payload}
        return item


class PrematchProvider(ProviderAdapter):
    name = "PREMATCH"

    def normalize(self, payload: Dict[str, Any]) -> NormalizedMatch:
        item = ApiFootballProvider().normalize(payload)
        item.source = self.name
        item.source_payloads = {self.name: payload}
        return item


class OddsProvider(ProviderAdapter):
    name = "ODDS"

    def normalize(self, payload: Dict[str, Any]) -> NormalizedMatch:
        item = ApiFootballProvider().normalize(payload)
        item.source = self.name
        item.source_payloads = {self.name: payload}
        return item


class DataFusionEngine:
    """Conflict-aware fusion of normalized provider snapshots."""

    def fuse(self, snapshots: Iterable[NormalizedMatch]) -> Dict[str, Any]:
        rows = [x for x in snapshots if isinstance(x, NormalizedMatch)]
        if not rows:
            return {"ok": False, "conflicts": ["NO_SOURCE"], "match": {}}
        rows.sort(key=lambda x: (self._freshness_score(x), self._source_reliability(x.source)), reverse=True)
        winner = rows[0]
        conflicts: List[str] = []
        for other in rows[1:]:
            if (winner.home_score, winner.away_score) != (other.home_score, other.away_score):
                conflicts.append("SCORE_CONFLICT")
            if abs(winner.minute - other.minute) >= 3:
                conflicts.append("CLOCK_CONFLICT")
            if abs(winner.shots_on_target - other.shots_on_target) >= 4:
                conflicts.append("STATS_CONFLICT")
            if self._freshness_score(other) < -120:
                conflicts.append("STALE_SOURCE")

        fused = winner.to_dict()
        fused["source_payloads"] = {r.source: r.source_payloads.get(r.source, {}) for r in rows}
        fused["fusion_sources"] = [r.source for r in rows]
        fused["fusion_conflicts"] = sorted(set(conflicts))
        fused["fusion_status"] = "CONFLICTED" if conflicts else "CONSISTENT"
        fused["source"] = "FUSED" if len(rows) > 1 else winner.source
        return {"ok": True, "conflicts": sorted(set(conflicts)), "match": fused}

    @staticmethod
    def _source_reliability(source: str) -> float:
        return {"API_FOOTBALL": 0.95, "FLASHSCORE": 0.90, "ODDS": 0.88, "PREMATCH": 0.85}.get(str(source).upper(), 0.70)

    @staticmethod
    def _freshness_score(item: NormalizedMatch) -> float:
        age = sf(item.data_age, 0.0)
        return -age
