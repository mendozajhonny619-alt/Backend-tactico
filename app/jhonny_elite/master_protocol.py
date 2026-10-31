from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import time
from pathlib import Path
from threading import RLock
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from app.config.config import Config


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def first_known(*values: Any) -> Any:
    """Return first published value; numerical zero is NOT missing data."""
    for value in values:
        if value is not None and value != "":
            return value
    return None


def si(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _market(direction: Any) -> str:
    text = str(direction or "").upper()
    if "OVER" in text:
        return "OVER"
    if "UNDER" in text:
        return "UNDER"
    return "NO_BET"


class DataTruthAI:
    """Master Protocol data-quality layer.

    It never converts missing data into football evidence.  Empty/flat live
    feeds are explicitly treated as insufficient instead of "quiet match".
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        base_quality: Dict[str, Any],
        clock: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = list(base_quality.get("data_issues") or [])
        score = 100.0

        shots = sf(first_known(match.get("shots"), match.get("total_shots")), -1)
        sot = sf(first_known(match.get("shots_on_target"), match.get("total_shots_on")), -1)
        dangerous = sf(first_known(match.get("dangerous_attacks"), match.get("total_dangerous_attacks")), -1)
        xg = sf(first_known(match.get("xg"), match.get("xG")), -1)
        minute = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)
        has_live_stats = bool(match.get("has_live_stats"))
        fusion_conflicts = {str(x).upper() for x in (match.get("fusion_conflicts") or []) if x}
        critical_fusion_conflicts = fusion_conflicts.intersection({
            "SCORE_CONFLICT", "CLOCK_CONFLICT", "EVENT_CONFLICT"
        })
        stale_fusion = "STALE_SOURCE" in fusion_conflicts

        if critical_fusion_conflicts:
            score -= 55
            issues.extend(sorted(critical_fusion_conflicts))
        if "STATS_CONFLICT" in fusion_conflicts:
            score -= 25
            issues.append("STATS_CONFLICT")
        if stale_fusion:
            score -= 35
            issues.append("STALE_SOURCE")

        if not base_quality.get("data_valid", True):
            score -= 45
        if not has_live_stats:
            score -= 20
            issues.append("NO_LIVE_STATS")
        if minute <= 0:
            score -= 20
            issues.append("INVALID_MINUTE")

        clock_status = str(clock.get("clock_status") or "").upper()
        if "BLOCK" in clock_status or clock.get("clock_stale") or clock.get("clock_frozen"):
            score -= 40
            issues.append("CLOCK_UNTRUSTED")

        # Anti-empty-data rule.  Zeros can be real, but if every attacking
        # channel is zero/missing after the opening minutes, it is absence of
        # interpretable evidence, not automatic UNDER evidence.
        zeros_or_missing = sum(1 for v in (shots, sot, dangerous, xg) if v <= 0)
        anti_empty_block = bool(minute >= 15 and zeros_or_missing >= 4)
        if anti_empty_block:
            score -= 45
            issues.append("EMPTY_LIVE_EVIDENCE")

        data_age = sf(first_known(clock.get("data_age_seconds"), match.get("stats_age_seconds"),
                                  match.get("api_data_age_seconds")), 9999.0)
        if clock.get("timestamp_missing"):
            score -= 40
            issues.append("TIMESTAMP_UNVERIFIED")
        age_limit = sf(getattr(Config, "MAX_LIVE_DATA_AGE_SECONDS", 150), 150)
        if data_age > age_limit and not clock.get("timestamp_missing"):
            score -= 35
            issues.append("STALE_SOURCE")

        score = clamp(score)
        if critical_fusion_conflicts:
            state = "CONFLICTED"
        elif stale_fusion or (data_age > age_limit and not clock.get("timestamp_missing")):
            state = "STALE"
        elif score >= 90:
            state = "EXCELLENT"
        elif score >= 78:
            state = "HIGH"
        elif score >= 62:
            state = "MEDIUM"
        elif score >= 45:
            state = "LOW"
        else:
            state = "INSUFFICIENT"

        critical = state in {"INSUFFICIENT", "CONFLICTED", "STALE"} or anti_empty_block
        return {
            **base_quality,
            "data_truth_score": round(score, 2),
            "data_truth_status": state,
            "data_truth_issues": sorted(set(str(x) for x in issues if x)),
            "anti_empty_data_block": anti_empty_block,
            "data_valid": bool(base_quality.get("data_valid", True)) and not critical,
        }


@dataclass
class _Snapshot:
    minute: int
    timestamp: float
    home_score: int
    away_score: int
    shots: Optional[float]
    sot: Optional[float]
    dangerous: Optional[float]
    corners: Optional[float]
    xg: Optional[float]
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_sot: Optional[float] = None
    away_sot: Optional[float] = None
    home_dangerous: Optional[float] = None
    away_dangerous: Optional[float] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    home_corners: Optional[float] = None
    away_corners: Optional[float] = None


class TemporalMatchMemory:
    """Evidence-only rolling 5/10/15 match-minute windows.

    Missing values remain missing. A 20-minute old snapshot cannot stand in
    for a five-minute window; short fragments cannot pretend to represent a
    full 10/15-minute window. No estimated momentum is returned when a source
    is stale, a counter is corrected, or the match clock moves backwards.
    """

    MIN_COVERAGE = 0.70
    CLOCK_GRACE_SECONDS = 75.0

    def __init__(self, max_snapshots: int = 90) -> None:
        self.max_snapshots = max_snapshots
        self._memory: Dict[str, Deque[_Snapshot]] = defaultdict(lambda: deque(maxlen=self.max_snapshots))

    @staticmethod
    def _metric(match: Dict[str, Any], *names: str) -> Optional[float]:
        for name in names:
            value = match.get(name)
            if value is None or value == "":
                continue
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(number) and number >= 0:
                return number
        return None

    @staticmethod
    def _timestamp(match: Dict[str, Any]) -> float:
        for field in ("source_timestamp", "fetched_at", "received_timestamp"):
            value = match.get(field)
            if value is None or value == "":
                continue
            try:
                if isinstance(value, (int, float)) or str(value).replace(".", "", 1).isdigit():
                    stamp = float(value)
                    if stamp > 1e12:  # provider milliseconds
                        stamp /= 1000.0
                else:
                    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    stamp = dt.timestamp()
                if math.isfinite(stamp) and stamp > 0:
                    return stamp
            except (ValueError, TypeError, OverflowError, OSError):
                continue
        return datetime.now(timezone.utc).timestamp()

    @staticmethod
    def _side_metric(
        match: Dict[str, Any], side: str, flat: Tuple[str, ...],
        nested: Tuple[str, ...], published: Tuple[str, ...],
    ) -> Optional[float]:
        """Read verified home/away metrics without promoting default zeroes.

        API-Football supplies `home_stats`/`away_stats` with explicit
        `stats_available_fields` provenance. The legacy flat schema remains
        supported for other adapters, but cannot override missing API fields.
        """
        stats = match.get(f"{side}_stats")
        if isinstance(stats, dict):
            flags = stats.get("stats_available_fields")
            if isinstance(flags, (list, tuple, set)):
                if not set(flags).intersection(published) and not (
                    "expected_goals" in published and stats.get("xg_available") is True
                ):
                    return None
                return TemporalMatchMemory._metric(stats, *nested)
        flat_value = TemporalMatchMemory._metric(match, *flat)
        if flat_value is not None:
            return flat_value
        return TemporalMatchMemory._metric(stats, *nested) if isinstance(stats, dict) else None

    @staticmethod
    def _total(match: Dict[str, Any], aggregate: Tuple[str, ...], home: Optional[float], away: Optional[float]) -> Optional[float]:
        # API totals are often created by adding default zeroes for fields
        # absent on either side. A real total requires BOTH side measurements.
        hs, aw = match.get("home_stats"), match.get("away_stats")
        if any(isinstance(row, dict) and isinstance(row.get("stats_available_fields"), (list, tuple, set)) for row in (hs, aw)):
            return home + away if home is not None and away is not None else None
        if match.get("has_live_stats") is False:
            return None
        actual = TemporalMatchMemory._metric(match, *aggregate)
        if actual is not None:
            return actual
        return home + away if home is not None and away is not None else None

    def enrich(self, match: Dict[str, Any]) -> Dict[str, Any]:
        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "")
        if not fixture_id:
            return match

        minute = si(first_known(match.get("effective_minute"), match.get("api_minute"), match.get("minute")), 0)
        home_shots = self._side_metric(match, "home", ("home_shots", "shots_home"), ("shots",), ("Total Shots",))
        away_shots = self._side_metric(match, "away", ("away_shots", "shots_away"), ("shots",), ("Total Shots",))
        home_sot = self._side_metric(match, "home", ("home_shots_on_target", "sot_home", "shots_on_home", "home_shots_on"), ("shots_on_target",), ("Shots on Goal",))
        away_sot = self._side_metric(match, "away", ("away_shots_on_target", "sot_away", "shots_on_away", "away_shots_on"), ("shots_on_target",), ("Shots on Goal",))
        home_dangerous = self._side_metric(match, "home", ("home_dangerous_attacks", "dangerous_attacks_home"), ("dangerous_attacks",), ("Dangerous Attacks",))
        away_dangerous = self._side_metric(match, "away", ("away_dangerous_attacks", "dangerous_attacks_away"), ("dangerous_attacks",), ("Dangerous Attacks",))
        home_xg = self._side_metric(match, "home", ("home_xg", "xg_home"), ("xG", "xg"), ("expected_goals",))
        away_xg = self._side_metric(match, "away", ("away_xg", "xg_away"), ("xG", "xg"), ("expected_goals",))
        home_corners = self._side_metric(match, "home", ("home_corners", "corners_home"), ("corners",), ("Corner Kicks",))
        away_corners = self._side_metric(match, "away", ("away_corners", "corners_away"), ("corners",), ("Corner Kicks",))
        snap = _Snapshot(
            minute=minute,
            timestamp=self._timestamp(match),
            home_score=si(match.get("home_score"), 0),
            away_score=si(match.get("away_score"), 0),
            shots=self._total(match, ("shots", "total_shots"), home_shots, away_shots),
            sot=self._total(match, ("shots_on_target", "total_shots_on"), home_sot, away_sot),
            dangerous=self._total(match, ("dangerous_attacks", "total_dangerous_attacks"), home_dangerous, away_dangerous),
            corners=self._total(match, ("corners", "total_corners"), home_corners, away_corners),
            xg=self._total(match, ("xg", "xG", "total_xg"), home_xg, away_xg),
            home_shots=home_shots, away_shots=away_shots,
            home_sot=home_sot, away_sot=away_sot,
            home_dangerous=home_dangerous, away_dangerous=away_dangerous,
            home_xg=home_xg, away_xg=away_xg,
            home_corners=home_corners, away_corners=away_corners,
        )
        history = self._memory[fixture_id]
        reset_reason = None
        if history:
            previous = history[-1]
            if snap.timestamp < previous.timestamp or snap.minute < previous.minute:
                reset_reason = "OUT_OF_ORDER_CLOCK"
            elif (snap.home_score < previous.home_score or snap.away_score < previous.away_score):
                reset_reason = "SCORE_REVISION"
            elif any(
                before is not None and after is not None and after + 0.005 < before
                for before, after in (
                    (getattr(previous, key), getattr(snap, key)) for key in (
                        "shots", "sot", "dangerous", "corners", "xg",
                        "home_shots", "away_shots", "home_sot", "away_sot",
                        "home_dangerous", "away_dangerous", "home_xg", "away_xg",
                        "home_corners", "away_corners",
                    )
                )
            ):
                reset_reason = "STAT_REVISION"
            if reset_reason:
                history.clear()
        if not history or snap.timestamp > history[-1].timestamp:
            history.append(snap)
        elif snap.timestamp == history[-1].timestamp:
            # A corrected payload at the same source time supersedes the old
            # reading; it never creates a fictitious extra time interval.
            history[-1] = snap

        # A source whose explicit freshness guard has already failed cannot
        # provide live momentum even when old snapshots happen to be present.
        stats_age = self._metric(match, "stats_age_seconds")
        stale_stats = stats_age is not None and stats_age > sf(getattr(Config, "MAX_LIVE_DATA_AGE_SECONDS", 150), 150)
        untrusted = (bool(match.get("clock_stale") or match.get("clock_frozen"))
                     or str(match.get("data_truth_status") or "").upper() in {"CONFLICTED", "STALE"}
                     or stale_stats)
        if untrusted:
            # Never use an old cached baseline to manufacture a fresh window
            # once the provider starts updating again.
            history.clear()
        result = dict(match)
        for window in (5, 10, 15):
            result[f"window_{window}"] = (
                {"available": False, "minutes": window, "reason": "SOURCE_UNTRUSTED"}
                if untrusted else self._window_metrics(history, snap, window)
            )
        result["temporal_memory_points"] = len(history)
        result["temporal_memory_ready"] = any(result[f"window_{w}"].get("available") for w in (5, 10, 15))
        result["temporal_team_windows_ready"] = any(
            result[f"window_{w}"].get("team_attribution_available", False) for w in (5, 10, 15)
        )
        if reset_reason:
            result["temporal_memory_reset_reason"] = reset_reason
        return result

    def _window_metrics(self, history: Deque[_Snapshot], current: _Snapshot, window: int) -> Dict[str, Any]:
        unavailable = {"available": False, "minutes": window, "reason": "INSUFFICIENT_WINDOW_COVERAGE"}
        if len(history) < 2:
            return unavailable
        minimum_span = window * self.MIN_COVERAGE
        candidates = [
            x for x in history
            if 0 < current.minute - x.minute <= window
            and minimum_span <= current.minute - x.minute
            and 0 < current.timestamp - x.timestamp <= window * 60.0 + self.CLOCK_GRACE_SECONDS
        ]
        if not candidates:
            return unavailable
        first = candidates[0]
        elapsed = current.minute - first.minute
        deltas: Dict[str, Optional[float]] = {}
        fields = ("shots", "sot", "dangerous", "corners", "xg")
        for field in fields + ("home_shots", "away_shots", "home_sot", "away_sot", "home_dangerous", "away_dangerous", "home_xg", "away_xg", "home_corners", "away_corners"):
            a = getattr(first, field)
            b = getattr(current, field)
            deltas[field] = round(max(0.0, b - a), 3) if a is not None and b is not None else None
        # Dangerous-attack counts alone are insufficient to call an interval
        # genuine goal pressure. At least one football finishing channel must
        # be observed twice to make this window suitable for model input.
        if all(deltas[key] is None for key in ("shots", "sot", "xg")):
            return {**unavailable, "reason": "MISSING_FINISHING_STATISTICS"}
        dsot = deltas["sot"] or 0.0
        dshots = deltas["shots"] or 0.0
        ddanger = deltas["dangerous"] or 0.0
        dcorners = deltas["corners"] or 0.0
        dxg = deltas["xg"] or 0.0
        team_measured = any(
            deltas[f"home_{field}"] is not None and deltas[f"away_{field}"] is not None
            for field in ("shots", "sot", "xg")
        )
        threat = clamp(dsot * 18.0 + dshots * 4.0 + ddanger + dcorners * 4.0 + dxg * 28.0, 0, 100)
        return {
            "available": True,
            "minutes": window,
            "observed_minutes": elapsed,
            "observed_seconds": round(current.timestamp - first.timestamp, 1),
            "coverage_fraction": round(elapsed / window, 3),
            "delta_shots": deltas["shots"],
            "delta_sot": deltas["sot"],
            "delta_dangerous_attacks": deltas["dangerous"],
            "delta_corners": deltas["corners"],
            "delta_xg": deltas["xg"],
            "delta_goals": max(0, (current.home_score + current.away_score) - (first.home_score + first.away_score)),
            "home_delta_shots": deltas["home_shots"],
            "away_delta_shots": deltas["away_shots"],
            "home_delta_sot": deltas["home_sot"],
            "away_delta_sot": deltas["away_sot"],
            "home_delta_xg": deltas["home_xg"],
            "away_delta_xg": deltas["away_xg"],
            "home_delta_dangerous_attacks": deltas["home_dangerous"],
            "away_delta_dangerous_attacks": deltas["away_dangerous"],
            "home_delta_corners": deltas["home_corners"],
            "away_delta_corners": deltas["away_corners"],
            "team_attribution_available": team_measured,
            "threat_score": round(threat, 2),
        }


class ContradictionJudgeMaster:
    """Explicit contradiction judge required by the Master Protocol."""

    def evaluate(
        self,
        direction: Optional[str],
        data_truth: Dict[str, Any],
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        odds: Dict[str, Any],
    ) -> Dict[str, Any]:
        direction = _market(direction)
        warnings: List[Dict[str, str]] = []
        recent = sf(match.get("recent_threat_score"), 0.0)
        rhythm = sf(context.get("rhythm_score"), 0.0)
        false_pressure = sf(tactical.get("false_pressure_risk"), 0.0)
        data_state = str(data_truth.get("data_truth_status") or "INSUFFICIENT")

        def add(code: str, severity: str) -> None:
            warnings.append({"code": code, "severity": severity})

        if direction == "OVER" and false_pressure >= 70:
            add("OVER_PLUS_STERILE_PRESSURE", "WARNING")
        if direction == "UNDER" and (rhythm >= 70 or recent >= 70):
            add("UNDER_PLUS_ACCELERATING_RHYTHM", "CRITICAL")
        if data_state in {"LOW", "INSUFFICIENT", "CONFLICTED", "STALE"}:
            add("HIGH_CONFIDENCE_PLUS_LOW_DATA_QUALITY", "CRITICAL")
        if odds.get("odds_available"):
            status = str(odds.get("valuation_status") or "").upper()
            # Do not mistake a missing/un-calibrated quote for an adverse
            # *verified* price. Such a match may remain a football candidate,
            # though no official market signal can be published.
            if status == "VERIFIED_FRESH_CALIBRATED":
                if not odds.get("has_positive_value"):
                    add("MARKET_VALUE_LOST", "CRITICAL")
            elif odds.get("verification_required"):
                add("MARKET_NOT_VALIDATED", "WARNING")
            if sf(odds.get("odds_age_seconds"), 0) > sf(getattr(Config, "MAX_ODDS_AGE_SECONDS", 180), 180):
                # Stale price blocks publication through Master market_ready;
                # it does not by itself invalidate an observable tactical idea.
                add("STALE_ODDS", "WARNING")

        critical = [x["code"] for x in warnings if x["severity"] == "CRITICAL"]
        return {
            "contradictions": warnings,
            "critical_contradictions": critical,
            "contradiction_status": "CRITICAL" if critical else "WARNING" if warnings else "CLEAR",
        }


class MasterDecisionAI20:
    """Single final authority for official fields.

    Other modules may propose evidence only.  This class alone creates the
    official_* contract consumed by tracking and the frontend.
    """

    def decide(
        self,
        *,
        match: Dict[str, Any],
        direction: Optional[str],
        candidate_score: float,
        candidate: bool,
        blockers: List[str],
        clock: Dict[str, Any],
        data_truth: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        risk: Dict[str, Any],
        pre_match: Dict[str, Any],
        math_evidence: Dict[str, Any],
        odds: Dict[str, Any],
        contradiction: Dict[str, Any],
        enrichment_deferred: bool = False,
    ) -> Dict[str, Any]:
        market = _market(direction)
        minute = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)
        line = sf(odds.get("line"), 0.0)
        price = sf(odds.get("odds"), 0.0)
        data_state = str(data_truth.get("data_truth_status") or "INSUFFICIENT")
        hard = list(blockers or []) + list(contradiction.get("critical_contradictions") or [])
        if str(risk.get("risk_status") or risk.get("risk_level") or "").upper().startswith("EXTREME"):
            hard.append("EXTREME_RISK")
        if data_state in {"INSUFFICIENT", "CONFLICTED", "STALE"}:
            hard.append(f"DATA_{data_state}")
        if data_truth.get("anti_empty_data_block"):
            hard.append("EMPTY_LIVE_EVIDENCE")
        if clock.get("clock_stale") or clock.get("clock_frozen"):
            hard.append("CLOCK_STALE")

        # Publication requires a real live-statistics snapshot. Fixture-only
        # metadata can keep a match visible/tracked, but it is never evidence
        # for an official OVER/UNDER decision (NO DATA != UNDER).
        scan_phase = str(match.get("scan_phase") or "").upper()
        if ("has_live_stats" in match and not bool(match.get("has_live_stats"))) or (scan_phase and scan_phase != "FULL_SCAN"):
            hard.append("NO_LIVE_STATS")
        if match.get("can_publish_signal") is False:
            hard.append("SCAN_NOT_PUBLISHABLE")

        if hard:
            return self._result("BLOCKED", "NO_BET", 0.0, "EXTREME", False, "Bloqueo crítico: " + ", ".join(sorted(set(hard))[:5]), line, price, match, math_evidence, odds, hard, [])
        if not candidate or market == "NO_BET":
            status = "OBSERVATION" if candidate_score >= sf(getattr(Config, "OBSERVATION_MIN_SCORE", 45), 45) else "NO_BET"
            return self._result(status, "NO_BET", candidate_score, "MEDIUM", False, "Sin ventaja suficiente; continuar observando.", line, price, match, math_evidence, odds, [], [])
        if enrichment_deferred:
            return self._result("OPPORTUNITY", "NO_BET", candidate_score, "LOW", False, "Candidato real en cola Economy; falta enriquecimiento.", line, price, match, math_evidence, odds, [], ["ECONOMY_QUEUE"])

        # A conservative Under 3.5 at a 2-0 score may allow ONE more goal.
        # P(no more goals) is a different event and must not substitute for
        # P(UNDER 3.5).  A verified exact-line quote supplies the probability
        # for that SPECIFIC market, while unverified markets remain unpublishable.
        math_support = sf(math_evidence.get("math_support_over" if market == "OVER" else "math_support_under"), 50.0)
        verified_exact_line_p = odds.get("model_probability_for_value")
        if (odds.get("valuation_status") == "VERIFIED_FRESH_CALIBRATED"
                and math_evidence.get("calibration_status") == "VALIDATED_OUT_OF_SAMPLE"
                and isinstance(verified_exact_line_p, (int, float))
                and math.isfinite(float(verified_exact_line_p))):
            math_support = clamp(float(verified_exact_line_p))
        pre_support = sf(pre_match.get("over_pre_match_score" if market == "OVER" else "under_pre_match_score"), 50.0)
        if not pre_match.get("pre_match_available"):
            pre_support = 50.0
        risk_score = sf(risk.get("risk_score"), 50.0)
        live_quality = sf(data_truth.get("data_truth_score"), 50.0)
        value_edge = sf(odds.get("value_edge"), 0.0)
        expected_value = sf(odds.get("expected_value"), value_edge / 100.0)

        # Fail-closed official contract. Missing or legacy verification flags
        # never establish the authenticity of a live goals quote. The LIVE
        # candidate service is the authority for the priced exact line.
        age = odds.get("odds_age_seconds")
        try:
            age = float(age)
        except (TypeError, ValueError, OverflowError):
            age = float("inf")
        verified_market = bool(
            odds.get("verification_required") is True
            and odds.get("valuation_status") == "VERIFIED_FRESH_CALIBRATED"
            and math_evidence.get("calibration_status") == "VALIDATED_OUT_OF_SAMPLE"
            and odds.get("odds_source") == "API_FOOTBALL_LIVE_ODDS"
            and odds.get("quote_is_live") is True
            and odds.get("fixture_verified") is True
            and odds.get("market_verified") is True
            and odds.get("market_type") == "MATCH_GOALS_TOTAL"
            and odds.get("market_period") == "FT"
            and odds.get("odds_timestamp")
            and math.isfinite(age)
            and -30 <= age <= sf(getattr(Config, "MAX_ODDS_AGE_SECONDS", 120), 120)
            and odds.get("odds_status") not in {"SUSPENDED", "BLOCKED", "CLOSED"}
        )

        # Five-layer consensus: tactical, context, goal/rhythm, value, market.
        layers = {
            "TACTICAL": sf(tactical.get("tactical_score"), 0) >= 55,
            "CONTEXT": (sf(context.get("over_context_score"), 0) >= 58 if market == "OVER" else sf(context.get("under_context_score"), 0) >= 58),
            "GOAL_RHYTHM": (sf(context.get("rhythm_score"), 0) >= 55 or sf(match.get("recent_threat_score"), 0) >= 55) if market == "OVER" else (sf(context.get("rhythm_score"), 100) <= 48 and sf(match.get("recent_threat_score"), 100) <= 48),
            "VALUE": verified_market and bool(odds.get("has_positive_value")) and value_edge >= sf(getattr(Config, "EDGE_MIN_PERCENT", 4.0), 4.0),
            "MARKET": verified_market and bool(odds.get("odds_available")) and line > 0 and sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50) <= price <= sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10),
        }
        consensus = sum(1 for ok in layers.values() if ok)

        raw_confidence = (
            candidate_score * 0.34
            + math_support * 0.30
            + pre_support * 0.10
            + live_quality * 0.16
            + clamp(50 + value_edge * 2.2) * 0.10
            - max(0.0, risk_score - 30.0) * 0.24
        )
        # Precision-first: un componente muy debil no puede quedar oculto por el
        # promedio. La confianza se limita por el eslabon mas debil + margen.
        weakest_core = min(candidate_score, math_support, live_quality, max(0.0, 100.0 - risk_score))
        confidence = min(raw_confidence, weakest_core + 12.0)

        warnings: List[str] = []
        prematch_available = bool(pre_match.get("pre_match_available"))
        if not prematch_available:
            warnings.append("PREMATCH_UNAVAILABLE")

        # UNDER debe llegar preparado al ~75: preanalisis desde 68, entrada desde
        # 72, ventana objetivo 75-79 y bloqueo de nuevas entradas muy tardias.
        under_min = int(getattr(Config, "UNDER_MINUTE_MIN", 72))
        under_target = int(getattr(Config, "UNDER_PREFERRED_MINUTE", 75))
        under_target_end = int(getattr(Config, "UNDER_TARGET_WINDOW_END", 79))
        under_late = int(getattr(Config, "UNDER_LATE_ENTRY_MINUTE", 80))
        under_hard_cutoff = int(getattr(Config, "UNDER_HARD_CUTOFF_MINUTE", 84))
        under_timing_ready = True
        if market == "UNDER":
            if minute < under_min:
                warnings.append("UNDER_PREPARING_FOR_75")
                confidence -= max(3.0, (under_min - minute) * 1.5)
                under_timing_ready = False
            elif under_target <= minute <= under_target_end:
                confidence += 2.0
            elif minute >= under_late:
                warnings.append("UNDER_LATE_ENTRY")
                confidence -= min(12.0, 4.0 + max(0, minute - under_late) * 2.0)
            if minute >= under_hard_cutoff:
                warnings.append("UNDER_TOO_LATE_FOR_NEW_SIGNAL")
                under_timing_ready = False

        if minute >= 86:
            warnings.append("RESTRICTED_86_PLUS")
            confidence -= 6

        confidence = clamp(confidence)

        # Mandatory real line/price/value for any official O/U publication.
        low_price = sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50)
        high_price = sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10)
        # verified_market is calculated above from the complete native
        # service contract, never inferred from a missing legacy flag.
        market_ready = bool(odds.get("odds_available")) and verified_market and line > 0 and low_price <= price <= high_price
        edge_floor = sf(getattr(Config, "EDGE_MIN_PERCENT", 5.0), 5.0)
        ev_floor = sf(getattr(Config, "MIN_EXPECTED_VALUE", 0.03), 0.03)
        value_ready = verified_market and bool(odds.get("has_positive_value")) and value_edge >= edge_floor and expected_value >= ev_floor

        consensus_required = 5 if market == "UNDER" else int(getattr(Config, "MASTER_MIN_CONSENSUS", 4))
        consensus_ready = consensus >= consensus_required
        math_floor = sf(getattr(Config, "MIN_MATH_SUPPORT_UNDER", 70.0), 70.0) if market == "UNDER" else sf(getattr(Config, "MIN_MATH_SUPPORT_OVER", 72.0), 72.0)
        math_ready = math_support >= math_floor
        data_ready = live_quality >= sf(getattr(Config, "MIN_DATA_TRUTH_SCORE", 72.0), 72.0)
        risk_ready = risk_score <= sf(getattr(Config, "MAX_SIGNAL_RISK_SCORE", 45.0), 45.0)
        prematch_ready = prematch_available or not bool(getattr(Config, "REQUIRE_PREMATCH_FOR_OFFICIAL", True))

        # Operability/fragility of the real total line.  A stale OVER line that
        # is already below the current score is already settled and must never
        # become a new official signal.  UNDER remains stricter: keep at least
        # one full goal of margin.
        current_total = si(match.get("home_score"), 0) + si(match.get("away_score"), 0)
        line_margin = line - current_total if line > 0 else -999.0
        over_line_ready = market != "OVER" or line >= current_total
        under_line_ready = market != "UNDER" or line_margin >= 1.0
        if market == "OVER" and not over_line_ready:
            warnings.append("OVER_LINE_ALREADY_SETTLED")
        if market == "UNDER" and not under_line_ready:
            warnings.append("UNDER_FRAGILE_LINE")

        publish_floor = (
            sf(getattr(Config, "UNDER_PUBLISH_MIN_CONFIDENCE", 90.0), 90.0)
            if market == "UNDER"
            else sf(getattr(Config, "OVER_PUBLISH_MIN_CONFIDENCE", 88.0), 88.0)
        )

        # Despues de 80 un UNDER nuevo solo puede pasar en condiciones premium;
        # esto evita que el sistema espere hasta 85 simplemente porque el tiempo
        # eleva artificialmente la probabilidad de no gol.
        late_under_ready = True
        if market == "UNDER" and minute >= under_late:
            late_under_ready = confidence >= sf(getattr(Config, "PREMIUM_SIGNAL_CONFIDENCE", 95), 95) and risk_score <= 25
            if not late_under_ready:
                warnings.append("UNDER_LATE_NOT_PREMIUM")

        can_publish = bool(
            confidence >= publish_floor
            and market_ready
            and value_ready
            and consensus_ready
            and math_ready
            and data_ready
            and risk_ready
            and prematch_ready
            and under_timing_ready
            and over_line_ready
            and under_line_ready
            and late_under_ready
        )

        if not verified_market:
            warnings.append("LIVE_GOALS_MARKET_NOT_VERIFIED")
        if not market_ready:
            warnings.append("MISSING_OR_OUT_OF_RANGE_REAL_ODDS")
        if not value_ready:
            warnings.append("NO_POSITIVE_EXPECTED_VALUE")
        if not consensus_ready:
            warnings.append(f"CONSENSUS_{consensus}_OF_5_REQUIRED_{consensus_required}")
        if not math_ready:
            warnings.append(f"MATH_SUPPORT_{math_support:.1f}_BELOW_{math_floor:.1f}")
        if not data_ready:
            warnings.append("DATA_TRUTH_BELOW_MINIMUM")
        if not risk_ready:
            warnings.append("RISK_ABOVE_PRECISION_LIMIT")
        if not prematch_ready:
            warnings.append("PREMATCH_REQUIRED_FOR_OFFICIAL")

        if can_publish:
            if confidence >= sf(getattr(Config, "PREMIUM_SIGNAL_CONFIDENCE", 94), 94):
                tier = "PREMIUM"
            elif confidence >= sf(getattr(Config, "STRONG_SIGNAL_CONFIDENCE", 89), 89):
                tier = "STRONG"
            else:
                tier = "GOOD"
            status = "CONFIRMED_SIGNAL"
            reason = f"MasterDecisionAI confirma {market} {line:g}: consenso {consensus}/5, confianza {confidence:.1f}%, edge {value_edge:.1f}%, EV {expected_value:.3f}."
        else:
            tier = "OBSERVATION" if confidence < publish_floor else "GOOD"
            status = "STRONG_CANDIDATE" if confidence >= publish_floor - 4 else "CANDIDATE"
            reason = "Candidato no publicable todavía: " + ", ".join(warnings[:4])

        risk_level = "LOW" if risk_score < 35 else "MEDIUM" if risk_score < 55 else "HIGH"
        return self._result(status, market if can_publish else "NO_BET", confidence, risk_level, can_publish, reason, line, price, match, math_evidence, odds, [], warnings, tier=tier, consensus=consensus, layers=layers)

    def _result(
        self,
        status: str,
        market: str,
        confidence: float,
        risk: str,
        can_publish: bool,
        reason: str,
        line: float,
        odds_price: float,
        match: Dict[str, Any],
        math_evidence: Dict[str, Any],
        odds: Dict[str, Any],
        blockers: List[str],
        warnings: List[str],
        *,
        tier: str = "NO_BET",
        consensus: int = 0,
        layers: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        next_team = math_evidence.get("next_goal_team") or math_evidence.get("prediction_attacking_team")
        next_prob = sf(math_evidence.get("probability_next_goal") or math_evidence.get("prediction_next_goal_probability"), 0.0)
        no_change = sf(math_evidence.get("probability_no_more_goals") or math_evidence.get("prediction_no_goal_probability"), 0.0)
        if not can_publish:
            stake_pct = 0.0
        elif tier == "PREMIUM" and risk == "LOW":
            stake_pct = min(sf(getattr(Config, "BANKROLL_PREMIUM_MAX_PCT", 5.0), 5.0), 5.0)
        elif risk == "LOW":
            stake_pct = min(sf(getattr(Config, "BANKROLL_STAKE_MAX_PCT", 3.0), 3.0), 3.0)
        else:
            stake_pct = sf(getattr(Config, "BANKROLL_STAKE_MIN_PCT", 1.0), 1.0)

        return {
            "official_status": status,
            "official_market": market,
            "official_line": round(line, 3) if line > 0 else None,
            "official_odds": round(odds_price, 3) if odds_price > 0 else None,
            "official_confidence": round(clamp(confidence), 2),
            "official_risk": risk,
            # Match risk is NOT the same as market risk. An absent quote must
            # not look like an evaluated LOW-risk market in the UI.
            "official_market_risk": (
                "ASSESSED" if odds.get("valuation_status") == "VERIFIED_FRESH_CALIBRATED"
                else "NOT_EVALUABLE"
            ),
            "official_market_probability": (
                odds.get("model_probability_for_value")
                if odds.get("valuation_status") == "VERIFIED_FRESH_CALIBRATED" else None
            ),
            "official_market_evaluation_status": odds.get("valuation_status") or "UNKNOWN",
            "official_can_publish": bool(can_publish),
            "official_reason": reason,
            "official_predicted_score": math_evidence.get("primary_final_score"),
            "official_next_goal_team": next_team,
            "official_next_goal_probability": round(next_prob, 2),
            "official_no_change_probability": round(no_change, 2),
            "official_signal_tier": tier,
            "official_consensus": consensus,
            "official_consensus_layers": layers or {},
            "official_blockers": sorted(set(blockers)),
            "official_warnings": list(dict.fromkeys(warnings)),
            "official_value_edge": round(sf(odds.get("value_edge"), 0.0), 3),
            "official_expected_value": round(sf(odds.get("expected_value"), sf(odds.get("value_edge"), 0.0) / 100.0), 4),
            "official_recommended_stake_pct": round(stake_pct, 2),
            "official_implied_probability": round(sf(odds.get("implied_probability"), 0.0), 2),
            "decision_version": "MASTER_PROTOCOL_20.0",
            "decision_timestamp": now_iso(),
        }


class ShadowModeRecorder:
    """Small append-only Shadow journal, physically separate from official picks.

    Snapshotting all raw match structures every 30 seconds wastes disk space on
    4 GB laptops and may write provider payloads to disk.  Retain only the
    decision evidence needed for an audit, on state/score changes or every five
    minutes.  Existing jsonl data is left untouched and remains readable.
    """

    MIN_REFRESH_SECONDS = 300

    def __init__(self, path: Optional[str] = None) -> None:
        base = Path(getattr(Config, "DATA_DIR", "app/v17/storage"))
        self.path = Path(path) if path else base / "shadow_decisions.jsonl"
        self._last_written: Dict[str, Tuple[Tuple[Any, ...], float]] = {}
        self._lock = RLock()

    def record(self, payload: Dict[str, Any]) -> None:
        if not bool(getattr(Config, "SHADOW_MODE", False)):
            return
        fixture_id = str(payload.get("fixture_id") or payload.get("match_id") or "")
        if not fixture_id:
            return
        status = "SHADOW_VALIDATED" if payload.get("official_can_publish") else str(payload.get("decision_status") or "NO_BET")
        reasons = list(dict.fromkeys(
            str(x) for x in (
                (payload.get("decision_reason_codes") or [])
                or (payload.get("official_blockers") or [])
                or (payload.get("official_warnings") or [])
            ) if x
        ))[:8]
        status_key = (status, payload.get("home_score"), payload.get("away_score"),
                      str(payload.get("suggested_market") or ""), tuple(reasons))
        now = time.time()
        with self._lock:
            previous = self._last_written.get(fixture_id)
            if previous and previous[0] == status_key and now - previous[1] < self.MIN_REFRESH_SECONDS:
                return
            # This is a best-effort research journal; it never affects the
            # source of truth for active/official signals.
            entry = {
                "recorded_at": now_iso(),
                "fixture_id": fixture_id,
                "home_team": payload.get("home_team"),
                "away_team": payload.get("away_team"),
                "country": payload.get("country"),
                "league": payload.get("league"),
                "api_minute": payload.get("api_minute"),
                "home_score": payload.get("home_score"),
                "away_score": payload.get("away_score"),
                "decision_status": status,
                "suggested_market": payload.get("suggested_market"),
                "candidate_score": payload.get("candidate_score"),
                "data_truth_status": payload.get("data_truth_status"),
                "decision_reason_codes": reasons,
                "main_reading": str(payload.get("main_reading") or "")[:450],
                "prediction_status": payload.get("prediction_status", "N/A"),
                "model_version": payload.get("math_engine_version"),
                "calibration_status": payload.get("calibration_status", "NOT_VALIDATED_OUT_OF_SAMPLE"),
                "primary_final_score": payload.get("primary_final_score") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "probability_next_goal": payload.get("probability_next_goal") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "probability_no_more_goals": payload.get("probability_no_more_goals") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "goal_next_5_probability": payload.get("goal_next_5_probability") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "goal_next_10_probability": payload.get("goal_next_10_probability") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "goal_next_15_probability": payload.get("goal_next_15_probability") if payload.get("prediction_status") == "EXPERIMENTAL" else None,
                "model_probability_for_exact_line": payload.get("model_probability"),
                "market_line": payload.get("line"),
                "market_period": payload.get("market_period"),
                "expected_goals_remaining": payload.get("expected_goals_remaining"),
                "would_pass_master": bool(payload.get("official_can_publish")),
                "shadow_mode": True,
                "official_can_publish": False,
                "result_status": "NOT_SETTLED_RESEARCH",
            }
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
                self._last_written[fixture_id] = (status_key, now)
                if len(self._last_written) > 5000:
                    self._last_written.clear()
            except OSError:
                # A full disk must not interrupt a LIVE analysis cycle.
                pass

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Read a bounded tail, never scan a potentially multi-GB old journal."""
        if not self.path.is_file():
            return []
        try:
            with self.path.open("rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                offset = max(0, size - 2_000_000)
                fh.seek(offset)
                if offset:
                    fh.readline()  # discard the partial first record
                lines = fh.readlines()
            records = []
            for line in reversed(lines):
                if len(records) >= max(1, min(int(limit), 100)):
                    break
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(row, dict):
                    continue
                # Old versions contain a full match snapshot; expose only
                # safe whitelisted fields from those records as well.
                records.append({
                    "recorded_at": row.get("recorded_at") or row.get("decision_timestamp"),
                    "fixture_id": row.get("fixture_id") or row.get("match_id"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "country": row.get("country"),
                    "league": row.get("league"),
                    "api_minute": row.get("api_minute"),
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                    "decision_status": row.get("decision_status"),
                    "suggested_market": row.get("suggested_market"),
                    "candidate_score": row.get("candidate_score"),
                    "data_truth_status": row.get("data_truth_status"),
                    "decision_reason_codes": row.get("decision_reason_codes", []),
                    "main_reading": row.get("main_reading"),
                    "prediction_status": row.get("prediction_status", "N/A"),
                    "model_version": row.get("model_version"),
                    "calibration_status": row.get("calibration_status", "NOT_VALIDATED_OUT_OF_SAMPLE"),
                    "primary_final_score": row.get("primary_final_score") if row.get("prediction_status") == "EXPERIMENTAL" else None,
                    "probability_next_goal": row.get("probability_next_goal") if row.get("prediction_status") == "EXPERIMENTAL" else None,
                    "probability_no_more_goals": row.get("probability_no_more_goals"),
                    "goal_next_5_probability": row.get("goal_next_5_probability"),
                    "goal_next_10_probability": row.get("goal_next_10_probability"),
                    "goal_next_15_probability": row.get("goal_next_15_probability"),
                    "shadow_mode": True,
                    "official_can_publish": False,
                    "result_status": "NOT_SETTLED_RESEARCH",
                })
            return records
        except OSError:
            return []


class CalibrationMetrics:
    """Diagnostics for settled binary events, NEVER official confidence.

    ``official_confidence`` is an evidence-quality score, not a forecast
    probability. The only admissible input is a stored model_probability for
    the *exact event that was resolved* (WON/LOST). Missing probabilities are
    excluded, not interpreted as 0% or as perfect calibration.
    """

    @staticmethod
    def evaluate(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        pairs: List[Tuple[float, float]] = []
        for item in records:
            result = str(item.get("result_status") or item.get("result") or "").upper()
            if result not in {"WON", "LOST"}:
                continue
            value = item.get("model_probability")
            if value is None or value == "":
                continue
            try:
                p = float(value)
            except (ValueError, TypeError, OverflowError):
                continue
            if not math.isfinite(p) or p < 0 or p > 100:
                continue
            if p > 1:
                p /= 100.0
            p = max(1e-6, min(1 - 1e-6, p))
            pairs.append((p, 1.0 if result == "WON" else 0.0))
        if not pairs:
            return {"brier_score": None, "log_loss": None, "calibration_error": None,
                    "samples": 0, "calibration_status": "INSUFFICIENT_DATA"}
        brier = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
        logloss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for p, y in pairs) / len(pairs)
        bins: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
        for p, y in pairs:
            bins[min(9, int(p * 10))].append((p, y))
        ece = 0.0
        for values in bins.values():
            avg_p = sum(p for p, _ in values) / len(values)
            avg_y = sum(y for _, y in values) / len(values)
            ece += (len(values) / len(pairs)) * abs(avg_p - avg_y)
        return {
            "brier_score": round(brier, 5),
            "log_loss": round(logloss, 5),
            "calibration_error": round(ece, 5),
            "samples": len(pairs),
            "calibration_status": "UNVALIDATED_DIAGNOSTIC",
        }
