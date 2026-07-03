from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.v17.signals.result_resolver import ResultResolver


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_text(value: Any) -> str:
    try:
        return str(value or "").strip().upper()
    except Exception:
        return ""


def normalize_market(value: Any) -> str:
    text = normalize_text(value)

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    return "OTHER"


def parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None

    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


class CandidateTrackerV17:
    """
    Tracking pasivo de candidatos fuertes V17.5.

    Objetivo:
    - Registrar STRONG_CANDIDATE / HIGH_OBSERVATION como EVALUATION_ONLY.
    - No publicar.
    - No tocar official_*.
    - No mezclar métricas con señales oficiales.
    - Persistir pending/closed para que no desaparezcan al reiniciar backend.
    """

    VERSION = "V17_5_TRACKED_CANDIDATE_EVALUATOR_1"
    TRACKING_TYPE = "TRACKED_CANDIDATE"
    TRACKING_ROLE = "EVALUATION_ONLY"

    STORAGE_DIR = Path("app/v17/storage")
    STORAGE_FILE = STORAGE_DIR / "tracked_candidates.json"

    RETENTION_HOURS = 24
    MAX_PENDING = 300
    MAX_CLOSED = 1000

    ALLOWED_OFFICIAL_STATUS = {
        "WAIT_CONFIRMATION",
        "OBSERVE",
        "OPERABLE",
        "ENTER",
    }

    CANDIDATE_LEVELS = {
        "STRONG_CANDIDATE",
        "HIGH_OBSERVATION",
        "MAIN_SIGNAL",
        "TOP_SIGNAL",
    }

    BAD_DATA_TRUTH_STATES = {
        "NO_INTERPRETABLE_DATA",
        "DATA_INSUFFICIENT",
        "WAIT_REAL_STATS",
    }

    CRITICAL_BLOCKER_TOKENS = {
        "CRITICAL",
        "EXTREME",
        "BLOCKED_CLOCK",
        "NO_INTERPRETABLE",
        "DATA_INSUFFICIENT",
        "WAIT_REAL_STATS",
        "DATA_TRUTH",
        "NO_REENTRY",
        "MATCH_NOT_SCANNABLE",
    }

    def __init__(self, storage_file: Optional[Path] = None) -> None:
        self.storage_file = storage_file or self.STORAGE_FILE
        self.resolver = ResultResolver()
        self._ensure_storage()

    def register_candidates(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Registra candidatos evaluables sin publicarlos.

        No registra bloqueados, datos insuficientes, mercados no oficiales
        ni lecturas peligrosas.
        """

        data = self._load()
        pending = data.setdefault("pending", {})
        registered: List[Dict[str, Any]] = []
        changed = False

        for signal in signals or []:
            if not isinstance(signal, dict):
                continue

            if not self._should_track(signal):
                continue

            record = self._build_candidate_record(signal)
            signal_key = record.get("signal_key")

            if not signal_key:
                continue

            existing = pending.get(signal_key)

            if existing:
                pending[signal_key] = self._refresh_candidate(existing, signal)
                registered.append(deepcopy(pending[signal_key]))
                changed = True
                continue

            pending[signal_key] = record
            registered.append(deepcopy(record))
            changed = True

        if changed:
            data["updated_at"] = utc_now_iso()
            self._save(data)

        return registered

    def update_with_live_matches(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resuelve candidatos pendientes usando el mismo ResultResolver,
        pero manteniendo tracking_role=EVALUATION_ONLY.
        """

        data = self._load()
        pending = data.setdefault("pending", {})
        closed = data.setdefault("closed", [])

        match_index = self._build_match_index(live_matches)
        still_pending: Dict[str, Dict[str, Any]] = {}
        newly_closed: List[Dict[str, Any]] = []

        for signal_key, tracked in list(pending.items()):
            expired = self._expire_if_needed(tracked)

            if expired:
                closed.insert(0, expired)
                newly_closed.append(deepcopy(expired))
                continue

            match_id = str(tracked.get("fixture_id") or tracked.get("match_id") or "")
            current_match = match_index.get(match_id)

            if not current_match:
                tracked["tracking_status"] = "PENDING"
                tracked["pending_reason"] = "MATCH_NOT_FOUND_IN_LIVE_SNAPSHOT"
                still_pending[signal_key] = tracked
                continue

            resolved = self.resolver.resolve(tracked, current_match)
            resolved = self._mark_as_candidate_result(resolved)

            if resolved.get("resolved"):
                resolved["tracking_status"] = "CLOSED"
                closed.insert(0, deepcopy(resolved))
                newly_closed.append(deepcopy(resolved))
            else:
                resolved["tracking_status"] = "PENDING"
                still_pending[signal_key] = resolved

        data["pending"] = self._trim_pending(still_pending)
        data["closed"] = self._trim_closed(closed)
        data["updated_at"] = utc_now_iso()

        self._save(data)

        return {
            "candidate_tracking_role": self.TRACKING_ROLE,
            "candidate_tracking_type": self.TRACKING_TYPE,
            "registered": [],
            "pending": self.pending(),
            "closed": self.closed(),
            "newly_closed": newly_closed,
            "summary": self.summary(),
        }

    def pending(self) -> List[Dict[str, Any]]:
        data = self._load()
        pending = list((data.get("pending") or {}).values())
        pending.sort(
            key=lambda item: str(item.get("registered_at") or ""),
            reverse=True,
        )
        return deepcopy(pending)

    def closed(self, limit: int = 200) -> List[Dict[str, Any]]:
        data = self._load()
        closed = data.get("closed") or []
        return deepcopy(closed[:limit])

    def summary(self) -> Dict[str, Any]:
        data = self._load()
        pending = list((data.get("pending") or {}).values())
        closed = data.get("closed") or []

        wins = sum(1 for item in closed if normalize_text(item.get("result_status")) == "WON")
        losses = sum(1 for item in closed if normalize_text(item.get("result_status")) == "LOST")
        voids = sum(1 for item in closed if normalize_text(item.get("result_status")) == "VOID")
        expired = sum(1 for item in closed if normalize_text(item.get("result_status")) == "EXPIRED")

        decided = wins + losses

        return {
            "candidate_tracking_role": self.TRACKING_ROLE,
            "candidate_tracking_type": self.TRACKING_TYPE,
            "pending": len(pending),
            "closed": len(closed),
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "expired": expired,
            "decided": decided,
            "candidate_accuracy": round((wins / decided) * 100, 2) if decided else 0.0,
            "total_tracked_candidates": len(pending) + len(closed),
        }

    def _should_track(self, signal: Dict[str, Any]) -> bool:
        official_market = normalize_market(signal.get("official_market"))

        if official_market not in {"OVER", "UNDER"}:
            return False

        official_status = normalize_text(signal.get("official_status"))

        if official_status == "BLOCKED":
            return False

        if official_status not in self.ALLOWED_OFFICIAL_STATUS:
            return False

        if normalize_text(signal.get("risk_status")) == "EXTREME_RISK":
            return False

        if normalize_text(signal.get("clock_status")) == "BLOCKED_CLOCK":
            return False

        if bool(signal.get("data_truth_blocks_market")):
            return False

        data_truth_state = normalize_text(signal.get("data_truth_state"))

        if data_truth_state in self.BAD_DATA_TRUTH_STATES:
            return False

        if signal.get("data_truth_can_interpret") is False:
            return False

        hard_blockers = signal.get("hard_blockers") or []

        if self._has_critical_blockers(hard_blockers):
            return False

        promotion_level = normalize_text(signal.get("promotion_level"))
        activation_level = normalize_text(signal.get("activation_level"))

        if promotion_level in self.CANDIDATE_LEVELS:
            return True

        if activation_level in self.CANDIDATE_LEVELS:
            return True

        return False

    def _has_critical_blockers(self, blockers: Any) -> bool:
        if not isinstance(blockers, list):
            return False

        text = " ".join(str(item or "").upper() for item in blockers)

        if not text.strip():
            return False

        return any(token in text for token in self.CRITICAL_BLOCKER_TOKENS)

    def _build_candidate_record(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        market = normalize_market(signal.get("official_market"))
        minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("minute")
            or signal.get("current_minute"),
            0,
        )

        entry_home_score = safe_int(
            signal.get("home_score")
            or signal.get("current_home_score")
            or signal.get("entry_home_score"),
            0,
        )

        entry_away_score = safe_int(
            signal.get("away_score")
            or signal.get("current_away_score")
            or signal.get("entry_away_score"),
            0,
        )

        minute_bucket = self._minute_bucket(minute)
        fixture_id = str(signal.get("fixture_id") or signal.get("match_id") or "")
        signal_key = self._candidate_key(
            fixture_id=fixture_id,
            market=market,
            minute_bucket=minute_bucket,
        )

        max_follow_minutes = self._follow_window(market=market, entry_minute=minute)

        now = utc_now_iso()

        return {
            "candidate_tracker_version": self.VERSION,
            "tracking_type": self.TRACKING_TYPE,
            "tracking_role": self.TRACKING_ROLE,
            "evaluation_only": True,
            "published": False,

            "signal_key": signal_key,
            "fixture_id": fixture_id,
            "match_id": fixture_id,

            "home_team": signal.get("home_team") or "",
            "away_team": signal.get("away_team") or "",
            "league": signal.get("league") or "",
            "country": signal.get("country") or "",

            "entry_minute": minute,
            "minute_bucket": minute_bucket,
            "entry_home_score": entry_home_score,
            "entry_away_score": entry_away_score,
            "entry_score": f"{entry_home_score}-{entry_away_score}",
            "entry_scoreline": f"{entry_home_score}-{entry_away_score}",
            "entry_total_goals": entry_home_score + entry_away_score,
            "max_follow_minutes": max_follow_minutes,

            "market": market,
            "market_direction": market,
            "official_market": signal.get("official_market"),
            "official_status": signal.get("official_status"),
            "official_confidence": safe_float(signal.get("official_confidence"), 0),
            "official_probable_score": signal.get("official_probable_score"),
            "official_next_goal_team": signal.get("official_next_goal_team"),
            "official_can_publish": bool(signal.get("official_can_publish")),

            "promotion_level": signal.get("promotion_level"),
            "promotion_score": safe_float(signal.get("promotion_score"), 0),
            "activation_level": signal.get("activation_level"),
            "activation_score": safe_float(signal.get("activation_score"), 0),

            "data_quality": signal.get("data_quality") or signal.get("data_source_quality"),
            "data_source_quality": signal.get("data_source_quality") or signal.get("data_quality"),
            "data_truth_state": signal.get("data_truth_state"),
            "data_truth_can_interpret": signal.get("data_truth_can_interpret"),

            "match_phase_type": signal.get("match_phase_type"),
            "momentum_direction": signal.get("momentum_direction"),
            "pressure_type": signal.get("pressure_type"),
            "live_match_state": signal.get("live_match_state"),

            "registered_at": now,
            "last_seen_at": now,

            "tracking_status": "PENDING",
            "result_status": "PENDING",
            "result_label": "PENDIENTE",
            "result_reason": "TRACKED_CANDIDATE_REGISTERED",
            "result_explanation": (
                "Candidato fuerte registrado solo para evaluación. "
                "No es señal publicada ni decisión operativa."
            ),
            "resolved": False,
            "resolved_at": None,
        }

    def _refresh_candidate(
        self,
        existing: Dict[str, Any],
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        refreshed = deepcopy(existing)

        keep_fields = {
            "candidate_tracker_version",
            "tracking_type",
            "tracking_role",
            "evaluation_only",
            "published",
            "signal_key",
            "fixture_id",
            "match_id",
            "entry_minute",
            "minute_bucket",
            "entry_home_score",
            "entry_away_score",
            "entry_score",
            "entry_scoreline",
            "entry_total_goals",
            "max_follow_minutes",
            "market",
            "market_direction",
            "registered_at",
            "tracking_status",
            "result_status",
            "result_label",
            "result_reason",
            "result_explanation",
            "resolved",
            "resolved_at",
        }

        fresh = self._build_candidate_record(signal)

        for key, value in fresh.items():
            if key not in keep_fields:
                refreshed[key] = value

        refreshed["last_seen_at"] = utc_now_iso()

        return refreshed

    def _mark_as_candidate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(result or {})
        result["tracking_type"] = self.TRACKING_TYPE
        result["tracking_role"] = self.TRACKING_ROLE
        result["evaluation_only"] = True
        result["published"] = False
        result["candidate_result_label"] = "CANDIDATO EVALUADO"
        return result

    def _expire_if_needed(self, tracked: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        registered_at = parse_time(tracked.get("registered_at"))
        now = utc_now()

        if not registered_at:
            return None

        age = now - registered_at

        if age < timedelta(hours=self.RETENTION_HOURS):
            return None

        expired = deepcopy(tracked)
        expired["tracking_status"] = "CLOSED"
        expired["result_status"] = "EXPIRED"
        expired["result_label"] = "EXPIRADO"
        expired["resolved"] = True
        expired["resolved_at"] = utc_now_iso()
        expired["result_reason"] = "TRACKED_CANDIDATE_RETENTION_EXPIRED"
        expired["result_explanation"] = (
            "El candidato evaluado superó la ventana máxima de seguimiento pasivo."
        )
        return expired

    def _build_match_index(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}

        for match in live_matches or []:
            if not isinstance(match, dict):
                continue

            match_id = str(match.get("fixture_id") or match.get("match_id") or "")

            if match_id:
                index[match_id] = match

        return index

    def _candidate_key(self, fixture_id: str, market: str, minute_bucket: str) -> str:
        if not fixture_id or market not in {"OVER", "UNDER"}:
            return ""

        return f"V17_TRACKED_CANDIDATE:{fixture_id}:{market}:{minute_bucket}"

    def _minute_bucket(self, minute: int) -> str:
        minute = max(0, safe_int(minute, 0))

        if minute <= 15:
            return "M00_15"

        if minute <= 30:
            return "M16_30"

        if minute <= 45:
            return "M31_45"

        if minute <= 60:
            return "M46_60"

        if minute <= 75:
            return "M61_75"

        if minute <= 90:
            return "M76_90"

        return "M90_PLUS"

    def _follow_window(self, market: str, entry_minute: int) -> int:
        entry_minute = safe_int(entry_minute, 0)

        if market == "UNDER":
            base = 18
        else:
            base = 20

        if entry_minute >= 88:
            return 8

        if entry_minute >= 80:
            return 12

        return base

    def _trim_pending(self, pending: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if len(pending) <= self.MAX_PENDING:
            return pending

        items = sorted(
            pending.items(),
            key=lambda item: str(item[1].get("last_seen_at") or item[1].get("registered_at") or ""),
            reverse=True,
        )

        return dict(items[: self.MAX_PENDING])

    def _trim_closed(self, closed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = utc_now()
        kept: List[Dict[str, Any]] = []

        for item in closed or []:
            resolved_at = parse_time(item.get("resolved_at"))

            if not resolved_at:
                kept.append(item)
                continue

            if now - resolved_at <= timedelta(hours=self.RETENTION_HOURS):
                kept.append(item)

        return kept[: self.MAX_CLOSED]

    def _ensure_storage(self) -> None:
        if self.storage_file.exists():
            return

        self._save(
            {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "pending": {},
                "closed": [],
            }
        )

    def _load(self) -> Dict[str, Any]:
        self._ensure_storage()

        try:
            with self.storage_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid tracked candidates storage")

            data.setdefault("pending", {})
            data.setdefault("closed", [])
            return data

        except Exception:
            return {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "pending": {},
                "closed": [],
            }

    def _save(self, data: Dict[str, Any]) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        temp_file = self.storage_file.with_suffix(".tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        temp_file.replace(self.storage_file)
