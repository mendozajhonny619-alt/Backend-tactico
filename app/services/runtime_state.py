from copy import deepcopy
from typing import Any, Dict, List

_last_live_matches: List[Dict[str, Any]] = []
_last_signals: List[Dict[str, Any]] = []
_last_opportunities: Dict[str, Any] = {
    "ok": True,
    "summary": {},
    "sections": {
        "over_candidates": [],
        "under_candidates": [],
        "observe": [],
        "rejected": [],
    },
}


def set_last_live_matches(items: List[Dict[str, Any]]) -> None:
    global _last_live_matches
    _last_live_matches = deepcopy(items or [])


def get_last_live_matches() -> List[Dict[str, Any]]:
    return deepcopy(_last_live_matches)


def set_last_signals(items: List[Dict[str, Any]]) -> None:
    global _last_signals
    _last_signals = deepcopy(items or [])


def get_last_signals() -> List[Dict[str, Any]]:
    return deepcopy(_last_signals)


def set_last_opportunities(payload: Dict[str, Any]) -> None:
    global _last_opportunities
    _last_opportunities = deepcopy(payload or {
        "ok": True,
        "summary": {},
        "sections": {
            "over_candidates": [],
            "under_candidates": [],
            "observe": [],
            "rejected": [],
        },
    })


def get_last_opportunities() -> Dict[str, Any]:
    return deepcopy(_last_opportunities)
