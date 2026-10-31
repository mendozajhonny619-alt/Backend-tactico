"""V3.6: durable, explicitly non-official outcome monitoring for live forecasts.

Never publishes a betting signal or relaxes MasterDecisionAI. One immutable
prediction per fixture/entry score/event is recorded only while the game is
live. Results are settled only on a *verified final fixture snapshot*, avoiding
hindsight and interpreting a live goal as a prematurely successful prediction.

Events are research contracts, NOT bookmaker markets:
  GOAL_REMAINING_FT   - at least one more goal before final whistle
  NO_GOAL_REMAINING_FT - zero further goals before final whistle
  EXACT_SCORE_FT     - the primary model score equals the final score
A research observation does not require odds and is never an official pick.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from app.config.config import Config


FINISHED = {"FT"}  # AET/PEN can contain non-90-minute scores: not interchangeable.
UNSETTLEABLE = {"AET", "PEN", "CANC", "ABD", "AWD", "WO", "PST"}
OPEN = {"1H", "2H", "LIVE"}
ALLOWED_DATA_QUALITY = {"HIGH", "EXCELLENT"}
MAX_EPISODES_PER_FIXTURE = 3


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool) or value == "":
            return None
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _score(value: Any) -> Optional[int]:
    x = _number(value)
    return int(x) if x is not None and x >= 0 and x.is_integer() else None


def _p(value: Any) -> Optional[float]:
    x = _number(value)
    return round(x, 4) if x is not None and 0 <= x <= 100 else None


def _fixture(row: Dict[str, Any]) -> str:
    return str(row.get("match_id") or row.get("fixture_id") or "").strip()


def _date(value: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def _entry(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Accept only live and evidence-gated experimental readings."""
    fid = _fixture(row)
    if not fid or row.get("tracking_only_terminal") or row.get("prediction_status") != "EXPERIMENTAL":
        return None
    if str(row.get("status_short") or "").upper() not in OPEN:
        return None
    if str(row.get("decision_status") or "").upper() not in {"STRONG_CANDIDATE", "CANDIDATE", "SHADOW"}:
        return None
    if str(row.get("data_truth_status") or "").upper() not in ALLOWED_DATA_QUALITY:
        return None
    # Ignore untrusted live context, even for non-operable research predictions.
    if row.get("clock_stale") or row.get("clock_frozen") or row.get("clock_blockers"):
        return None
    if any(str(x).upper() in {"CLOCK_NOT_TRUSTED", "SCORE_CONFLICT", "DATA_CONFLICTED", "LIVE_DATA_TOO_OLD", "MATCH_END_TIME_UNVERIFIED"}
           for x in row.get("prediction_evidence_gaps") or []):
        return None
    age = _number(row.get("data_age_seconds"))
    if age is not None and age > max(20, float(getattr(Config, "MAX_LIVE_DATA_AGE_SECONDS", 150))):
        return None
    minute = _score(row.get("effective_minute") if row.get("effective_minute") is not None else row.get("api_minute"))
    home, away = _score(row.get("home_score")), _score(row.get("away_score"))
    if minute is None or minute < 1 or minute >= 96 or home is None or away is None:
        return None
    direction = str(row.get("suggested_market") or "").upper().strip()
    if direction not in {"OVER", "UNDER"} or (direction == "UNDER" and minute < 60):
        return None
    event_type = "GOAL_REMAINING_FT" if direction == "OVER" else "NO_GOAL_REMAINING_FT"
    prob = _p(row.get("probability_next_goal") if direction == "OVER" else row.get("probability_no_more_goals"))
    if prob is None:
        return None
    primary = str(row.get("primary_final_score") or "")
    ft_prob = _p(row.get("primary_score_probability"))
    if not re.fullmatch(r"\d+-\d+", primary) or ft_prob is None:
        primary, ft_prob = None, None
    if primary:
        expected_home, expected_away = [int(x) for x in primary.split("-")]
        if expected_home < home or expected_away < away:
            # A model forecast that undoes an already-confirmed goal is
            # internally inconsistent, so reject the entire observation.
            return None
    return {
        "fixture_id": fid, "entry_home": home, "entry_away": away,
        "entry_minute": minute, "entry_score": f"{home}-{away}",
        "market_direction": direction, "event_type": event_type,
        "event_probability": prob, "primary_score": primary,
        "primary_probability": ft_prob,
        "candidate_score": _number(row.get("candidate_score")),
        "model_version": str(row.get("math_engine_version") or "EXPERIMENTAL_UNKNOWN"),
        "data_quality": str(row.get("data_truth_status") or ""),
        "decision_status": str(row.get("decision_status") or ""),
        "home_team": str(row.get("home_team") or ""),
        "away_team": str(row.get("away_team") or ""),
        "league": str(row.get("league") or ""),
        "country": str(row.get("country") or ""),
    }


class ShadowOutcomeTracker:
    """Single-writer SQLite store; readers only query a small bounded window."""

    def __init__(self, path: str | Path | None = None) -> None:
        base = Path(getattr(Config, "DATA_DIR", "app/v17/storage"))
        self.path = Path(path) if path is not None else base / "shadow_outcomes_v36.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS forecasts (
                forecast_id TEXT PRIMARY KEY, fixture_id TEXT NOT NULL,
                event_type TEXT NOT NULL, market_direction TEXT NOT NULL,
                entry_score TEXT NOT NULL, entry_home INTEGER NOT NULL,
                entry_away INTEGER NOT NULL, entry_minute INTEGER NOT NULL,
                predicted_score TEXT, model_probability REAL NOT NULL,
                candidate_score REAL, model_version TEXT NOT NULL,
                data_quality TEXT NOT NULL, decision_status TEXT NOT NULL,
                home_team TEXT, away_team TEXT, league TEXT, country TEXT,
                created_at TEXT NOT NULL, result_status TEXT NOT NULL DEFAULT 'PENDING',
                result_reason TEXT, final_score TEXT, resolved_at TEXT,
                label_source TEXT, shadow_only INTEGER NOT NULL DEFAULT 1,
                UNIQUE(fixture_id,event_type,entry_score)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_shadow_fixture ON forecasts(fixture_id, result_status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_shadow_created ON forecasts(created_at DESC)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, analyzed: Iterable[Dict[str, Any]], *, per_cycle: int = 6) -> int:
        """Freeze at most six new research candidate episodes each cycle.

        No public signal is added, no quota/API is consumed, and the official
        publication tracker is never called.
        """
        readings: List[Dict[str, Any]] = []
        for raw in analyzed:
            if not isinstance(raw, dict):
                continue
            entry = _entry(raw)
            if entry:
                readings.append(entry)
        readings.sort(key=lambda x: (x["decision_status"] == "STRONG_CANDIDATE", x["candidate_score"] or 0.0), reverse=True)
        added = 0
        episode_slots = max(0, min(6, int(per_cycle)))
        created_fixtures = set()
        with self._lock, self._connect() as db:
            for r in readings:
                fid = r["fixture_id"]
                if fid in created_fixtures or len(created_fixtures) >= episode_slots:
                    continue
                prior = db.execute("""SELECT entry_score, entry_minute FROM forecasts
                    WHERE fixture_id=? AND event_type IN ('GOAL_REMAINING_FT','NO_GOAL_REMAINING_FT')
                    ORDER BY entry_minute DESC""", (fid,)).fetchall()
                if len(prior) >= MAX_EPISODES_PER_FIXTURE:
                    continue
                # Same score = same episode. Require a new score and elapsed
                # time before recording a new observation after a real goal.
                if prior and (prior[0]["entry_score"] == r["entry_score"]
                              or r["entry_minute"] - prior[0]["entry_minute"] < 5):
                    continue
                created_at = _utc()
                for kind, probability, predicted in (
                    (r["event_type"], r["event_probability"], None),
                    ("EXACT_SCORE_FT", r["primary_probability"], r["primary_score"]),
                ):
                    if probability is None or (kind == "EXACT_SCORE_FT" and not predicted):
                        continue
                    digest = sha256(f"{fid}:{kind}:{r['entry_score']}".encode("utf-8")).hexdigest()[:24]
                    cur = db.execute("""INSERT OR IGNORE INTO forecasts (
                        forecast_id,fixture_id,event_type,market_direction,entry_score,
                        entry_home,entry_away,entry_minute,predicted_score,model_probability,
                        candidate_score,model_version,data_quality,decision_status,
                        home_team,away_team,league,country,created_at,result_status
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING')""",
                        (digest, fid, kind, r["market_direction"], r["entry_score"],
                         r["entry_home"], r["entry_away"], r["entry_minute"],
                         predicted, probability, r["candidate_score"], r["model_version"],
                         r["data_quality"], r["decision_status"], r["home_team"],
                         r["away_team"], r["league"], r["country"], created_at))
                    added += cur.rowcount
                created_fixtures.add(fid)
        return added

    def resolve(self, snapshots: Iterable[Dict[str, Any]]) -> int:
        """Resolve ONLY from final fixture scores, not from live intermediates.

        AET/PEN, cancellation and retroactive score corrections are not counted
        as wins/losses. Missing fixtures remain pending, never invented as lost.
        """
        updates = 0
        with self._lock, self._connect() as db:
            for m in snapshots:
                if not isinstance(m, dict):
                    continue
                fid = _fixture(m)
                if not fid:
                    continue
                status = str(m.get("status_short") or m.get("short_status") or "").upper()
                if status not in FINISHED | UNSETTLEABLE:
                    continue
                final_home = _score(m.get("home_score"))
                final_away = _score(m.get("away_score"))
                pending = db.execute("SELECT * FROM forecasts WHERE fixture_id=? AND result_status='PENDING'", (fid,)).fetchall()
                for row in pending:
                    outcome, reason = "UNRESOLVED", "NO_VERIFIABLE_FT_SCORE"
                    if status in UNSETTLEABLE:
                        outcome, reason = "VOID", f"UNSUPPORTED_FINAL_STATUS_{status}"
                    elif final_home is not None and final_away is not None:
                        if final_home < row["entry_home"] or final_away < row["entry_away"]:
                            outcome, reason = "UNRESOLVED", "SCORE_CORRECTION_OR_CONFLICT"
                        else:
                            result_score = f"{final_home}-{final_away}"
                            if row["event_type"] == "EXACT_SCORE_FT":
                                won = result_score == row["predicted_score"]
                            else:
                                more_goals = final_home + final_away > row["entry_home"] + row["entry_away"]
                                won = more_goals if row["event_type"] == "GOAL_REMAINING_FT" else not more_goals
                            outcome, reason = ("WON" if won else "LOST"), "VERIFIED_FINAL_SCORE"
                    db.execute("""UPDATE forecasts SET result_status=?, result_reason=?,
                        final_score=?, resolved_at=?, label_source=? WHERE forecast_id=? AND result_status='PENDING'""",
                        (outcome, reason,
                         f"{final_home}-{final_away}" if final_home is not None and final_away is not None else None,
                         _utc(), "PROVIDER_FINAL_SCORE" if status == "FT" and outcome in {"WON", "LOST"} else None,
                         row["forecast_id"]))
                    updates += 1
            # Old unfinished matches are NOT scored as failures. Expire them
            # without result to avoid repeated API status calls forever.
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
            db.execute("""UPDATE forecasts SET result_status='UNRESOLVED',
                result_reason='NO_FINAL_VERIFIED_WITHIN_72H',resolved_at=?
                WHERE result_status='PENDING' AND created_at < ?""", (_utc(), cutoff))
        return updates

    def pending_fixture_ids(self, limit: int = 40) -> List[str]:
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT fixture_id,MAX(created_at) as newest FROM forecasts
                WHERE result_status='PENDING' GROUP BY fixture_id ORDER BY newest DESC LIMIT ?""",
                (max(0, min(100, int(limit))),)).fetchall()
        return [r["fixture_id"] for r in rows]

    def recent(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM forecasts ORDER BY created_at DESC LIMIT ?", (max(0, min(1000, int(limit))),)).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, limit: int = 250) -> Dict[str, Any]:
        """Full-history counts, but only bounded recent rows in the live feed."""
        rows = self.recent(limit)
        grouped: Dict[str, Dict[str, Any]] = {}
        with self._lock, self._connect() as db:
            count_rows = db.execute("""SELECT event_type,result_status,COUNT(*) AS cnt
                FROM forecasts GROUP BY event_type,result_status""").fetchall()
            total = int(db.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0])
            fixtures = int(db.execute("SELECT COUNT(DISTINCT fixture_id) FROM forecasts WHERE result_status='PENDING'").fetchone()[0])
        counts = {(r["event_type"],r["result_status"]):int(r["cnt"]) for r in count_rows}
        for event in ("GOAL_REMAINING_FT", "NO_GOAL_REMAINING_FT", "EXACT_SCORE_FT"):
            wins, losses = counts.get((event,"WON"),0), counts.get((event,"LOST"),0)
            grouped[event] = {
                "count": sum(v for (k,_),v in counts.items() if k==event),
                "won": wins, "lost": losses,
                "void": counts.get((event,"VOID"),0),
                "unresolved": counts.get((event,"UNRESOLVED"),0),
                "pending": counts.get((event,"PENDING"),0),
                "hit_rate_percent": round(100*wins/(wins+losses),2) if wins+losses else None,
            }
        return {
            "mode":"SHADOW_RESEARCH_ONLY",
            "production_calibration_status":"NOT_VALIDATED_OUT_OF_SAMPLE",
            "official_signals_created":0, "grouped":grouped,
            "pending_fixture_count":fixtures, "total_historical_forecasts":total,
            "research_diagnostics":self.research_diagnostics(),
            "rows":rows, "counts_cover_latest":len(rows),
            "is_complete_history":len(rows)==total,
        }

    def research_diagnostics(self) -> Dict[str, Any]:
        """Empirical forecast error, NOT a calibrated production model.

        Query aggregates in SQLite to avoid loading a potentially large history
        into 4GB RAM on the Windows laptop. Multiple forecasts per fixture
        are correlated; unique fixture count is reported separately.
        """
        square = "((model_probability/100.0)-(CASE WHEN result_status='WON' THEN 1.0 ELSE 0.0 END))"
        statement = f"""SELECT event_type, COUNT(*) AS n,
            COUNT(DISTINCT fixture_id) AS fixtures,
            AVG({square}*{square}) AS brier FROM forecasts
            WHERE result_status IN ('WON','LOST')
            AND label_source='PROVIDER_FINAL_SCORE'
            GROUP BY event_type"""
        with self._lock, self._connect() as db:
            rows = db.execute(statement).fetchall()
        groups = {r['event_type']: {
            'labeled_forecasts': int(r['n']),
            'distinct_fixtures': int(r['fixtures']),
            'brier_score': round(float(r['brier']), 6),
            'production_calibrated': False,
        } for r in rows}
        return {
            'basis': 'VERIFIED_FINAL_SCORE_ONLY',
            'method': 'EMPIRICAL_BRIER_DIAGNOSTIC_IN_SAMPLE',
            'requires_temporal_out_of_sample_validation': True,
            'production_calibrated': False,
            'groups': groups,
        }

    def query(
        self, *, range_key: str = "today", family: str = "goals",
        offset: int = 0, limit: int = 100,
    ) -> Dict[str, Any]:
        """Read-only, date-paged history. No external API calls.

        Filtering uses the forecast's entry date in America/La_Paz. Final
        settlements received after midnight remain attached to that day.
        """
        if range_key not in {"today","yesterday","three","seven","thirty","all"}:
            raise ValueError("INVALID_DATE_RANGE")
        if family not in {"goals","score"}:
            raise ValueError("INVALID_FORECAST_FAMILY")
        offset = max(0, min(100000, int(offset)))
        limit = max(1, min(200, int(limit)))
        local = datetime.now(ZoneInfo("America/La_Paz"))
        today = local.replace(hour=0,minute=0,second=0,microsecond=0)
        length = {"today":1,"yesterday":1,"three":3,"seven":7,"thirty":30,"all":None}[range_key]
        conditions = ["event_type" + ("='EXACT_SCORE_FT'" if family=="score" else " IN ('GOAL_REMAINING_FT','NO_GOAL_REMAINING_FT')")]
        params: List[Any] = []
        if length is not None:
            first = today-timedelta(days=(1 if range_key=="yesterday" else length-1))
            last = today if range_key=="yesterday" else today+timedelta(days=1)
            conditions.extend(["created_at>=?", "created_at<?"])
            params.extend([first.astimezone(timezone.utc).isoformat(), last.astimezone(timezone.utc).isoformat()])
        where = " AND ".join(conditions)
        with self._lock, self._connect() as db:
            total = int(db.execute(f"SELECT COUNT(*) FROM forecasts WHERE {where}",params).fetchone()[0])
            summary = db.execute(f"""SELECT result_status,COUNT(*) AS n FROM forecasts
                WHERE {where} GROUP BY result_status""",params).fetchall()
            matches = db.execute(f"""SELECT * FROM forecasts WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",params+[limit,offset]).fetchall()
        counts = {r["result_status"]:int(r["n"]) for r in summary}
        return {
            "ok":True,"mode":"SHADOW_RESEARCH_ONLY", "range":range_key,
            "family":family,"offset":offset,"limit":limit,"total":total,
            "has_more":offset+len(matches)<total,
            "rows":[dict(row) for row in matches],
            "summary":{"total":total,"won":counts.get("WON",0),"lost":counts.get("LOST",0),
                       "pending":counts.get("PENDING",0),"void":counts.get("VOID",0),
                       "unresolved":counts.get("UNRESOLVED",0)},
        }

    def export_research_jsonl(self, path: str | Path) -> int:
        """Offline export: research event probabilities, never real market odds."""
        dest = Path(path)
        count = 0
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT * FROM forecasts WHERE result_status IN ('WON','LOST')
                AND label_source='PROVIDER_FINAL_SCORE' ORDER BY created_at""").fetchall()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("w", encoding="utf-8") as file:
                for r in rows:
                    file.write(json.dumps({
                        "fixture_id": r["fixture_id"], "forecast_id": r["forecast_id"],
                        "event_type": r["event_type"], "period": "FT",
                        "model_version": r["model_version"],
                        "model_probability": r["model_probability"],
                        "result_status": r["result_status"],
                        "predicted_at": r["created_at"], "resolved_at": r["resolved_at"],
                        "entry_score": r["entry_score"], "final_score": r["final_score"],
                        "predicted_score": r["predicted_score"],
                        "label_source": "PROVIDER_FINAL_SCORE", "research_only": True,
                    }, ensure_ascii=False) + "\n")
                    count += 1
        return count
