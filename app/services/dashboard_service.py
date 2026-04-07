from datetime import datetime
from app.services.history_service import HistoryService
from app.services.live_signal_manager import LiveSignalManager

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
        active_signals = LiveSignalManager.active_signals

        total_signals = len(history)
        total_matches = len(active_signals)
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

    @staticmethod
    def get_active_signals():
        active_signals = LiveSignalManager.active_signals

        formatted = []
        for signal in active_signals:
            match = signal.get("match", {})
            motores = signal.get("motores", {})

            formatted.append({
                "match_id": match.get("match_id"),
                "partido": f"{match.get('home', 'N/A')} vs {match.get('away', 'N/A')}",
                "league": match.get("league"),
                "country": match.get("country"),
                "minute": match.get("minute"),
                "score": match.get("score"),
                "market": match.get("market"),
                "selection": match.get("selection"),
                "line": match.get("line"),
                "odd": match.get("cuota"),
                "confidence": match.get("confidence"),
                "risk_score": match.get("risk_score"),
                "signal_score": match.get("signal_score"),
                "signal_rank": match.get("signal_rank"),
                "recomendacion_final": match.get("recomendacion_final"),
                "reason": match.get("reason"),
                "status": signal.get("status", "ACTIVA"),
                "match_state": motores.get("tactica", {}).get("match_state"),
                "match_state_reason": motores.get("tactica", {}).get("match_state_reason"),
                "edge": motores.get("value", {}).get("edge"),
                "value_category": motores.get("value", {}).get("value_category"),
            })

        return {
            "ok": True,
            "count": len(formatted),
            "items": formatted,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
