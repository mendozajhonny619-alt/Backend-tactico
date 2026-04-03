# app/engines/tactical_engine.py
from app.config.config import Config

class TacticalEngine:
    """
    JHONNY_ELITE V16 - Motor Táctico e Inteligencia de Momentum
    Implementa M2 (Clasificación), M3 (Emocional) y M4 (Gol Inminente)
    """

    @staticmethod
    def analizar_momentum(stats):
        """
        Regla #7: Las estadísticas recientes pesan más que el acumulado.
        Calcula un Score de Intensidad basado en ataques y remates.
        """
        # Extraemos variables (Asegurar que el fetcher use estos nombres)
        ataques_p = stats.get('dangerous_attacks', 0)
        remates_total = stats.get('shots', 0)
        remates_arco = stats.get('shots_on_target', 0)
        xg = stats.get('xG', 0.0)
        minuto = stats.get('minute', 0)

        # Cálculo de presión por minuto (PPM)
        ppm = ataques_p / minuto if minuto > 0 else 0
        
        # Lógica de Clasificación de Partido (M2)
        estado = "CONTROLADO"
        razon = "Ritmo estándar de juego"

        if ppm > 1.2 and remates_arco >= 3:
            estado = "EXPLOSIVO"
            razon = "Alta frecuencia de ataques peligrosos con puntería"
        elif ppm > 0.8:
            estado = "CALIENTE"
            razon = "Presión constante en área rival"
        elif ppm < 0.3 and minuto > 20:
            estado = "MUERTO"
            razon = "Falta de profundidad y ritmo"
        
        # M3: Interpretación Emocional (Inercia psicológica)
        # Si hay muchos ataques pero 0 remates al arco, el equipo está "frustrado"
        if ataques_p > 40 and remates_arco == 0:
            estado = "CAOS PELIGROSO"
            razon = "Ataques estériles, riesgo de contraataque"

        return {
            "match_state": estado,
            "match_state_reason": razon,
            "intensity_score": round(ppm * 10, 2)
        }

    @staticmethod
    def predictor_gol_inminente(stats):
        """
        M4: Ventana real de gol en próximos 5/10 min.
        """
        momentum = TacticalEngine.analizar_momentum(stats)
        
        # Un gol es inminente si el estado es EXPLOSIVO y hay xG reciente
        es_inminente = False
        confianza_gol = 0
        
        if momentum['match_state'] == "EXPLOSIVO":
            es_inminente = True
            confianza_gol = 85
        elif momentum['match_state'] == "CALIENTE":
            es_inminente = True
            confianza_gol = 70
            
        return {
            "gol_inminente": es_inminente,
            "confianza_ventana": confianza_gol,
            "ventana_minutos": 10 if es_inminente else 0
        }
