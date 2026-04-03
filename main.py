# main.py (VERSIÓN FINAL INTEGRADA V16)
import time
import logging
from app.services.scan_service import ScanService
from app.services.signal_service import SignalService
from app.services.notifier_service import NotifierService
from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.fetchers.odds_fetcher import OddsFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - JHONNY_ELITE_V16 - %(message)s')

def iniciar_sistema():
    # Inicialización de componentes
    scanner = ScanService()
    football_api = LiveMatchFetcher()
    odds_api = OddsFetcher()
    
    logging.info("SISTEMA JHONNY_ELITE V16 - EN LÍNEA Y OPERATIVO")

    while True:
        try:
            logging.info("Iniciando nuevo ciclo de escaneo profundo...")
            
            # 1. Obtener datos reales
            live_matches = football_api.fetch_live_data()
            live_odds = odds_api.get_live_odds()
            
            if not live_matches:
                logging.info("No se detectaron partidos en vivo elegibles.")
            else:
                # 2. Procesar con los Motores V16
                signals = scanner.escanear_partidos(live_matches, live_odds)
                
                # 3. Notificar señales de alta confianza
                for signal in signals:
                    msg = SignalService.crear_formato_v16(signal['match'], signal['motores'])
                    NotifierService.send_telegram_signal(msg)
                    logging.info(f"SEÑAL EMITIDA: {signal['match']['home']} vs {signal['match']['away']}")

            # 4. Respetar cadencia de APIs (60 seg)
            time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Sistema apagado manualmente.")
            break
        except Exception as e:
            logging.error(f"FALLO CRÍTICO EN CICLO: {e}")
            time.sleep(30)

if __name__ == "__main__":
    iniciar_sistema()
