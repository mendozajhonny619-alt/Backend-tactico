# app/services/signal_service.py
from datetime import datetime

class SignalService:
    """
    JHONNY_ELITE V16 - Servicio de Formateo de Señales
    Sigue el formato del Punto 18 del Protocolo.
    """

    @staticmethod
    def crear_formato_v16(partido, motores_data):
        """
        Genera la estructura oficial para ser enviada al Notificador.
        """
        t = motores_data # Alias corto para legibilidad
        
        output = (
            f"🎯 **JHONNY_ELITE V16 - NUEVA SEÑAL**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Liga:** {partido.get('league')} | {partido.get('country')}\n"
            f"⚽ **Partido:** {partido.get('home')} vs {partido.get('away')}\n"
            f"⏰ **Minuto:** {partido.get('minute')}'  |  **Marcador:** {partido.get('score')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Mercado:** {partido.get('market')}\n"
            f"✅ **Selección:** {partido.get('selection')}\n"
            f"📊 **Línea:** {partido.get('line')}  |  **Cuota:** {partido.get('cuota')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Confianza:** {partido.get('confidence')}% | **Riesgo:** {partido.get('risk_score')}/10\n"
            f"💎 **Value:** {t['value']['value_category']} (Edge: {t['value']['edge']})\n"
            f"🔥 **Lectura IA:** {t['tactica']['match_state']}\n"
            f"📝 **Razón Táctica:** {t['tactica']['match_state_reason']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **RECOMENDACIÓN:** {partido.get('recomendacion_final')}\n"
            f"Validado por The Odds API ✅\n"
            f"_{datetime.now().strftime('%H:%M:%S')}_"
        )
        return output
