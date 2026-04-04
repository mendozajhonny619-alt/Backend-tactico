from datetime import datetime
from app.services.history_service import HistoryService

class DashboardService:
    @staticmethod
    def healthcheck():
        return {
            "ok": True,
            "system_status": "OPERATIONAL",
            "version": "V16.0_ELITE",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def get_stats():
        history = HistoryService.obtener_historial()

        total_signals = len(history)
        total_matches = 0
        errors = 0

        return {
            "ok": True,
            "stats": {
                "total_matches": total_matches,
                "total_signals": total_signals,
                "errors": errors,
                "system_status": "OPERATIONAL",
                "version": "V16.0_ELITE"
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def get_history_panel():
        history = HistoryService.obtener_historial()
        return {
            "ok": True,
            "count": len(history),
            "items": history[-20:],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
