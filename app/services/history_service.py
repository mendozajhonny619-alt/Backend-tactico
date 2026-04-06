import json
import os
from datetime import datetime

class HistoryService:
    FILE_PATH = "data/history_signals.json"

    @staticmethod
    def _asegurar_archivo():
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(HistoryService.FILE_PATH):
            with open(HistoryService.FILE_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)

    @staticmethod
    def obtener_historial():
        try:
            HistoryService._asegurar_archivo()
            with open(HistoryService.FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def registrar_senal(match, motores):
        HistoryService._asegurar_archivo()

        history = HistoryService.obtener_historial()

        registro = {
            "timestamp": datetime.now().isoformat(),
            "match_id": match.get("match_id"),
            "partido": f"{match.get('home', 'N/A')} vs {match.get('away', 'N/A')}",
            "liga": match.get("league"),
            "pais": match.get("country"),
            "minuto": match.get("minute"),
            "marcador_entrada": match.get("score"),
            "mercado": match.get("market"),
            "seleccion": match.get("selection"),
            "linea": match.get("line"),
            "cuota": match.get("cuota"),
            "confianza": match.get("confidence"),
            "edge": motores.get("value", {}).get("edge"),
            "value_category": motores.get("value", {}).get("value_category"),
            "match_state": motores.get("tactica", {}).get("match_state"),
            "risk_score": motores.get("riesgo", {}).get("risk_score"),
            "signal_score": match.get("signal_score"),
            "signal_rank": match.get("signal_rank"),
            "publish_ready": match.get("publish_ready"),
            "reason": match.get("reason"),
            "resultado_final": "PENDIENTE",
            "motivo_fallo": "N/A"
        }

        history.append(registro)

        with open(HistoryService.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
