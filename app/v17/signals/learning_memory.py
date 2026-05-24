from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Dict, List


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class LearningMemory:
    """
    Memoria de aprendizaje V17.

    No solo cuenta aciertos y fallos.
    También explica por qué falló una señal.
    """

    def __init__(self, max_records: int = 500) -> None:
        self.max_records = max_records
        self._records: List[Dict[str, Any]] = []

    def add_result(self, resolved_signal: Dict[str, Any]) -> None:
        if not isinstance(resolved_signal, dict):
            return

        status = str(resolved_signal.get("result_status") or "").upper()

        if status not in {"WON", "LOST", "VOID"}:
            return

        signal_key = resolved_signal.get("signal_key") or resolved_signal.get("signal_id")

        if signal_key:
            for record in self._records:
                if record.get("signal_key") == signal_key:
                    record.update(deepcopy(resolved_signal))
                    return

        self._records.insert(0, deepcopy(resolved_signal))
        self._records = self._records[: self.max_records]

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return deepcopy(self._records[:limit])

    def summary(self) -> Dict[str, Any]:
        total = len(self._records)
        wins = sum(1 for x in self._records if x.get("result_status") == "WON")
        losses = sum(1 for x in self._records if x.get("result_status") == "LOST")
        voids = sum(1 for x in self._records if x.get("result_status") == "VOID")

        precision = round((wins / max(1, wins + losses)) * 100, 2)

        failure_reasons = Counter(
            x.get("result_reason")
            for x in self._records
            if x.get("result_status") == "LOST"
        )

        market_counter = Counter(x.get("market") for x in self._records)
        league_counter = Counter(x.get("league") for x in self._records)

        return {
            "total_closed": total,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "precision": precision,
            "top_failure_reasons": [
                {"reason": reason, "count": count}
                for reason, count in failure_reasons.most_common(10)
                if reason
            ],
            "by_market": dict(market_counter),
            "by_league": dict(league_counter),
        }

    def performance_analysis(self) -> Dict[str, Any]:
        by_market = defaultdict(lambda: {"wins": 0, "losses": 0, "voids": 0})
        by_reason = Counter()
        by_league = defaultdict(lambda: {"wins": 0, "losses": 0, "voids": 0})

        for item in self._records:
            market = str(item.get("market") or "UNKNOWN")
            league = str(item.get("league") or "UNKNOWN")
            status = str(item.get("result_status") or "").upper()

            if status == "WON":
                by_market[market]["wins"] += 1
                by_league[league]["wins"] += 1
            elif status == "LOST":
                by_market[market]["losses"] += 1
                by_league[league]["losses"] += 1
                by_reason[item.get("result_reason") or "UNKNOWN"] += 1
            elif status == "VOID":
                by_market[market]["voids"] += 1
                by_league[league]["voids"] += 1

        return {
            "market_performance": self._with_precision(by_market),
            "league_performance": self._with_precision(by_league),
            "failure_reasons": [
                {"reason": reason, "count": count}
                for reason, count in by_reason.most_common(10)
            ],
            "recommendation": self._build_recommendation(by_reason),
        }

    def _with_precision(self, data: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}

        for key, value in data.items():
            wins = value.get("wins", 0)
            losses = value.get("losses", 0)
            total_valid = wins + losses
            precision = round((wins / max(1, total_valid)) * 100, 2)

            result[key] = {
                **value,
                "precision": precision,
                "total_valid": total_valid,
            }

        return result

    def _build_recommendation(self, by_reason: Counter) -> str:
        if not by_reason:
            return "Todavía no hay suficientes fallos cerrados para generar aprendizaje."

        top_reason, count = by_reason.most_common(1)[0]

        if top_reason == "OVER_SIN_TIRO_AL_ARCO":
            return "Ajustar el filtro OVER para exigir más tiros al arco recientes antes de publicar."

        if top_reason == "PRESION_FALSA":
            return "Fortalecer el detector de presión falsa y exigir profundidad ofensiva real."

        if top_reason == "MINUTO_ATRASADO":
            return "Endurecer el ClockGuard y evitar cierre de señales con datos atrasados."

        if top_reason == "CONMEBOL_SIN_CONFIRMACION":
            return "Exigir confirmación extra en CONMEBOL, especialmente después del minuto 70."

        if top_reason == "RETENCION_NO_SUPERADA":
            return "Reducir señales OVER cuando el score_hold_probability sea alto."

        if top_reason == "TRANSICION_UNDER_NO_DETECTADA":
            return "Mejorar la transición de OVER a UNDER cuando el ritmo cae."

        return f"Revisar el patrón de fallo más frecuente: {top_reason}."
