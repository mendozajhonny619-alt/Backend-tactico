from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.app_container import app_container

router = APIRouter()


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
    }


@router.get("/opportunities")
def opportunities() -> Dict[str, Any]:
    runtime_state = app_container.runtime_state

    opportunities_items = _safe_list(runtime_state.get_opportunities())
    blocked_items = _safe_list(runtime_state.get_blocked())
    stats = _safe_dict(runtime_state.get_stats())

    premium = 0
    strong = 0
    good = 0
    observation = 0
    no_bet = 0

    for item in opportunities_items:
        rank = str(item.get("rank") or "").upper()
        item_type = str(item.get("type") or "").upper()

        if rank == "PREMIUM":
            premium += 1
        elif rank == "FUERTE":
            strong += 1
        elif rank in {"BUENA", "OPERABLE"}:
            good += 1
        elif rank == "OBSERVACION" or item_type == "OBSERVE":
            observation += 1
        elif rank == "NO_BET" or item_type == "NO_BET":
            no_bet += 1

    top = [
        item for item in opportunities_items
        if str(item.get("rank") or "").upper() in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}
    ]

    observe = [
        item for item in opportunities_items
        if str(item.get("rank") or "").upper() == "OBSERVACION"
        or str(item.get("type") or "").upper() == "OBSERVE"
    ]

    blocked_preview = blocked_items[:20]

    return {
        "ok": True,
        "summary": {
            "total": len(opportunities_items),
            "premium": premium,
            "strong": strong,
            "good": good,
            "observation": observation,
            "no_bet": no_bet,
            "blocked_total": len(blocked_items),
            "updated_at": stats.get("updated_at"),
        },
        "top": top,
        "observe": observe,
        "blocked": blocked_preview,
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
