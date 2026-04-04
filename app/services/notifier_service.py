import os
import logging
import requests

class NotifierService:
    TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    @staticmethod
    def send_telegram_signal(message):
        if NotifierService.TOKEN in ("", "TU_TOKEN_AQUI", "tu_bot_token_aqui"):
            logging.warning("TELEGRAM_TOKEN no configurado. Señal no enviada.")
            return

        if NotifierService.CHAT_ID in ("", "TU_CHAT_ID_AQUI", "tu_chat_id_aqui"):
            logging.warning("TELEGRAM_CHAT_ID no configurado. Señal no enviada.")
            return

        url = f"https://api.telegram.org/bot{NotifierService.TOKEN}/sendMessage"
        payload = {
            "chat_id": NotifierService.CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logging.error(f"Telegram respondió con status {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"Error enviando a Telegram: {e}")
