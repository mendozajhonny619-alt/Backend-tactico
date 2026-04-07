from fastapi import APIRouter
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/")
def home():
    return {
        "ok": True,
        "service": "JHONNY_ELITE V16",
        "message": "API operativa 🚀"
    }

@router.get("/health")
def health():
    try:
        return DashboardService.healthcheck()
    except Exception:
        return {
            "status": "error",
            "message": "Healthcheck falló"
        }

@router.get("/stats")
def stats():
    try:
        return DashboardService.get_stats()
    except Exception:
        return {
            "error": "No se pudieron obtener stats",
            "data": {}
        }

@router.get("/history")
def history():
    try:
        return DashboardService.get_history_panel()
    except Exception:
        return {
            "error": "No se pudo obtener historial",
            "data": []
        }
