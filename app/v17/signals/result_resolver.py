from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def normalize_market(value: Any) -> str:
    text = str(value or "").upper()
    if "OVER" in text or "SOBRE" in text:
        return "OVER"
    if "UNDER" in text or "BAJO" in text:
        return "UNDER"
    return "OTHER"


class ResultResolver:
    """Resuelve señales live de forma determinista y auditable.

    Reglas:
    - Si existe línea numérica, OVER/UNDER se resuelve contra esa línea.
    - Sin línea, OVER significa "al menos un gol adicional" dentro de la
      ventana de seguimiento; UNDER significa "no más goles" hasta FT.
    - Un UNDER se pierde inmediatamente si aparece un gol adicional.
    - Un OVER se gana inmediatamente cuando el total supera la entrada/línea.
    """

    FINAL_STATUS_SHORT = {"FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"}
    FINAL_STATUS_LONG_HINTS = {
        "MATCH FINISHED", "FINISHED", "AFTER EXTRA TIME", "PENALTY", "CANCELLED", "ABANDONED"
    }

    def resolve(self, tracked: Dict[str, Any], current_match: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(tracked or {})
        match = current_match or {}

        market = normalize_market(
            result.get("market_direction")
            or result.get("market")
            or result.get("official_market")
            or result.get("master_market")
        )

        entry_minute = safe_int(result.get("entry_minute") or result.get("api_minute"), 0)
        current_minute = safe_int(
            match.get("effective_minute")
            or match.get("api_minute")
            or match.get("minute")
            or match.get("minuto"),
            entry_minute,
        )
        entry_home = safe_int(result.get("entry_home_score"), safe_int(result.get("home_score"), 0))
        entry_away = safe_int(result.get("entry_away_score"), safe_int(result.get("away_score"), 0))
        current_home = safe_int(match.get("home_score") or match.get("local_score"), entry_home)
        current_away = safe_int(match.get("away_score") or match.get("visitante_score"), entry_away)

        entry_total = safe_int(result.get("entry_total_goals"), entry_home + entry_away)
        current_total = current_home + current_away
        goals_after_entry = current_total - entry_total
        line = self._extract_line(result)
        finished = self._is_finished(match)
        cancelled = self._is_cancelled(match)

        result.update({
            "market": market,
            "market_direction": market,
            "current_minute": current_minute,
            "current_home_score": current_home,
            "current_away_score": current_away,
            "current_score": f"{current_home}-{current_away}",
            "current_total_goals": current_total,
            "goals_after_entry": goals_after_entry,
            "resolved": False,
            "last_seen_at": utc_now_iso(),
        })

        if cancelled:
            return self._close(result, "VOID", "PARTIDO_CANCELADO_O_ABANDONADO")

        if market == "OVER":
            return self._resolve_over(result, line, entry_total, current_total, current_minute, entry_minute, finished)

        if market == "UNDER":
            return self._resolve_under(result, line, entry_total, current_total, finished)

        if finished:
            return self._close(result, "VOID", "MERCADO_NO_RECONOCIDO")

        result["pending_reason"] = "WAITING_MARKET_RESOLUTION"
        return result

    def _resolve_over(
        self,
        result: Dict[str, Any],
        line: Optional[float],
        entry_total: int,
        current_total: int,
        current_minute: int,
        entry_minute: int,
        finished: bool,
    ) -> Dict[str, Any]:
        if line is not None:
            if current_total > line:
                return self._close(result, "WON", f"OVER_{line:g}_CUMPLIDO")
            if finished and current_total == line and float(line).is_integer():
                return self._close(result, "VOID", f"OVER_{line:g}_PUSH")
            if finished:
                return self._close(result, "LOST", f"OVER_{line:g}_NO_CUMPLIDO")
            result["pending_reason"] = f"WAITING_OVER_{line:g}"
            return result

        # Sin línea explícita: oportunidad de próximo gol.
        if current_total > entry_total:
            return self._close(result, "WON", "GOL_POSTERIOR_A_LA_SENAL_OVER")

        max_follow = max(5, safe_int(result.get("max_follow_minutes"), 20))
        if finished:
            return self._close(result, "LOST", "FINAL_SIN_GOL_ADICIONAL")
        if entry_minute > 0 and current_minute >= entry_minute + max_follow:
            return self._close(result, "LOST", "VENTANA_OVER_AGOTADA_SIN_GOL")

        result["pending_reason"] = "WAITING_NEXT_GOAL"
        return result

    def _resolve_under(
        self,
        result: Dict[str, Any],
        line: Optional[float],
        entry_total: int,
        current_total: int,
        finished: bool,
    ) -> Dict[str, Any]:
        if line is not None:
            if current_total > line:
                return self._close(result, "LOST", f"UNDER_{line:g}_SUPERADO")
            if finished and current_total == line and float(line).is_integer():
                return self._close(result, "VOID", f"UNDER_{line:g}_PUSH")
            if finished:
                return self._close(result, "WON", f"UNDER_{line:g}_CUMPLIDO")
            result["pending_reason"] = f"WAITING_FT_UNDER_{line:g}"
            return result

        # Predicción SCORE_HOLD: cualquier gol adicional rompe el escenario principal.
        if current_total > entry_total:
            return self._close(result, "LOST", "GOL_ADICIONAL_ROMPIO_SCORE_HOLD")
        if finished:
            return self._close(result, "WON", "MARCADOR_SE_MANTUVO_HASTA_EL_FINAL")

        result["pending_reason"] = "WAITING_FT_SCORE_HOLD"
        return result

    def _close(self, payload: Dict[str, Any], status: str, reason: str) -> Dict[str, Any]:
        payload["resolved"] = True
        payload["tracking_status"] = "CLOSED"
        payload["result_status"] = status
        payload["result_label"] = {
            "WON": "ACIERTO",
            "LOST": "FALLO",
            "VOID": "ANULADA",
        }.get(status, status)
        payload["result_reason"] = reason
        payload["result_explanation"] = reason.replace("_", " ").capitalize()
        payload["resolved_at"] = utc_now_iso()
        return payload

    def _extract_line(self, payload: Dict[str, Any]) -> Optional[float]:
        for key in ("line", "market_line", "bet_line", "total_line", "official_line"):
            value = payload.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, (int, float)):
                return float(value)
            match = re.search(r"(\d+(?:[\.,]\d+)?)", str(value))
            if match:
                try:
                    return float(match.group(1).replace(",", "."))
                except Exception:
                    pass
        return None

    def _is_finished(self, match: Dict[str, Any]) -> bool:
        short = str(match.get("status_short") or match.get("short_status") or match.get("status") or "").upper()
        long = str(match.get("status_long") or match.get("long_status") or "").upper()
        if short in self.FINAL_STATUS_SHORT:
            return True
        return any(x in long for x in self.FINAL_STATUS_LONG_HINTS)

    def _is_cancelled(self, match: Dict[str, Any]) -> bool:
        short = str(match.get("status_short") or match.get("status") or "").upper()
        long = str(match.get("status_long") or "").upper()
        return short in {"CANC", "ABD", "AWD", "WO", "PST"} or any(
            x in long for x in {"CANCELLED", "ABANDONED", "POSTPONED", "WALKOVER"}
        )
