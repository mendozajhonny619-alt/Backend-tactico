from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from fastapi import APIRouter

from app.services.app_container import app_container


router = APIRouter()

# Executor pequeño para proteger las rutas del panel.
# La idea es que ningún endpoint visual se quede colgado esperando procesos lentos.
_ROUTE_EXECUTOR = ThreadPoolExecutor(max_workers=8)

# Tiempo máximo por bloque del dashboard.
# Si un método tarda más que esto, la ruta responde igual con fallback.
SERVICE_TIMEOUT_SECONDS = 2.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _get_dashboard_service():
    """
    Punto único de salida para el panel visual.

    Las rutas no deben recalcular escaneo pesado.
    Solo deben leer el estado ya procesado por el worker
    y normalizarlo mediante DashboardService.
    """
    return app_container.dashboard_service


def _timeout_payload(name: str) -> Dict[str, Any]:
    updated_at = _now_iso()

    base = {
        "ok": True,
        "fallback": True,
        "timeout": True,
        "source": name,
        "updated_at": updated_at,
        "warning": f"{name} respondió con fallback por demora del servicio.",
    }

    if name == "live":
        return {
            **base,
            "count": 0,
            "items": [],
            "matches": [],
        }

    if name == "signals":
        return {
            **base,
            "count": 0,
            "items": [],
            "signals": [],
        }

    if name == "opportunities":
        return {
            **base,
            "summary": {},
            "sections": {
                "over_candidates": [],
                "under_candidates": [],
                "observe": [],
                "rejected": [],
            },
            "items": [],
        }

    if name == "blocked":
        return {
            **base,
            "count": 0,
            "items": [],
            "blocked": [],
        }

    if name == "history":
        return {
            **base,
            "count": 0,
            "total_available": 0,
            "limit": 0,
            "items": [],
            "history": [],
            "tracking_items": [],
            "tracking_history": [],
            "tracking_count": 0,
            "tracking_total_available": 0,
            "tracking_summary": {},
            "performance_analysis": {},
        }

    if name == "stats":
        return {
            **base,
            "stats": {
                "wins": 0,
                "losses": 0,
                "pending": 0,
                "precision": 0,
                "roi": 0,
            },
        }

    if name == "health":
        return {
            **base,
            "status": "DEGRADED",
            "active": False,
        }

    return base


def _safe_service_call(
    name: str,
    getter: Callable[[], Any],
    timeout_seconds: float = SERVICE_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Ejecuta una lectura del DashboardService con límite de tiempo.

    Si el método tarda demasiado o falla, devuelve un payload seguro.
    Esto evita que /dashboard, /live, /signals y demás endpoints
    queden colgados y provoquen timeout en el frontend.
    """
    future = _ROUTE_EXECUTOR.submit(getter)

    try:
        result = future.result(timeout=timeout_seconds)

        if isinstance(result, dict):
            payload = result
        else:
            payload = {}

        if not payload.get("updated_at"):
            payload["updated_at"] = _now_iso()

        payload.setdefault("ok", True)
        payload.setdefault("fallback", False)
        payload.setdefault("timeout", False)

        return payload

    except TimeoutError:
        return _timeout_payload(name)

    except Exception as exc:
        payload = _timeout_payload(name)
        payload["timeout"] = False
        payload["error"] = str(exc)
        payload["warning"] = f"{name} respondió con fallback por error interno."
        return payload


def _normalize_live(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _safe_list(payload.get("items"))
    matches = _safe_list(payload.get("matches"))

    if not items and matches:
        items = matches

    if not matches and items:
        matches = items

    return {
        "count": payload.get("count", len(items)),
        "items": items,
        "matches": matches,
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_signals(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _safe_list(payload.get("items"))
    signals = _safe_list(payload.get("signals"))

    if not items and signals:
        items = signals

    if not signals and items:
        signals = items

    return {
        "count": payload.get("count", len(items)),
        "items": items,
        "signals": signals,
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_opportunities(payload: Dict[str, Any]) -> Dict[str, Any]:
    sections = _safe_dict(payload.get("sections"))

    normalized_sections = {
        "over_candidates": _safe_list(sections.get("over_candidates")),
        "under_candidates": _safe_list(sections.get("under_candidates")),
        "observe": _safe_list(sections.get("observe")),
        "rejected": _safe_list(sections.get("rejected")),
    }

    items = _safe_list(payload.get("items"))

    if not items:
        items = (
            normalized_sections["over_candidates"]
            + normalized_sections["under_candidates"]
            + normalized_sections["observe"]
            + normalized_sections["rejected"]
        )

    return {
        "summary": _safe_dict(payload.get("summary")),
        "sections": normalized_sections,
        "items": items,
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_blocked(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _safe_list(payload.get("items"))
    blocked = _safe_list(payload.get("blocked"))

    if not items and blocked:
        items = blocked

    if not blocked and items:
        blocked = items

    return {
        "count": payload.get("count", len(items)),
        "items": items,
        "blocked": blocked,
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_history(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _safe_list(payload.get("items"))
    history = _safe_list(payload.get("history"))

    if not items and history:
        items = history

    if not history and items:
        history = items

    return {
        "count": payload.get("count", len(items)),
        "total_available": payload.get("total_available", len(items)),
        "limit": payload.get("limit"),
        "items": items,
        "history": history,
        "tracking_items": _safe_list(payload.get("tracking_items")),
        "tracking_history": _safe_list(payload.get("tracking_history")),
        "tracking_count": payload.get("tracking_count", 0),
        "tracking_total_available": payload.get("tracking_total_available", 0),
        "tracking_summary": _safe_dict(payload.get("tracking_summary")),
        "performance_analysis": _safe_dict(payload.get("performance_analysis")),
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    stats = payload.get("stats", payload)
    stats = _safe_dict(stats)

    return {
        **stats,
        "updated_at": payload.get("updated_at") or stats.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


def _normalize_health(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **payload,
        "updated_at": payload.get("updated_at") or _now_iso(),
        "fallback": payload.get("fallback", False),
        "timeout": payload.get("timeout", False),
    }


@router.get("/v17/health")
@router.get("/health")
def health() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "health",
        dashboard_service.get_health,
        timeout_seconds=1.5,
    )

    return {
        "ok": True,
        **_normalize_health(payload),
    }


@router.get("/v17/live")
@router.get("/live")
def live() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "live",
        dashboard_service.get_live,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_live(payload),
    }


@router.get("/v17/live-matches")
@router.get("/live-matches")
def live_matches() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "live",
        dashboard_service.get_live,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_live(payload),
    }


@router.get("/v17/signals")
@router.get("/signals")
def signals() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "signals",
        dashboard_service.get_signals,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_signals(payload),
    }


@router.get("/v17/history")
@router.get("/history")
def history() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "history",
        dashboard_service.get_history,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_history(payload),
    }


@router.get("/v17/opportunities")
@router.get("/opportunities")
def opportunities() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "opportunities",
        dashboard_service.get_opportunities,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_opportunities(payload),
    }


@router.get("/v17/blocked")
@router.get("/blocked")
def blocked() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "blocked",
        dashboard_service.get_blocked,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_blocked(payload),
    }


@router.get("/v17/stats")
@router.get("/stats")
def stats() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()

    payload = _safe_service_call(
        "stats",
        dashboard_service.get_stats,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    return {
        "ok": True,
        **_normalize_stats(payload),
    }


@router.get("/v17/dashboard")
@router.get("/dashboard")
def dashboard() -> Dict[str, Any]:
    dashboard_service = _get_dashboard_service()
    updated_at = _now_iso()

    live_payload = _safe_service_call(
        "live",
        dashboard_service.get_live,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    signals_payload = _safe_service_call(
        "signals",
        dashboard_service.get_signals,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    opportunities_payload = _safe_service_call(
        "opportunities",
        dashboard_service.get_opportunities,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    blocked_payload = _safe_service_call(
        "blocked",
        dashboard_service.get_blocked,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    history_payload = _safe_service_call(
        "history",
        dashboard_service.get_history,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    stats_payload = _safe_service_call(
        "stats",
        dashboard_service.get_stats,
        timeout_seconds=SERVICE_TIMEOUT_SECONDS,
    )

    health_payload = _safe_service_call(
        "health",
        dashboard_service.get_health,
        timeout_seconds=1.5,
    )

    live_data = _normalize_live(live_payload)
    signals_data = _normalize_signals(signals_payload)
    opportunities_data = _normalize_opportunities(opportunities_payload)
    blocked_data = _normalize_blocked(blocked_payload)
    history_data = _normalize_history(history_payload)
    stats_data = _normalize_stats(stats_payload)
    health_data = _normalize_health(health_payload)

    any_timeout = any(
        [
            live_data.get("timeout"),
            signals_data.get("timeout"),
            opportunities_data.get("timeout"),
            blocked_data.get("timeout"),
            history_data.get("timeout"),
            stats_data.get("timeout"),
            health_data.get("timeout"),
        ]
    )

    any_fallback = any(
        [
            live_data.get("fallback"),
            signals_data.get("fallback"),
            opportunities_data.get("fallback"),
            blocked_data.get("fallback"),
            history_data.get("fallback"),
            stats_data.get("fallback"),
            health_data.get("fallback"),
        ]
    )

    return {
        "ok": True,
        "updated_at": updated_at,
        "frontend_safe": True,
        "fallback": any_fallback,
        "timeout": any_timeout,
        "live": live_data,
        "signals": signals_data,
        "opportunities": opportunities_data,
        "blocked": blocked_data,
        "history": history_data,
        "stats": stats_data,
        "health": health_data,
        }
