"""Normalizacion estricta y sin I/O de mercados de GOLES full-time.

No se infiere un mercado a partir de la palabra Over/Under en el resultado:
primero debe identificarse el tipo de apuesta en su contenedor (bet).
Los IDs de /odds/live/bets y /odds/bets pertenecen a catalogos diferentes.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional


_FORBIDDEN = (
    "corner", "tarjet", "card", "booking", "yellow", "red card", "throw", "offside",
    "shot", "foul", "free kick", "goal kick", "penalt", "player", "team total",
    "home total", "away total", "home goal", "away goal", "1st half", "2nd half",
    "first half", "second half", "1st period", "2nd period", "quarter",
    "next 5", "next 10", "next 15", "first 10", "first 15", "first goal",
    "half time", "half-time", "half/full", "extra time", "1st 45", "2nd 45",
    "team goals", "asian", "clean sheet", "winning margin", "exact goals",
)

# Explicitly allowed full-match totals; 'total' alone may refer to corners,
# cards or shots, so it is intentionally NOT an accepted name.
_ALLOWED_MARKET_NAMES = {
    "over under", "goals over under", "goal over under", "over under goals",
    "total goals", "goals total", "match total goals", "match goals",
    "total match goals", "total goals over under", "total goals full time",
    "full time goals over under", "full time total goals",
    "match goals over under",
}


def _simplify(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(ch for ch in raw if not unicodedata.combining(ch)).lower()
    ascii_text = ascii_text.replace("o/u", "over under")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_text)).strip()


def is_full_time_goals_market(name: Any) -> bool:
    """Whitelist of football MATCH goals totals, not generic over/under text."""
    original = str(name or "").lower()
    if any(term in original for term in _FORBIDDEN):
        return False
    normalized = _simplify(name)
    if normalized in _ALLOWED_MARKET_NAMES:
        return True
    # A few providers put 'FT' or '(90 min)' into an otherwise exact label.
    for suffix in (" ft", " full time", " 90 min", " 90 minutes", " regular time"):
        if normalized.endswith(suffix) and normalized[: -len(suffix)] in _ALLOWED_MARKET_NAMES:
            return True
    return False


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _boolean_true(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def _date_iso(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or str(value).strip().isdigit():
            raw = float(value)
            if raw > 10**11:
                raw /= 1000
            if 1_000_000_000 < raw < 10_000_000_000:
                return datetime.fromtimestamp(raw, timezone.utc).isoformat()
            return None
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # The provider has not established UTC for a naive ISO timestamp.
        # Never assume UTC and turn an ambiguous quote into an apparently
        # fresh, publishable in-play price.
        if moment.tzinfo is None:
            return None
        return moment.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _direction_and_line(outcome: Mapping[str, Any]) -> Optional[tuple[str, float]]:
    raw_value = str(outcome.get("value") or outcome.get("name") or "").strip()
    selection = re.fullmatch(r"\s*(Over|Under)(?:\s+([0-9]+(?:[.,][0-9]+)?))?\s*", raw_value, flags=re.I)
    if not selection:
        return None
    selection_line = _as_number(selection.group(2)) if selection.group(2) else None
    handicap = next((_as_number(outcome.get(k)) for k in ("handicap", "point", "line") if outcome.get(k) not in (None, "")), None)
    if selection_line is not None and handicap is not None and abs(selection_line - handicap) > 0.00001:
        return None
    line = selection_line if selection_line is not None else handicap
    if line is None or not 0 < line <= 12.5:
        return None
    return selection.group(1).upper(), line


def extract_match_goals_totals(
    raw: Any,
    direction: str,
    *,
    live: bool,
    fixture_id: Optional[str] = None,
    market_catalog: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Parse official API-Football bet containers, never arbitrary nested values.

    For LIVE quotes, suspended/stopped/blocked/finished results are ignored.
    A missing fixture ID can be shown as unverified but cannot pass publication.
    Pre-match quotes remain informative and are never treated as LIVE evidence.
    """
    requested = str(direction or "").upper()
    if requested not in {"OVER", "UNDER"}:
        return []
    events = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    out: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        fixture = event.get("fixture")
        event_id = fixture.get("id") if isinstance(fixture, dict) else fixture
        if fixture_id and event_id is not None and str(event_id) != str(fixture_id):
            continue
        id_verified = bool(fixture_id and event_id is not None and str(event_id) == str(fixture_id))
        status = event.get("status") if isinstance(event.get("status"), dict) else {}
        if live and any(_boolean_true(status.get(field)) for field in ("stopped", "blocked", "finished")):
            continue
        quote_stamp = _date_iso(event.get("update") or event.get("last_update") or event.get("updated_at"))
        bookmaker_groups = [(None, event.get("bets"))] if live else [
            (bookmaker.get("name"), bookmaker.get("bets"))
            for bookmaker in event.get("bookmakers", [])
            if isinstance(bookmaker, dict)
        ]
        for bookmaker, bets in bookmaker_groups:
            for bet in bets or []:
                if not isinstance(bet, dict):
                    continue
                bet_id = bet.get("id")
                name = bet.get("name") or bet.get("market")
                if not name and bet_id is not None:
                    name = (market_catalog or {}).get(str(bet_id))
                if not is_full_time_goals_market(name) or _boolean_true(bet.get("suspended")) or _boolean_true(bet.get("blocked")):
                    continue
                bet_stamp = _date_iso(bet.get("update") or bet.get("last_update")) or quote_stamp
                for value in bet.get("values") or []:
                    if not isinstance(value, dict) or _boolean_true(value.get("suspended")):
                        continue
                    selected = _direction_and_line(value)
                    if not selected or selected[0] != requested:
                        continue
                    odd = _as_number(value.get("odd") if "odd" in value else value.get("price"))
                    if odd is None or not 1.0 < odd <= 1000.0:
                        continue
                    out.append({
                        "line": selected[1], "odds": odd,
                        "bookmaker": bookmaker,
                        "market_id": bet_id,
                        "market_name": str(name),
                        "market_period": "FT",
                        "market_type": "MATCH_GOALS_TOTAL",
                        "fixture_verified": id_verified,
                        "fixture_id": str(event_id) if event_id is not None else None,
                        "quote_is_live": live,
                        "market_verified": True,
                        "timestamp": _date_iso(value.get("update")) or bet_stamp,
                        "main": value.get("main") is True,
                        "raw_text": f"{requested} {selected[1]:g}",
                    })
    return out
