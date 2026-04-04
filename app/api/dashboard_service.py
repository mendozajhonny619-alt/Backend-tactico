# app/api/dashboard_service.py
class DashboardService:
    @staticmethod
    def formatear_stats_panel(total_matches, total_signals, errors=0):
        """Prepara el JSON blindado para el frontend (Regla #33)"""
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
