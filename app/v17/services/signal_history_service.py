from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def normalize_text(value: Any) -> str:
    return str(value or "").strip().upper()


class SignalHistoryService:
    """
    Servicio persistente de historial de señales V17.

    Objetivo:
    - Guardar señales detectadas.
    - Mantener candidatos fuertes aunque no sean señal principal.
    - Mantener señales principales y top signals.
    - Evitar que las señales desaparezcan del panel de resultados.
    - Actualizar una misma señal cuando evoluciona de observación a candidato fuerte o señal principal.
    - Dejar base para evaluar aciertos y fallos cuando el partido termine.

    Este servicio no decide señales.
    Solo registra, actualiza y devuelve historial.
    """

    VERSION = "V17_SIGNAL_HISTORY_SERVICE_1"

    STORAGE_DIR = Path("app/v17/storage")
    STORAGE_FILE = STORAGE_DIR / "signal_history.json"

    LEVEL_PRIORITY = {
        "BLOCKED": 0,
        "OBSERVE_ONLY": 10,
        "WAIT_REVALIDATION": 20,
        "OBSERVATION": 25,
        "STRONG_CANDIDATE": 50,
        "MAIN_SIGNAL": 80,
        "TOP_SIGNAL": 100,
    }

    RESULT_PENDING = "PENDING"
    RESULT_WON = "WON"
    RESULT_LOST = "LOST"
    RESULT_EXPIRED = "EXPIRED"
    RESULT_CANCELLED = "CANCELLED"
    RESULT_UNKNOWN = "UNKNOWN"

    def __init__(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()

    def register_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra o actualiza una señal.

        Se guarda desde observación si tiene lectura relevante, pero para el panel
        de resultados se priorizan candidatos fuertes, señales principales y top signals.
        """

        if not isinstance(signal, dict):
            return {
                "history_ok": False,
                "history_error": "INVALID_SIGNAL",
            }

        if not self._should_store(signal):
            return {
                "history_ok": True,
                "history_action": "IGNORED_NOT_RELEVANT",
                "history_signal_id": None,
            }

        data = self._load()
        records = data.get("records", [])

        signal_id = self._build_history_id(signal)
        now = utc_now_iso()

        existing = self._find_record(records, signal_id)

        if existing is None:
            record = self._create_record(signal=signal, signal_id=signal_id, now=now)
            records.append(record)

            data["records"] = records
            data["updated_at"] = now
            self._save(data)

            return {
                "history_ok": True,
                "history_action": "CREATED",
                "history_signal_id": signal_id,
                "history_record": record,
            }

        updated = self._update_record(existing=existing, signal=signal, now=now)

        data["records"] = records
        data["updated_at"] = now
        self._save(data)

        return {
            "history_ok": True,
            "history_action": "UPDATED",
            "history_signal_id": signal_id,
            "history_record": updated,
        }

    def get_results(
        self,
        limit: int = 100,
        include_observation: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve resultados visibles para el panel.

        Por defecto no muestra observaciones simples, para que la sección RESULTADOS
        no se llene de señales débiles.
        """

        data = self._load()
        records = data.get("records", [])

        visible: List[Dict[str, Any]] = []

        for record in records:
            best_level = normalize_text(record.get("best_promotion_level"))

            if include_observation:
                visible.append(record)
                continue

            if best_level in {"STRONG_CANDIDATE", "MAIN_SIGNAL", "TOP_SIGNAL"}:
                visible.append(record)

        visible.sort(
            key=lambda item: (
                self.LEVEL_PRIORITY.get(normalize_text(item.get("best_promotion_level")), 0),
                str(item.get("last_seen_at") or ""),
            ),
            reverse=True,
        )

        return visible[:limit]

    def get_full_history(self, limit: int = 200) -> List[Dict[str, Any]]:
        data = self._load()
        records = data.get("records", [])

        records.sort(
            key=lambda item: str(item.get("last_seen_at") or ""),
            reverse=True,
        )

        return records[:limit]

    def get_summary(self) -> Dict[str, Any]:
        data = self._load()
        records = data.get("records", [])

        summary = {
            "total_records": len(records),
            "pending": 0,
            "won": 0,
            "lost": 0,
            "expired": 0,
            "cancelled": 0,
            "unknown": 0,
            "strong_candidates": 0,
            "main_signals": 0,
            "top_signals": 0,
            "observations": 0,
        }

        for record in records:
            result_status = normalize_text(record.get("result_status"))
            best_level = normalize_text(record.get("best_promotion_level"))

            if result_status == self.RESULT_PENDING:
                summary["pending"] += 1
            elif result_status == self.RESULT_WON:
                summary["won"] += 1
            elif result_status == self.RESULT_LOST:
                summary["lost"] += 1
            elif result_status == self.RESULT_EXPIRED:
                summary["expired"] += 1
            elif result_status == self.RESULT_CANCELLED:
                summary["cancelled"] += 1
            else:
                summary["unknown"] += 1

            if best_level == "TOP_SIGNAL":
                summary["top_signals"] += 1
            elif best_level == "MAIN_SIGNAL":
                summary["main_signals"] += 1
            elif best_level == "STRONG_CANDIDATE":
                summary["strong_candidates"] += 1
            else:
                summary["observations"] += 1

        return summary

    def _should_store(self, signal: Dict[str, Any]) -> bool:
        market = self._detect_market(signal)
        promotion_level = normalize_text(signal.get("promotion_level"))
        master_status = normalize_text(signal.get("master_status"))
        candidate_level = normalize_text(signal.get("candidate_level"))
        panel_signal_type = normalize_text(signal.get("panel_signal_type"))
        can_publish = bool(signal.get("can_publish"))
        should_observe = bool(signal.get("should_observe"))

        if market not in {"OVER", "UNDER"}:
            return False

        if promotion_level in {
            "OBSERVE_ONLY",
            "WAIT_REVALIDATION",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            return True

        if master_status in {
            "OBSERVE",
            "WAIT_REVALIDATION",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            return True

        if candidate_level or panel_signal_type:
            return True

        if can_publish or should_observe:
            return True

        return False

    def _create_record(
        self,
        signal: Dict[str, Any],
        signal_id: str,
        now: str,
    ) -> Dict[str, Any]:
        promotion_level = self._current_level(signal)
        market = self._detect_market(signal)

        record = {
            "history_version": self.VERSION,
            "history_signal_id": signal_id,
            "created_at": now,
            "last_seen_at": now,
            "updated_at": now,

            "match_id": str(signal.get("match_id") or signal.get("fixture_id") or ""),
            "fixture_id": str(signal.get("fixture_id") or signal.get("match_id") or ""),

            "home_team": signal.get("home_team") or "",
            "away_team": signal.get("away_team") or "",
            "league": signal.get("league") or "",
            "country": signal.get("country") or "",

            "market": market,
            "initial_promotion_level": promotion_level,
            "current_promotion_level": promotion_level,
            "best_promotion_level": promotion_level,

            "initial_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "current_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "best_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),

            "initial_scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "current_scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "final_scoreline": None,

            "promotion_score": safe_float(signal.get("promotion_score"), 0),
            "best_promotion_score": safe_float(signal.get("promotion_score"), 0),

            "confidence": self._confidence(signal),
            "best_confidence": self._confidence(signal),

            "panel_label": signal.get("panel_promotion_label")
            or signal.get("promotion_panel_label")
            or signal.get("panel_signal_type")
            or signal.get("panel_label")
            or "",

            "reason": signal.get("panel_promotion_reason")
            or signal.get("promotion_reason")
            or signal.get("panel_narrative_reason")
            or signal.get("narrative_main_reason")
            or signal.get("master_reason")
            or "",

            "action": signal.get("promotion_action")
            or signal.get("master_action")
            or "",

            "result_status": self.RESULT_PENDING,
            "result_reason": "Señal registrada. Resultado pendiente.",
            "evaluated_at": None,

            "evolution": [
                self._build_evolution_item(signal=signal, now=now, event="CREATED")
            ],
        }

        return record

    def _update_record(
        self,
        existing: Dict[str, Any],
        signal: Dict[str, Any],
        now: str,
    ) -> Dict[str, Any]:
        current_level = self._current_level(signal)
        current_priority = self.LEVEL_PRIORITY.get(current_level, 0)

        best_level = normalize_text(existing.get("best_promotion_level"))
        best_priority = self.LEVEL_PRIORITY.get(best_level, 0)

        current_score = safe_float(signal.get("promotion_score"), 0)
        best_score = safe_float(existing.get("best_promotion_score"), 0)

        current_confidence = self._confidence(signal)
        best_confidence = safe_float(existing.get("best_confidence"), 0)

        existing["last_seen_at"] = now
        existing["updated_at"] = now
        existing["current_promotion_level"] = current_level
        existing["current_minute"] = safe_int(signal.get("api_minute") or signal.get("display_minute"), 0)
        existing["current_scoreline"] = signal.get("scoreline") or signal.get("current_score") or existing.get("current_scoreline")
        existing["promotion_score"] = current_score
        existing["confidence"] = current_confidence

        existing["panel_label"] = (
            signal.get("panel_promotion_label")
            or signal.get("promotion_panel_label")
            or signal.get("panel_signal_type")
            or signal.get("panel_label")
            or existing.get("panel_label")
            or ""
        )

        existing["reason"] = (
            signal.get("panel_promotion_reason")
            or signal.get("promotion_reason")
            or signal.get("panel_narrative_reason")
            or signal.get("narrative_main_reason")
            or signal.get("master_reason")
            or existing.get("reason")
            or ""
        )

        existing["action"] = (
            signal.get("promotion_action")
            or signal.get("master_action")
            or existing.get("action")
            or ""
        )

        if current_priority > best_priority:
            existing["best_promotion_level"] = current_level
            existing["best_minute"] = existing["current_minute"]
            existing["best_promotion_score"] = current_score
            existing["best_confidence"] = current_confidence

            existing.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="PROMOTED")
            )

        elif current_score > best_score or current_confidence > best_confidence:
            existing["best_promotion_score"] = max(best_score, current_score)
            existing["best_confidence"] = max(best_confidence, current_confidence)

            existing.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="UPDATED")
            )

        else:
            evolution = existing.setdefault("evolution", [])
            if not evolution or evolution[-1].get("minute") != existing["current_minute"]:
                evolution.append(
                    self._build_evolution_item(signal=signal, now=now, event="SEEN_AGAIN")
                )

        self._apply_expiration_if_needed(existing, signal, now)

        return existing

    def _apply_expiration_if_needed(
        self,
        record: Dict[str, Any],
        signal: Dict[str, Any],
        now: str,
    ) -> None:
        if record.get("result_status") != self.RESULT_PENDING:
            return

        if bool(signal.get("no_reentry")):
            record["result_status"] = self.RESULT_EXPIRED
            record["result_reason"] = "La señal expiró por vida útil."
            record["evaluated_at"] = now
            record.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="EXPIRED")
            )

    def _build_evolution_item(
        self,
        signal: Dict[str, Any],
        now: str,
        event: str,
    ) -> Dict[str, Any]:
        return {
            "event": event,
            "at": now,
            "minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "promotion_level": self._current_level(signal),
            "promotion_score": safe_float(signal.get("promotion_score"), 0),
            "confidence": self._confidence(signal),
            "panel_label": signal.get("panel_promotion_label")
            or signal.get("promotion_panel_label")
            or signal.get("panel_signal_type")
            or signal.get("panel_label")
            or "",
            "reason": signal.get("promotion_reason")
            or signal.get("master_reason")
            or signal.get("panel_narrative_reason")
            or "",
        }

    def _current_level(self, signal: Dict[str, Any]) -> str:
        promotion_level = normalize_text(signal.get("promotion_level"))

        if promotion_level:
            return promotion_level

        master_status = normalize_text(signal.get("master_status"))

        if master_status in {"TOP_SIGNAL", "MAIN_SIGNAL", "STRONG_CANDIDATE", "WAIT_REVALIDATION"}:
            return master_status

        if bool(signal.get("can_publish")):
            return "MAIN_SIGNAL"

        if bool(signal.get("should_observe")):
            return "OBSERVE_ONLY"

        return "OBSERVE_ONLY"

    def _detect_market(self, signal: Dict[str, Any]) -> str:
        candidates = [
            signal.get("promotion_market"),
            signal.get("narrative_reading_name"),
            signal.get("football_dominant_reading"),
            signal.get("panel_market"),
            signal.get("master_market"),
            signal.get("market"),
            signal.get("suggested_market"),
        ]

        for item in candidates:
            value = normalize_text(item)
            if "OVER" in value:
                return "OVER"
            if "UNDER" in value or "BAJO" in value:
                return "UNDER"

        over = safe_float(signal.get("over_score"), 0)
        under = safe_float(signal.get("under_score"), 0)

        if over > under + 5:
            return "OVER"

        if under > over + 5:
            return "UNDER"

        return "NO_BET"

    def _confidence(self, signal: Dict[str, Any]) -> float:
        values = [
            safe_float(signal.get("promotion_score"), 0),
            safe_float(signal.get("master_confidence"), 0),
            safe_float(signal.get("football_confidence"), 0),
            safe_float(signal.get("elite_score"), 0),
        ]

        return max(values)

    def _build_history_id(self, signal: Dict[str, Any]) -> str:
        match_id = str(signal.get("match_id") or signal.get("fixture_id") or "").strip()
        market = self._detect_market(signal)

        if not match_id:
            home = str(signal.get("home_team") or "").strip().lower().replace(" ", "_")
            away = str(signal.get("away_team") or "").strip().lower().replace(" ", "_")
            match_id = f"{home}_vs_{away}"

        return f"V17_HISTORY:{match_id}:{market}"

    def _find_record(
        self,
        records: List[Dict[str, Any]],
        signal_id: str,
    ) -> Optional[Dict[str, Any]]:
        for record in records:
            if record.get("history_signal_id") == signal_id:
                return record
        return None

    def _ensure_storage(self) -> None:
        if self.STORAGE_FILE.exists():
            return

        self._save(
            {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "records": [],
            }
        )

    def _load(self) -> Dict[str, Any]:
        self._ensure_storage()

        try:
            with self.STORAGE_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid history storage")

            data.setdefault("records", [])
            return data

        except Exception:
            return {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "records": [],
            }

    def _save(self, data: Dict[str, Any]) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        temp_file = self.STORAGE_FILE.with_suffix(".tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        temp_file.replace(self.STORAGE_FILE)
