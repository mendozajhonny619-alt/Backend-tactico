from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter


router = APIRouter(prefix="/v17", tags=["JHONNY ELITE V17"])

_adapter = V17DashboardAdapter()


def _safe_service_call(label: str, func, fallback: Any) -> Any:
    try:
        return func()
    except Exception as exc:
        return {
            "ok": False,
            "label": label,
            "error": str(exc),
            "fallback": True,
            "data": fallback,
        }


def _get_v16_dashboard_payload() -> Dict[str, Any]:
    """
    Intenta leer datos desde el sistema V16 actual.

    Esto permite que V17 funcione como capa nueva sin destruir V16.
    """

    payload: Dict[str, Any] = {
        "ok": True,
        "source": "V16_BRIDGE",
        "live": [],
        "signals": [],
        "opportunities": [],
        "stats": {},
        "history": [],
    }

    service = None

    try:
        from app.api.routes import _get_dashboard_service

        service = _get_dashboard_service()
    except Exception:
        service = None

    if service is None:
        try:
            from app.services.dashboard_service import DashboardService

            service = DashboardService()
        except Exception:
            service = None

    if service is None:
        payload["ok"] = False
        payload["source_status"] = "V16_SERVICE_NOT_AVAILABLE"
        return payload

    live_payload = _safe_service_call("live", lambda: service.get_live(), {"live": []})
    signals_payload = _safe_service_call("signals", lambda: service.get_signals(), {"signals": []})
    opportunities_payload = _safe_service_call("opportunities", lambda: service.get_opportunities(), {"opportunities": []})
    stats_payload = _safe_service_call("stats", lambda: service.get_stats(), {"stats": {}})
    history_payload = _safe_service_call("history", lambda: service.get_history(), {"history": []})

    payload["live"] = live_payload
    payload["signals"] = signals_payload
    payload["opportunities"] = opportunities_payload
    payload["stats"] = stats_payload
    payload["history"] = history_payload
    payload["source_status"] = "V16_SERVICE_OK"

    return payload


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": "V17",
        "status": "OK",
        "message": "JHONNY ELITE V17 API activa.",
    }


@router.get("/dashboard")
def dashboard() -> Dict[str, Any]:
    """
    Dashboard principal V17.

    Esta ruta:
    - lee datos desde V16
    - los pasa por el motor V17
    - entrega señales, observaciones, bloqueados e historial
    """

    payload = _get_v16_dashboard_payload()

    if not payload.get("ok"):
        last = _adapter.last_dashboard()
        last["source_status"] = payload.get("source_status", "V16_NOT_AVAILABLE")
        last["warning"] = "No se pudo leer V16. Se devuelve último estado V17 disponible."
        return last

    return _adapter.build_from_v16_payload(
        payload=payload,
        source_status=payload.get("source_status", "V16_SERVICE_OK"),
    )


@router.get("/signals")
def signals() -> Dict[str, Any]:
    """
    Señales V17.
    """

    dashboard()
    return _adapter.get_signals()


@router.get("/history")
def history() -> Dict[str, Any]:
    """
    Historial y tracking V17.
    """

    dashboard()
    return _adapter.get_history()


@router.get("/debug")
def debug() -> Dict[str, Any]:
    """
    Diagnóstico rápido V17.
    """

    dashboard()
    return _adapter.get_debug()


@router.post("/manual-test")
def manual_test(raw_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ruta de prueba manual.

    Permite enviar una lista de partidos simulados para probar V17
    sin depender de V16 ni de la API externa.
    """

    return _adapter.build_from_raw_matches(
        raw_matches=raw_matches,
        source_status="MANUAL_TEST",
  )
