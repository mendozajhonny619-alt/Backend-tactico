# app/services/history_service.py
import json
import os
from datetime import datetime

class HistoryService:
    """
    JHONNY_ELITE V16 - Memoria del Sistema
    Registra señales para auditoría y aprendizaje continuo (Regla #19).
    """
    FILE_PATH = "data/history_signals.json"

    @staticmethod
    def registrar_senal(match, motores):
        # Asegurar que la carpeta existe
        os.makedirs("data", exist_ok=True)
        
        registro = {
            "timestamp": datetime.now().isoformat(),
            "match_id": match.get('match_id'),
            "partido": f"{match['home']} vs {match['away']}",
            "liga": match.get('league'),
            "minuto": match.get('minute'),
            "marcador_entrada": match.get('score'),
            "mercado": match.get('market'),
            "cuota": match.get('cuota'),
            "confianza": match.get('confidence'),
            "edge": motores['value'].get('edge'),
            "match_state": motores['tactica'].get('match_state'),
            "resultado_final": "PENDIENTE", # Se actualiza después
            "motivo_fallo": "N/A"
        }

        # Guardar en JSON (Simulado para facilidad de uso rápido)
        history = []
        if os.path.exists(HistoryService.FILE_PATH):
            with open(HistoryService.FILE_PATH, "r") as f:
                history = json.load(f)
        
        history.append(registro)
        with open(HistoryService.FILE_PATH, "w") as f:
            json.dump(history, f, indent=4)
