# app/services/notifier_service.py
import requests
import os
import logging

class NotifierService:
    """
    JHONNY_ELITE V16 - Mensajería y Alertas
    Envía las señales validadas a los canales oficiales.
    """
    TOKEN = os.getenv("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "TU_CHAT_ID_AQUI")

    @staticmethod
    def send_telegram_signal(message):
        if not NotifierService.TOKEN or not NotifierService.CHAT_ID:
            logging.warning("Telegram no configurado. Señal impresa en consola.")
            return
            
        url = f"https://api.telegram.org/bot{NotifierService.TOKEN}/sendMessage"
        payload = {
            "chat_id": NotifierService.CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logging.error(f"Error enviando a Telegram: {e}")
