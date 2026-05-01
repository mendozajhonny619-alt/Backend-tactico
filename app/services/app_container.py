from __future__ import annotations

from app.fetchers.live_match_fetcher import LiveMatchFetcher

from app.services.runtime_state import RuntimeState
from app.services.scan_service import ScanService
from app.services.live_signal_manager import LiveSignalManager
from app.services.history_service import HistoryService


class AppContainer:
    """
    Contenedor central del sistema.

    Aquí viven las dependencias compartidas:
    - fetcher live
    - scanner
    - runtime state
    - señales activas
    - historial
    """

    def __init__(self) -> None:
        self.runtime_state = RuntimeState()
        self.live_fetcher = LiveMatchFetcher()
        self.scan_service = ScanService()
        self.live_signal_manager = LiveSignalManager()
        self.history_service = HistoryService()


app_container = AppContainer()
