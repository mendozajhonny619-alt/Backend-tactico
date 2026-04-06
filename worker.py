import time
import logging
from dotenv import load_dotenv

load_dotenv()

from app.services.scan_service import ScanService
from app.services.signal_service import SignalService
from app.services.history_service import HistoryService
from app.services.live_signal_manager import LiveSignalManager
from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.fetchers.odds_fetcher import OddsFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - JHONNY_ELITE_V16 - %(levelname)s - %(message)s"
)

def iniciar_worker():
    scanner = ScanService()
    football_api = LiveMatchFetcher()
    odds_api = OddsFetcher()

    logging.info("WORKER JHONNY_ELITE V16 INICIADO")

    while True:
        try:
            logging.info("Nuevo ciclo de escaneo...")

            live_matches = football_api.fetch_live_data()
            live_odds = odds_api.get_live_odds()

            logging.info(f"Partidos en vivo detectados: {len(live_matches)}")
            logging.info(f"Partidos con odds detectados: {len(live_odds)}")

            if not live_matches:
                logging.info("No hay partidos elegibles en este ciclo.")
            else:
                signals_raw = scanner.escanear_partidos(live_matches, live_odds)
                signals = LiveSignalManager.actualizar_signales(signals_raw, live_matches)

                logging.info(f"Señales activas detectadas: {len(signals)}")

                for signal in signals:
                    msg = SignalService.crear_formato_v16(signal["match"], signal["motores"])
                    print(msg)
                    HistoryService.registrar_senal(signal["match"], signal["motores"])

                    logging.info(
                        f"SEÑAL ACTIVA: {signal['match'].get('home')} vs {signal['match'].get('away')} "
                        f"| Score: {signal['match'].get('signal_score')} "
                        f"| Rank: {signal['match'].get('signal_rank')}"
                    )

            time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Worker detenido manualmente.")
            break
        except Exception as e:
            logging.exception(f"FALLO CRÍTICO EN WORKER: {e}")
            time.sleep(30)

if __name__ == "__main__":
    iniciar_worker()
