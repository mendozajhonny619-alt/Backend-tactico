from datetime import datetime


class SignalService:
    @staticmethod
    def crear_formato_v16(partido, motores_data):
        tactica = motores_data.get("tactica", {}) or {}
        predictor = motores_data.get("predictor", {}) or {}
        riesgo = motores_data.get("riesgo", {}) or {}
        value_data = motores_data.get("value", {}) or {}

        # 🔥 NUEVO: normalización segura de mercado
        market = str(partido.get("market") or "").upper()

        if "UNDER" in market:
            selection = "Under"
        elif "OVER" in market:
            selection = "Over"
        else:
            selection = partido.get("selection", "Observación")

        output = (
            f"🎯 **JHONNY_ELITE V16 - NUEVA SEÑAL IA**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Liga:** {partido.get('league', 'N/A')} | {partido.get('country', 'N/A')}\n"
            f"⚽ **Partido:** {partido.get('home', 'N/A')} vs {partido.get('away', 'N/A')}\n"
            f"⏰ **Minuto:** {partido.get('minute', 0)}' | **Marcador:** {partido.get('score', '0-0')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Mercado sugerido:** {market or 'NO DEFINIDO'}\n"
            f"✅ **Selección sugerida:** {selection}\n"
            f"📊 **Línea:** {partido.get('line', 'Auto')} | **Referencia:** {partido.get('cuota', 1.80)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **Score IA:** {partido.get('ai_score', 0)}/100\n"
            f"🎯 **Prob. gol:** {partido.get('goal_probability', 0)}%\n"
            f"📈 **Prob. over:** {partido.get('over_probability', 0)}%\n"
            f"🔥 **Momentum:** {partido.get('momentum_label', 'ESTABLE')}\n"
            f"🧠 **Lectura IA:** {tactica.get('match_state', partido.get('match_state', 'N/A'))}\n"
            f"📝 **Razón táctica:** {tactica.get('match_state_reason', partido.get('match_state_reason', 'N/A'))}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **Riesgo numérico:** {partido.get('risk_score', 0)}/10\n"
            f"🛡️ **Riesgo IA:** {partido.get('risk_level', 'MEDIO')}\n"
            f"👑 **Dominancia:** {partido.get('dominance', 'EQUILIBRADO')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🥅 **Tiros al arco:** {partido.get('shots_on_target', 0)}\n"
            f"⚔️ **Ataques peligrosos:** {partido.get('dangerous_attacks', 0)}\n"
            f"🚩 **Corners:** {partido.get('corners', 0)}\n"
            f"📉 **xG estimado:** {partido.get('xG', 0)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔮 **Resultado probable:** {partido.get('result_prediction', '0-0')}\n"
            f"🏁 **Ganador probable:** {partido.get('winner_prediction', 'EMPATE')}\n"
            f"🚨 **Gol inminente:** {'SÍ' if predictor.get('gol_inminente', False) else 'NO'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **RECOMENDACIÓN FINAL:** {partido.get('recomendacion_final', 'ACEPTABLE')}\n"
            f"🧪 **Modo análisis:** IA + estadísticas en vivo\n"
            f"_{datetime.now().strftime('%H:%M:%S')}_"
        )

        return output
