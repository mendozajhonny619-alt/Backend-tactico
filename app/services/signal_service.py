from datetime import datetime

class SignalService:
    @staticmethod
    def crear_formato_v16(partido, motores_data):
        t = motores_data

        output = (
            f"🎯 **JHONNY_ELITE V16 - NUEVA SEÑAL**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Liga:** {partido.get('league')} | {partido.get('country')}\n"
            f"⚽ **Partido:** {partido.get('home')} vs {partido.get('away')}\n"
            f"⏰ **Minuto:** {partido.get('minute')}' | **Marcador:** {partido.get('score')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Mercado:** {partido.get('market')}\n"
            f"✅ **Selección:** {partido.get('selection')}\n"
            f"📊 **Línea:** {partido.get('line')} | **Cuota:** {partido.get('cuota')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Confianza:** {partido.get('confidence')}% | **Riesgo:** {partido.get('risk_score')}/10\n"
            f"💎 **Value:** {t.get('value', {}).get('value_category', 'N/A')} (Edge: {t.get('value', {}).get('edge', 0)})\n"
            f"🔥 **Lectura IA:** {t.get('tactica', {}).get('match_state', 'N/A')}\n"
            f"📝 **Razón Táctica:** {t.get('tactica', {}).get('match_state_reason', 'N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **RECOMENDACIÓN:** {partido.get('recomendacion_final')}\n"
            f"Validado por The Odds API ✅\n"
            f"_{datetime.now().strftime('%H:%M:%S')}_"
        )
        return output
