from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.services.scan_service import ScanService
from app.services.live_signal_manager import LiveSignalManager

live_fetcher = LiveMatchFetcher()
scan_service = ScanService()
live_signal_manager = LiveSignalManager()
