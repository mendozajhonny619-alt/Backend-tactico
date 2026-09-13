from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.app_container import app_container

router = APIRouter()


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _market(item: Dict[str, Any]) -> str:
    return str(item.get("market") or "").upper()


def _type(item: Dict[str, Any]) -> str:
    return str(item.get("type") or "").upper()


def _rank(item: Dict[str, Any]) -> str:
    return str(item.get("rank") or "").upper()


@router.get("/health")
def health() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state
    system_status = _safe_dict(runtime_state.get_health_status())

    return {
        "ok": system_status.get("status") == "OK",
        "system_status": system_status,
    }


@router.get("/live")
def live() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state
    items = _safe_list(runtime_state.get_live_matches())

    return {
        "ok": True,
        "count": len(items),
        "items": items,
    }


@router.get("/signals")
def signals() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state
    items = _safe_list(runtime_state.get_active_signals())
    stats = _safe_dict(runtime_state.get_stats())

    return {
        "ok": True,
        "count": len(items),
        "items": items,
        "signals": items,
        "updated_at": stats.get("updated_at"),
    }


@router.get("/history")
def history() -> Dict[str, Any]:
    history_service = app_container.history_service
    items = _safe_list(history_service.get_history())

    return {
        "ok": True,
        "count": len(items),
        "items": items,
        "history": items,
    }


@router.get("/opportunities")
def opportunities() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state

    opportunities_items = _safe_list(runtime_state.get_opportunities())
    active_signals = _safe_list(runtime_state.get_active_signals())
    blocked_items = _safe_list(runtime_state.get_blocked())
    stats = _safe_dict(runtime_state.get_stats())

    combined = []
    seen = set()

    for item in active_signals + opportunities_items:
        if not isinstance(item, dict):
            continue

        key = str(
            item.get("signal_key")
            or item.get("signal_id")
            or item.get("opportunity_id")
            or f"{item.get('match_id')}:{item.get('market') or item.get('type')}"
        )

        if key in seen:
            continue

        seen.add(key)
        combined.append(item)

    over_candidates = []
    under_candidates = []
    observe = []
    rejected = []

    for item in combined:
        market = _market(item)
        item_type = _type(item)
        rank = _rank(item)

        if market == "OVER" or item_type == "OVER_CANDIDATE":
            over_candidates.append(item)
        elif market == "UNDER" or item_type == "UNDER_CANDIDATE":
            under_candidates.append(item)
        elif item_type in {"REJECTED", "NO_BET"} or rank in {"RECHAZADO", "NO_BET"}:
            rejected.append(item)
        else:
            observe.append(item)

    for item in blocked_items[:20]:
        if isinstance(item, dict):
            rejected.append(item)

    premium = sum(1 for x in combined if _rank(x) == "PREMIUM")
    strong = sum(1 for x in combined if _rank(x) == "FUERTE")
    good = sum(1 for x in combined if _rank(x) in {"BUENA", "OPERABLE"})
    observation = sum(
        1 for x in combined
        if _rank(x) == "OBSERVACION" or _type(x) == "OBSERVE"
    )
    no_bet = sum(
        1 for x in combined
        if _rank(x) == "NO_BET" or _type(x) == "NO_BET"
    )

    return {
        "ok": True,
        "summary": {
            "total": len(combined),
            "over": len(over_candidates),
            "under": len(under_candidates),
            "observe": len(observe),
            "rejected": len(rejected),
            "premium": premium,
            "strong": strong,
            "good": good,
            "observation": observation,
            "no_bet": no_bet,
            "blocked_total": len(blocked_items),
            "updated_at": stats.get("updated_at"),
        },
        "sections": {
            "over_candidates": over_candidates,
            "under_candidates": under_candidates,
            "observe": observe,
            "rejected": rejected,
        },
        "items": combined,
        "top": over_candidates + under_candidates,
        "observe": observe,
        "blocked": rejected,
        "updated_at": stats.get("updated_at"),
    }


@router.get("/stats")
def stats() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state
    data = _safe_dict(runtime_state.get_stats())

    return {
        "ok": True,
        "stats": data,
    }


@router.get("/dashboard")
def dashboard() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state
    history_service = app_container.history_service

    live_matches = _safe_list(runtime_state.get_live_matches())
    active_signals = _safe_list(runtime_state.get_active_signals())
    opportunities_items = _safe_list(runtime_state.get_opportunities())
    blocked_items = _safe_list(runtime_state.get_blocked())
    stats = _safe_dict(runtime_state.get_stats())
    history_items = _safe_list(history_service.get_history())
    health_status = _safe_dict(runtime_state.get_health_status())

    return {
        "ok": True,
        "live": {
            "count": len(live_matches),
            "items": live_matches,
        },
        "signals": {
            "count": len(active_signals),
            "items": active_signals,
        },
        "opportunities": {
            "count": len(opportunities_items),
            "items": opportunities_items,
        },
        "blocked": {
            "count": len(blocked_items),
            "items": blocked_items[:20],
        },
        "history": {
            "count": len(history_items),
            "items": history_items[:20],
        },
        "stats": stats,
        "health": health_status,
    }
