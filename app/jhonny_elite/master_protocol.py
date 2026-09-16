from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from app.config.config import Config


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


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

        shots = sf(match.get("shots") or match.get("total_shots"), -1)
        sot = sf(match.get("shots_on_target") or match.get("total_shots_on"), -1)
        dangerous = sf(match.get("dangerous_attacks") or match.get("total_dangerous_attacks"), -1)
        xg = sf(match.get("xg") or match.get("xG"), -1)
        minute = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)
        has_live_stats = bool(match.get("has_live_stats"))

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

        data_age = sf(
            match.get("data_age_seconds")
            or match.get("stats_age_seconds")
            or match.get("api_data_age_seconds"),
            0.0,
        )
        if (
            data_age > sf(getattr(Config, "MAX_LIVE_DATA_AGE_SECONDS", 150), 150)
            and not (clock.get("timestamp_missing") and clock.get("stats_confirmed"))
        ):
            score -= 35
            issues.append("STALE_SOURCE")

        score = clamp(score)
        if score >= 90:
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
    shots: float
    sot: float
    dangerous: float
    corners: float
    xg: float


class TemporalMatchMemory:
    """Stores rolling live snapshots and exposes 5/10/15 minute windows."""

    def __init__(self, max_snapshots: int = 90) -> None:
        self.max_snapshots = max_snapshots
        self._memory: Dict[str, Deque[_Snapshot]] = defaultdict(lambda: deque(maxlen=self.max_snapshots))

    def enrich(self, match: Dict[str, Any]) -> Dict[str, Any]:
        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "")
        if not fixture_id:
            return match

        minute = si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0)
        ts = sf(match.get("fetched_at") or match.get("source_timestamp"), 0.0)
        if ts <= 0:
            ts = datetime.now(timezone.utc).timestamp()
        snap = _Snapshot(
            minute=minute,
            timestamp=ts,
            home_score=si(match.get("home_score"), 0),
            away_score=si(match.get("away_score"), 0),
            shots=sf(match.get("shots") or match.get("total_shots"), 0.0),
            sot=sf(match.get("shots_on_target") or match.get("total_shots_on"), 0.0),
            dangerous=sf(match.get("dangerous_attacks") or match.get("total_dangerous_attacks"), 0.0),
            corners=sf(match.get("corners"), 0.0),
            xg=sf(match.get("xg") or match.get("xG"), 0.0),
        )
        history = self._memory[fixture_id]
        if not history or history[-1].timestamp != snap.timestamp:
            history.append(snap)

        result = dict(match)
        for window in (5, 10, 15):
            result[f"window_{window}"] = self._window_metrics(history, snap, window)
        result["temporal_memory_points"] = len(history)
        result["temporal_memory_ready"] = len(history) >= 2
        return result

    def _window_metrics(self, history: Deque[_Snapshot], current: _Snapshot, window: int) -> Dict[str, Any]:
        if len(history) < 2:
            return {"available": False, "minutes": window}
        candidates = [x for x in history if current.minute - x.minute <= window and x.minute <= current.minute]
        if len(candidates) < 2:
            candidates = list(history)[-2:]
        first = candidates[0]
        elapsed = max(1, current.minute - first.minute)
        d_shots = max(0.0, current.shots - first.shots)
        d_sot = max(0.0, current.sot - first.sot)
        d_dangerous = max(0.0, current.dangerous - first.dangerous)
        d_corners = max(0.0, current.corners - first.corners)
        d_xg = max(0.0, current.xg - first.xg)
        d_goals = max(0, (current.home_score + current.away_score) - (first.home_score + first.away_score))
        threat = clamp(
            d_sot * 18.0 + d_shots * 4.0 + d_dangerous * 1.0 + d_corners * 4.0 + d_xg * 28.0,
            0,
            100,
        )
        return {
            "available": True,
            "minutes": window,
            "observed_minutes": elapsed,
            "delta_shots": round(d_shots, 2),
            "delta_sot": round(d_sot, 2),
            "delta_dangerous_attacks": round(d_dangerous, 2),
            "delta_corners": round(d_corners, 2),
            "delta_xg": round(d_xg, 3),
            "delta_goals": d_goals,
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
        if odds.get("odds_available") and not odds.get("has_positive_value"):
            add("MARKET_VALUE_LOST", "CRITICAL")
        if odds.get("odds_available") and sf(odds.get("odds_age_seconds"), 0) > sf(getattr(Config, "MAX_ODDS_AGE_SECONDS", 180), 180):
            add("STALE_ODDS", "CRITICAL")

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

        if hard:
            return self._result("BLOCKED", "NO_BET", 0.0, "EXTREME", False, "Bloqueo crítico: " + ", ".join(sorted(set(hard))[:5]), line, price, match, math_evidence, odds, hard, [])
        if not candidate or market == "NO_BET":
            status = "OBSERVATION" if candidate_score >= sf(getattr(Config, "OBSERVATION_MIN_SCORE", 45), 45) else "NO_BET"
            return self._result(status, "NO_BET", candidate_score, "MEDIUM", False, "Sin ventaja suficiente; continuar observando.", line, price, match, math_evidence, odds, [], [])
        if enrichment_deferred:
            return self._result("OPPORTUNITY", "NO_BET", candidate_score, "LOW", False, "Candidato real en cola Economy; falta enriquecimiento.", line, price, match, math_evidence, odds, [], ["ECONOMY_QUEUE"])

        math_support = sf(math_evidence.get("math_support_over" if market == "OVER" else "math_support_under"), 50.0)
        pre_support = sf(pre_match.get("over_pre_match_score" if market == "OVER" else "under_pre_match_score"), 50.0)
        if not pre_match.get("pre_match_available"):
            pre_support = 50.0
        risk_score = sf(risk.get("risk_score"), 50.0)
        live_quality = sf(data_truth.get("data_truth_score"), 50.0)
        value_edge = sf(odds.get("value_edge"), 0.0)
        expected_value = sf(odds.get("expected_value"), value_edge / 100.0)

        # Five-layer consensus: tactical, context, goal/rhythm, value, market.
        layers = {
            "TACTICAL": sf(tactical.get("tactical_score"), 0) >= 55,
            "CONTEXT": (sf(context.get("over_context_score"), 0) >= 58 if market == "OVER" else sf(context.get("under_context_score"), 0) >= 58),
            "GOAL_RHYTHM": (sf(context.get("rhythm_score"), 0) >= 55 or sf(match.get("recent_threat_score"), 0) >= 55) if market == "OVER" else (sf(context.get("rhythm_score"), 100) <= 48 and sf(match.get("recent_threat_score"), 100) <= 48),
            "VALUE": bool(odds.get("has_positive_value")) and value_edge >= sf(getattr(Config, "EDGE_MIN_PERCENT", 4.0), 4.0),
            "MARKET": bool(odds.get("odds_available")) and line > 0 and sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50) <= price <= sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10),
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
        market_ready = bool(odds.get("odds_available")) and line > 0 and low_price <= price <= high_price
        edge_floor = sf(getattr(Config, "EDGE_MIN_PERCENT", 5.0), 5.0)
        ev_floor = sf(getattr(Config, "MIN_EXPECTED_VALUE", 0.03), 0.03)
        value_ready = bool(odds.get("has_positive_value")) and value_edge >= edge_floor and expected_value >= ev_floor

        consensus_required = 5 if market == "UNDER" else int(getattr(Config, "MASTER_MIN_CONSENSUS", 4))
        consensus_ready = consensus >= consensus_required
        math_floor = sf(getattr(Config, "MIN_MATH_SUPPORT_UNDER", 70.0), 70.0) if market == "UNDER" else sf(getattr(Config, "MIN_MATH_SUPPORT_OVER", 72.0), 72.0)
        math_ready = math_support >= math_floor
        data_ready = live_quality >= sf(getattr(Config, "MIN_DATA_TRUTH_SCORE", 72.0), 72.0)
        risk_ready = risk_score <= sf(getattr(Config, "MAX_SIGNAL_RISK_SCORE", 45.0), 45.0)
        prematch_ready = prematch_available or not bool(getattr(Config, "REQUIRE_PREMATCH_FOR_OFFICIAL", True))

        # Fragilidad de linea UNDER: si queda menos de un gol completo de margen,
        # una sola accion destruye la apuesta y no se publica.
        current_total = si(match.get("home_score"), 0) + si(match.get("away_score"), 0)
        line_margin = line - current_total if line > 0 else -999.0
        under_line_ready = market != "UNDER" or line_margin >= 1.0
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
            and under_line_ready
            and late_under_ready
        )

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
    """Records shadow decisions separately; never publishes them."""

    def __init__(self, path: Optional[str] = None) -> None:
        base = Path(getattr(Config, "DATA_DIR", "app/v17/storage"))
        self.path = Path(path) if path else base / "shadow_decisions.jsonl"

    def record(self, payload: Dict[str, Any]) -> None:
        if not bool(getattr(Config, "SHADOW_MODE", False)):
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            shadow = deepcopy(payload)
            shadow["shadow_mode"] = True
            shadow["official_can_publish"] = False
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(shadow, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass


class CalibrationMetrics:
    """Small native calibration helper used by reports/tests."""

    @staticmethod
    def evaluate(records: Iterable[Dict[str, Any]]) -> Dict[str, float]:
        pairs: List[Tuple[float, float]] = []
        for item in records:
            result = str(item.get("result_status") or item.get("result") or "").upper()
            if result not in {"WON", "LOST"}:
                continue
            p = sf(item.get("model_probability") or item.get("official_confidence"), 0.0)
            if p > 1:
                p /= 100.0
            p = max(1e-6, min(1 - 1e-6, p))
            y = 1.0 if result == "WON" else 0.0
            pairs.append((p, y))
        if not pairs:
            return {"brier_score": 0.0, "log_loss": 0.0, "calibration_error": 0.0, "samples": 0}
        brier = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
        logloss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for p, y in pairs) / len(pairs)
        # 10-bin expected calibration error.
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
        }
