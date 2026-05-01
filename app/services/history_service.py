from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List


class HistoryService:
    """
    Historial de señales.

    Corrección aplicada:
    - signal_key estable: match_id:market
    - no usa match_name como fallback para evitar duplicados
    - update_result devuelve True/False
    - no permite que extra cambie la signal_key
    - mantiene logos/banderas
    """

    MAX_HISTORY_ITEMS = 300

    TEAM_LOGOS = {
        "Toluca": "https://media.api-sports.io/football/teams/2289.png",
        "León": "https://media.api-sports.io/football/teams/2287.png",
        "Club León": "https://media.api-sports.io/football/teams/2287.png",
        "Guadalajara Chivas": "https://media.api-sports.io/football/teams/2278.png",
        "Chivas": "https://media.api-sports.io/football/teams/2278.png",
        "Club Tijuana": "https://media.api-sports.io/football/teams/2285.png",
        "Tijuana": "https://media.api-sports.io/football/teams/2285.png",
        "River Plate": "https://media.api-sports.io/football/teams/435.png",
        "San Lorenzo": "https://media.api-sports.io/football/teams/458.png",
        "Platense": "https://media.api-sports.io/football/teams/1064.png",
        "Juventus": "https://media.api-sports.io/football/teams/496.png",
        "Roma": "https://media.api-sports.io/football/teams/497.png",
        "Real Madrid": "https://media.api-sports.io/football/teams/541.png",
        "Girona": "https://media.api-sports.io/football/teams/547.png",
        "Liverpool": "https://media.api-sports.io/football/teams/40.png",
        "Aston Villa": "https://media.api-sports.io/football/teams/66.png",
    }

    COUNTRY_FLAGS = {
        "Argentina": "https://media.api-sports.io/flags/ar.svg",
        "México": "https://media.api-sports.io/flags/mx.svg",
        "Mexico": "https://media.api-sports.io/flags/mx.svg",
        "EE.UU.": "https://media.api-sports.io/flags/us.svg",
        "Estados Unidos": "https://media.api-sports.io/flags/us.svg",
        "USA": "https://media.api-sports.io/flags/us.svg",
        "Brasil": "https://media.api-sports.io/flags/br.svg",
        "Brazil": "https://media.api-sports.io/flags/br.svg",
        "España": "https://media.api-sports.io/flags/es.svg",
        "Spain": "https://media.api-sports.io/flags/es.svg",
        "Italia": "https://media.api-sports.io/flags/it.svg",
        "Italy": "https://media.api-sports.io/flags/it.svg",
        "Inglaterra": "https://media.api-sports.io/flags/gb.svg",
        "England": "https://media.api-sports.io/flags/gb.svg",
        "Chile": "https://media.api-sports.io/flags/cl.svg",
        "Colombia": "https://media.api-sports.io/flags/co.svg",
        "Paraguay": "https://media.api-sports.io/flags/py.svg",
        "Perú": "https://media.api-sports.io/flags/pe.svg",
        "Peru": "https://media.api-sports.io/flags/pe.svg",
        "Uruguay": "https://media.api-sports.io/flags/uy.svg",
    }

    LEAGUE_LOGOS = {
        "Liga MX": "https://media.api-sports.io/football/leagues/262.png",
        "Liga Profesional Argentina": "https://media.api-sports.io/football/leagues/128.png",
        "NWSL Women": "https://media.api-sports.io/football/leagues/254.png",
        "Premier League": "https://media.api-sports.io/football/leagues/39.png",
        "Serie A": "https://media.api-sports.io/football/leagues/135.png",
        "La Liga": "https://media.api-sports.io/football/leagues/140.png",
        "LaLiga": "https://media.api-sports.io/football/leagues/140.png",
        "MLS": "https://media.api-sports.io/football/leagues/253.png",
        "Liga Mayor de Fútbol": "https://media.api-sports.io/football/leagues/253.png",
    }

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []
        self._published_count: int = 0

    def register_published_signal(self, signal: Dict[str, Any]) -> bool:
        if not isinstance(signal, dict):
            return False

        signal = self._enrich_visual_assets(signal)
        signal_key = self._get_signal_key(signal)

        for item in self._history:
            if str(item.get("signal_key") or "").strip().upper() == signal_key:
                return False

        record = deepcopy(signal)
        record["signal_key"] = signal_key
        record["history_status"] = record.get("history_status") or "PUBLISHED"
        record["status"] = record.get("status") or "PENDIENTE"
        record["resultado"] = record.get("resultado") or "PENDIENTE"
        record["created_at"] = (
            record.get("created_at")
            or datetime.now().isoformat(timespec="seconds")
        )
        record["closed_at"] = record.get("closed_at") if record.get("closed_at") else None

        self._history.insert(0, record)
        self._published_count += 1
        self._trim_history()
        return True

    def update_result(
        self,
        signal_key: str,
        result: str,
        extra: Dict[str, Any] | None = None,
    ) -> bool:
        normalized_key = str(signal_key or "").strip().upper()
        normalized_result = str(result or "PENDIENTE").strip().upper()

        if not normalized_key:
            return False

        for item in self._history:
            item_key = str(item.get("signal_key") or "").strip().upper()

            if item_key == normalized_key:
                if item.get("history_status") == "CLOSED":
                    return True

                if extra:
                    enriched = self._enrich_visual_assets(extra)
                    enriched["signal_key"] = normalized_key
                    item.update(enriched)

                item["signal_key"] = normalized_key
                item["status"] = normalized_result
                item["resultado"] = normalized_result
                item["history_status"] = "CLOSED"
                item["closed_at"] = datetime.now().isoformat(timespec="seconds")

                return True

        return False

    def register_closed_signal(
        self,
        signal: Dict[str, Any],
        result: str | None = None,
    ) -> bool:
        if not isinstance(signal, dict):
            return False

        record = self._enrich_visual_assets(signal)
        signal_key = self._get_signal_key(record)
        final_result = str(
            result
            or record.get("resultado")
            or record.get("status")
            or "PENDIENTE"
        ).upper()

        updated = self.update_result(
            signal_key=signal_key,
            result=final_result,
            extra=record,
        )

        if updated:
            return True

        record["signal_key"] = signal_key
        record["status"] = final_result
        record["resultado"] = final_result
        record["history_status"] = "CLOSED"
        record["created_at"] = (
            record.get("created_at")
            or record.get("activated_at")
            or datetime.now().isoformat(timespec="seconds")
        )
        record["closed_at"] = (
            record.get("closed_at")
            or datetime.now().isoformat(timespec="seconds")
        )

        self._history.insert(0, record)
        self._trim_history()
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        return [self._enrich_visual_assets(x) for x in deepcopy(self._history)]

    def get_last(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [self._enrich_visual_assets(x) for x in deepcopy(self._history[:limit])]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)

        wins = sum(1 for x in self._history if str(x.get("resultado")).upper() == "WIN")
        losses = sum(1 for x in self._history if str(x.get("resultado")).upper() == "LOSS")
        pending = sum(
            1 for x in self._history if str(x.get("resultado")).upper() == "PENDIENTE"
        )

        settled = wins + losses
        winrate = (wins / settled * 100) if settled > 0 else 0.0

        return {
            "history_items": total,
            "published_signals_total": self._published_count,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "settled": settled,
            "winrate": round(winrate, 2),
        }

    def _get_signal_key(self, signal: Dict[str, Any]) -> str:
        # Si ya viene con key, la respetamos solo si tiene formato estable.
        raw_key = signal.get("signal_key")

        if raw_key:
            text = str(raw_key).strip().upper()
            parts = text.split(":")
            if len(parts) >= 2:
                return f"{parts[0]}:{parts[1]}"

        return self._build_key(signal)

    def _build_key(self, signal: Dict[str, Any]) -> str:
        match_id = signal.get("match_id")
        market = signal.get("market") or "SIGNAL"

        if match_id is None:
            match_id = "UNKNOWN"

        return f"{str(match_id).strip()}:{str(market).strip().upper()}"

    def _trim_history(self) -> None:
        if len(self._history) > self.MAX_HISTORY_ITEMS:
            self._history = self._history[: self.MAX_HISTORY_ITEMS]

    def _enrich_visual_assets(self, item: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(item)

        home = (
            data.get("home_name")
            or data.get("nombre_local")
            or data.get("home")
            or data.get("local")
        )

        away = (
            data.get("away_name")
            or data.get("nombre_visitante")
            or data.get("away")
            or data.get("visitante")
        )

        league = data.get("league") or data.get("liga")
        country = data.get("country") or data.get("pais") or data.get("país")

        data["home_name"] = home
        data["away_name"] = away
        data["home"] = home
        data["away"] = away
        data["league"] = league
        data["country"] = country

        data["home_logo"] = (
            data.get("home_logo")
            or data.get("home_team_logo")
            or data.get("local_logo")
            or self._find_team_logo(home)
        )

        data["away_logo"] = (
            data.get("away_logo")
            or data.get("away_team_logo")
            or data.get("visitor_logo")
            or self._find_team_logo(away)
        )

        data["league_logo"] = (
            data.get("league_logo")
            or data.get("competition_logo")
            or self._find_league_logo(league)
        )

        data["country_flag"] = (
            data.get("country_flag")
            or data.get("flag")
            or data.get("league_flag")
            or self._find_country_flag(country)
        )

        return data

    def _find_team_logo(self, team_name: Any) -> str | None:
        if not team_name:
            return None

        text = str(team_name).strip().lower()

        for name, logo in self.TEAM_LOGOS.items():
            key = name.lower()
            if text == key or key in text or text in key:
                return logo

        return None

    def _find_league_logo(self, league_name: Any) -> str | None:
        if not league_name:
            return None

        text = str(league_name).strip().lower()

        for name, logo in self.LEAGUE_LOGOS.items():
            key = name.lower()
            if text == key or key in text or text in key:
                return logo

        return None

    def _find_country_flag(self, country_name: Any) -> str | None:
        if not country_name:
            return None

        text = str(country_name).strip().lower()

        for name, flag in self.COUNTRY_FLAGS.items():
            key = name.lower()
            if text == key or key in text or text in key:
                return flag

        return None
