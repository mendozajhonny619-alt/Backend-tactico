from __future__ import annotations

from typing import Any, Dict, List


class SignalPerformanceAnalyzer:
    """
    Analiza el rendimiento real de señales cerradas.

    No bloquea señales.
    No modifica decisiones.
    Solo entrega lectura estadística para saber:
    - dónde gana más el sistema
    - dónde falla más
    - qué ligas/mercados/minutos/rangos son mejores
    """

    def analyze(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        history = [x for x in history or [] if isinstance(x, dict)]

        closed = [
            x for x in history
            if str(x.get("status") or x.get("resultado") or "").upper() in {"WIN", "LOSS"}
        ]

        wins = sum(1 for x in closed if self._status(x) == "WIN")
        losses = sum(1 for x in closed if self._status(x) == "LOSS")
        total = wins + losses

        return {
            "summary": {
                "total_closed": total,
                "wins": wins,
                "losses": losses,
                "winrate": self._winrate(wins, losses),
            },
            "by_league": self._group_by(closed, "league"),
            "by_market": self._group_by(closed, "market"),
            "by_rank": self._group_by(closed, "rank"),
            "by_minute_range": self._group_by_minute_range(closed),
            "best_patterns": self._best_patterns(closed),
            "danger_patterns": self._danger_patterns(closed),
        }

    def _group_by(self, history: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in history:
            key = str(item.get(field) or "UNKNOWN").upper()
            status = self._status(item)

            if key not in grouped:
                grouped[key] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0.0,
                }

            grouped[key]["total"] += 1

            if status == "WIN":
                grouped[key]["wins"] += 1
            elif status == "LOSS":
                grouped[key]["losses"] += 1

        for key, stats in grouped.items():
            stats["winrate"] = self._winrate(stats["wins"], stats["losses"])

        return grouped

    def _group_by_minute_range(self, history: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in history:
            minute = self._safe_int(
                item.get("entry_minute")
                or item.get("minute")
                or item.get("final_minute")
            )

            bucket = self._minute_bucket(minute)
            status = self._status(item)

            if bucket not in grouped:
                grouped[bucket] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0.0,
                }

            grouped[bucket]["total"] += 1

            if status == "WIN":
                grouped[bucket]["wins"] += 1
            elif status == "LOSS":
                grouped[bucket]["losses"] += 1

        for key, stats in grouped.items():
            stats["winrate"] = self._winrate(stats["wins"], stats["losses"])

        return grouped

    def _best_patterns(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        patterns = self._build_patterns(history)

        return [
            item for item in patterns
            if item["total"] >= 3 and item["winrate"] >= 70
        ][:10]

    def _danger_patterns(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        patterns = self._build_patterns(history)

        return [
            item for item in patterns
            if item["total"] >= 3 and item["winrate"] <= 50
        ][:10]

    def _build_patterns(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in history:
            league = str(item.get("league") or "UNKNOWN").upper()
            market = str(item.get("market") or "UNKNOWN").upper()
            rank = str(item.get("rank") or "UNKNOWN").upper()
            minute = self._safe_int(item.get("entry_minute") or item.get("minute"))
            bucket = self._minute_bucket(minute)

            key = f"{league} | {market} | {rank} | {bucket}"
            status = self._status(item)

            if key not in grouped:
                grouped[key] = {
                    "pattern": key,
                    "league": league,
                    "market": market,
                    "rank": rank,
                    "minute_range": bucket,
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0.0,
                }

            grouped[key]["total"] += 1

            if status == "WIN":
                grouped[key]["wins"] += 1
            elif status == "LOSS":
                grouped[key]["losses"] += 1

        patterns = list(grouped.values())

        for item in patterns:
            item["winrate"] = self._winrate(item["wins"], item["losses"])

        patterns.sort(
            key=lambda x: (x["winrate"], x["total"]),
            reverse=True,
        )

        return patterns

    def _status(self, item: Dict[str, Any]) -> str:
        return str(item.get("status") or item.get("resultado") or "").upper()

    def _minute_bucket(self, minute: int) -> str:
        if minute <= 0:
            return "UNKNOWN"
        if minute <= 15:
            return "00-15"
        if minute <= 30:
            return "16-30"
        if minute <= 45:
            return "31-45"
        if minute <= 60:
            return "46-60"
        if minute <= 75:
            return "61-75"
        if minute <= 90:
            return "76-90"
        return "90+"

    def _winrate(self, wins: int, losses: int) -> float:
        total = wins + losses
        return round((wins / total) * 100, 2) if total else 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except Exception:
            return 0
