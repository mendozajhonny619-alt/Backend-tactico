from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.config.config import Config
from app.services.app_container import app_container

logger = logging.getLogger("JHONNY_ELITE_WORKER")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_worker() -> None:
    """Continuous live scan.

    This worker never downloads pre-match information globally. The unified
    engine requests pre-match/odds only after a live candidate passes the first
    gate, which protects API quota while keeping global discovery broad.
    """
    interval = max(15, int(getattr(Config, "SCAN_INTERVAL_SECONDS", 30)))
    state = app_container.runtime_state
    fetcher = app_container.live_fetcher
    adapter = app_container.v17_dashboard_adapter

    post_goal_interval = max(15, int(getattr(Config, "POST_GOAL_RESCAN_SECONDS", 15)))
    previous_scores: dict[str, tuple[int, int]] = {}
    logger.info("JHONNY ELITE worker started | interval=%ss | post-goal=%ss", interval, post_goal_interval)

    while True:
        started = time.time()
        score_changed = False
        try:
            raw_live = fetcher.get_live_matches()

            # Detect score changes. The current cycle already analyzes the new score;
            # the next cycle is accelerated so the engine can read the post-goal shape.
            current_scores: dict[str, tuple[int, int]] = {}
            for item in raw_live:
                if not isinstance(item, dict):
                    continue
                fixture_id = str(item.get("match_id") or item.get("fixture_id") or "")
                if not fixture_id:
                    continue
                score = (int(item.get("home_score") or 0), int(item.get("away_score") or 0))
                current_scores[fixture_id] = score
                if fixture_id in previous_scores and previous_scores[fixture_id] != score:
                    score_changed = True
            previous_scores = current_scores

            # A fixture normally disappears from live=all when it ends. Query only
            # pending tracked fixtures so UNDER/OVER can be closed with the final score.
            live_ids = {str(x.get("match_id") or x.get("fixture_id") or "") for x in raw_live if isinstance(x, dict)}
            pending_ids = {
                str(x.get("match_id") or x.get("fixture_id") or "")
                for x in adapter.tracker.pending()
                if isinstance(x, dict)
            }
            missing_tracked = [x for x in pending_ids if x and x not in live_ids]
            tracking_snapshots = fetcher.get_fixture_statuses(missing_tracked) if missing_tracked else []

            dashboard = adapter.build_from_raw_matches(
                list(raw_live) + list(tracking_snapshots),
                source_status="LIVE_API",
            )

            live = dashboard.get("live_matches", []) or []
            signals = dashboard.get("top_signals", []) or []
            opportunities = (dashboard.get("observe", []) or []) + (dashboard.get("no_bet", []) or [])
            blocked = (dashboard.get("blocked", []) or []) + (dashboard.get("blocked_by_league", []) or [])
            stats = dashboard.get("stats", {}) or {}

            state.update_live_matches(live)
            state.update_active_signals(signals)
            state.update_opportunities(opportunities)
            state.update_blocked(blocked)
            state.update_stats({
                **stats,
                "updated_at": now_iso(),
                "scan_interval_seconds": interval,
                "cycle_seconds": round(time.time() - started, 3),
                "worker_mode": "JHONNY_ELITE_UNIFIED",
            })
            state.set_health_ok()

            logger.info(
                "cycle OK | live=%s signals=%s observe=%s blocked=%s precision=%s%%",
                len(live), len(signals), len(dashboard.get("observe", []) or []),
                len(blocked), stats.get("precision", 0),
            )
        except Exception as exc:
            logger.exception("worker cycle failed: %s", exc)
            state.set_health_error(str(exc))

        elapsed = time.time() - started
        next_interval = post_goal_interval if score_changed else interval
        time.sleep(max(1.0, next_interval - elapsed))


def iniciar_worker() -> None:
    run_worker()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    run_worker()

# Legacy compatibility: old dashboard modules may still import this helper.
def get_last_live_matches():
    return app_container.runtime_state.get_live_matches()
