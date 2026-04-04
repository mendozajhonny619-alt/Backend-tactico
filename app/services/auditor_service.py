# app/services/auditor_service.py
class AuditorService:
    """
    JHONNY_ELITE V16 - Auditor de Resultados
    Clasifica los fallos para recalibrar el sistema (Regla #20).
    """
    
    MOTIVOS_FALLO = [
        "OVER_SIN_REMATES", 
        "GOL_TARDIO_IMPREDECIBLE", 
        "XG_ENGANOSO", 
        "BAJA_INTENSIDAD_POST_SENAL"
    ]

    @staticmethod
    def clasificar_error(match_stats_final):
        # Lógica para detectar por qué falló una señal de OVER
        if match_stats_final['total_shots'] < 5:
            return "OVER_SIN_REMATES"
        return "OTRO"
