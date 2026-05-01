from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from app.services.app_container import app_container

logger = logging.getLogger("JHONNY_ELITE_V16")

SCAN_INTERVAL_SECONDS = 15


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _match_name(item: Dict[str, Any]) -> str:
    return _text(
        item.get("match_name")
        or item.get("partido")
        or item.get("nombre_del_partido")
        or item.get("nombre_partido")
        or item.get("match")
    )


def _minute(item: Dict[str, Any]) -> int:
    return _safe_int(
        item.get("minute")
        or item.get("minuto")
        or item.get("current_minute")
        or item.get("match_minute")
        or item.get("final_minute")
    )


def _market(item: Dict[str, Any]) -> str:
    return _text(item.get("market") or item.get("mercado"), "N/A")


def _rank(item: Dict[str, Any]) -> str:
    return _text(item.get("rank") or item.get("rango"), "N/A")


def _reason(item: Dict[str, Any]) -> str:
    return _text(
        item.get("reason")
        or item.get("motivo")
        or item.get("block_reason")
        or item.get("razon_bloqueo")
        or item.get("close_reason"),
        "N/A",
    )


def _ai_score(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("ai_score") or item.get("puntuación_ai"))


def _goal_prob(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("goal_probability") or item.get("probabilidad_de_gol"))


def _over_prob(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("over_probability") or item.get("sobre_probabilidad"))


def _under_prob(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("under_probability") or item.get("bajo_probabilidad"))


def _risk_level(item: Dict[str, Any]) -> str:
    return _text(item.get("risk_level") or item.get("nivel_de_riesgo"), "N/A")


def _risk_score(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("risk_score") or item.get("puntuación_riesgo"))


def _data_quality(item: Dict[str, Any]) -> str:
    return _text(item.get("data_quality") or item.get("calidad_datos"), "N/A")


def _context_state(item: Dict[str, Any]) -> str:
    return _text(item.get("context_state") or item.get("estado_del_contexto"), "N/A")


def _odds(item: Dict[str, Any]) -> float:
    return _safe_float(item.get("odds") or item.get("cuotas"))


def _line(item: Dict[str, Any]) -> str:
    return _text(item.get("line") or item.get("línea"), "AUTO")


def _score(item: Dict[str, Any]) -> str:
    score = item.get("score") or item.get("marcador") or item.get("final_score")
    if score:
        return str(score)

    home = _safe_int(
        item.get("home_score")
        or item.get("local_score")
        or item.get("marcador_local")
    )
    away = _safe_int(
        item.get("away_score")
        or item.get("visitante_score")
        or item.get("marcador_visitante")
    )
    return f"{home}-{away}"


def _signal_key(item: Dict[str, Any]) -> str:
    return _text(item.get("signal_key") or item.get("signal_id") or item.get("opportunity_id"), "")


def _log_live_matches_preview(live_matches: List[Dict[str, Any]]) -> None:
    preview = live_matches[:8]

    for match in preview:
        logger.warning(
            "LIVE | %s | min=%s | score=%s | dq=%s | shots=%s | sot=%s | corners=%s | xg=%s | scannable=%s | source=%s",
            _match_name(match),
            _minute(match),
            _score(match),
            _data_quality(match),
            _safe_float(match.get("shots")),
            _safe_float(match.get("shots_on_target")),
            _safe_float(match.get("corners")),
            _safe_float(match.get("xg") or match.get("xG")),
            _text(match.get("is_scannable") or match.get("es_escaneable")),
            _text(match.get("stats_source") or match.get("fuente_estadísticas")),
        )

    remaining = max(len(live_matches) - len(preview), 0)
    if remaining > 0:
        logger.warning("LIVE | ... %s partidos más no mostrados en preview", remaining)


def _log_published_signals(signals: List[Dict[str, Any]]) -> None:
    if not signals:
        return

    for signal in signals:
        logger.warning(
            "SEÑAL | %s | market=%s | min=%s | score=%s | rank=%s | ai=%.2f | goal=%.2f | over=%.2f | under=%.2f | risk=%s(%.2f) | odds=%.2f | line=%s | reason=%s",
            _match_name(signal),
            _market(signal),
            _minute(signal),
            _score(signal),
            _rank(signal),
            _ai_score(signal),
            _goal_prob(signal),
            _over_prob(signal),
            _under_prob(signal),
            _risk_level(signal),
            _risk_score(signal),
            _odds(signal),
            _line(signal),
            _reason(signal),
        )


def _log_closed_signals(closed_signals: List[Dict[str, Any]]) -> None:
    if not closed_signals:
        return

    for signal in closed_signals:
        logger.warning(
            "CERRADA | %s | key=%s | market=%s | result=%s | entry_score=%s | final_score=%s | reason=%s",
            _match_name(signal),
            _signal_key(signal),
            _market(signal),
            _text(signal.get("resultado") or signal.get("status")),
            _text(signal.get("entry_score")),
            _text(signal.get("final_score") or signal.get("score")),
            _reason(signal),
        )


def _log_opportunities(opportunities: List[Dict[str, Any]]) -> None:
    if not opportunities:
        return

    preview = opportunities[:12]

    for opp in preview:
        logger.warning(
            "OBSERVE | %s | min=%s | score=%s | type=%s | rank=%s | ai=%.2f | goal=%.2f | over=%.2f | under=%.2f | risk=%s(%.2f) | dq=%s | ctx=%s | market=%s | reason=%s",
            _match_name(opp),
            _minute(opp),
            _score(opp),
            _text(opp.get("type") or opp.get("tipo"), "OBSERVE"),
            _rank(opp),
            _ai_score(opp),
            _goal_prob(opp),
            _over_prob(opp),
            _under_prob(opp),
            _risk_level(opp),
            _risk_score(opp),
            _data_quality(opp),
            _context_state(opp),
            _market(opp),
            _reason(opp),
        )

    remaining = max(len(opportunities) - len(preview), 0)
    if remaining > 0:
        logger.warning("OBSERVE | ... %s oportunidades más no mostradas en preview", remaining)


def _log_blocked(blocked: List[Dict[str, Any]]) -> None:
    if not blocked:
        return

    preview = blocked[:12]

    for item in preview:
        logger.warning(
            "DESCARTE | %s | min=%s | score=%s | motivo=%s",
            _match_name(item),
            _minute(item),
            _score(item),
            _reason(item),
        )

    remaining = max(len(blocked) - len(preview), 0)
    if remaining > 0:
        logger.warning("DESCARTE | ... %s bloqueados más no mostrados en preview", remaining)


def _log_cycle_snapshot(
    live_matches: List[Dict[str, Any]],
    published_signals: List[Dict[str, Any]],
    opportunities: List[Dict[str, Any]],
    blocked: List[Dict[str, Any]],
    active_signals: List[Dict[str, Any]],
    closed_signals: List[Dict[str, Any]],
) -> None:
    over_count = 0
    under_count = 0

    for signal in published_signals:
        market = _market(signal).upper()
        if "OVER" in market:
            over_count += 1
        elif "UNDER" in market:
            under_count += 1

    logger.warning(
        "SNAPSHOT | live=%s | published=%s | over=%s | under=%s | observe=%s | blocked=%s | active=%s | closed=%s",
        len(live_matches),
        len(published_signals),
        over_count,
        under_count,
        len(opportunities),
        len(blocked),
        len(active_signals),
        len(closed_signals),
    )


def _register_closed_signals_in_history(
    history_service: Any,
    closed_signals: List[Dict[str, Any]],
) -> int:
    """
    Manda señales cerradas al historial.

    Primero intenta actualizar la señal si ya existía.
    Si no existía, la registra y luego la actualiza.
    """
    saved = 0

    for closed in closed_signals:
        if not isinstance(closed, dict):
            continue

        signal_key = (
            closed.get("signal_key")
            or closed.get("signal_id")
            or closed.get("opportunity_id")
        )

        result = str(closed.get("resultado") or closed.get("status") or "").upper()

        if not signal_key:
            continue

        if result not in {"WIN", "LOSS", "PUSH", "VOID", "REMOVED"}:
            continue

        try:
            history_service.update_result(
                signal_key=str(signal_key),
                result=result,
                extra=closed,
            )
            saved += 1
        except Exception:
            try:
                history_service.register_published_signal(closed)
                history_service.update_result(
                    signal_key=str(signal_key),
                    result=result,
                    extra=closed,
                )
                saved += 1
            except Exception as exc:
                logger.warning(
                    "WORKER: no se pudo guardar señal cerrada en historial | key=%s | error=%s",
                    signal_key,
                    exc,
                )

    return saved


def run_worker() -> None:
    """
    Ciclo vivo del sistema.

    Flujo:
    1. Obtiene partidos live.
    2. Escanea señales.
    3. Registra señales publicadas en historial.
    4. Sincroniza señales activas.
    5. Cierra señales cumplidas.
    6. Guarda señales cerradas en resultados.
    7. Actualiza estado del panel.
    """
    runtime_state = app_container.runtime_state
    fetcher = app_container.live_fetcher
    scan_service = app_container.scan_service
    live_signal_manager = app_container.live_signal_manager
    history_service = app_container.history_service

    logger.warning(
        "WORKER JHONNY_ELITE_V16 iniciado | intervalo=%ss",
        SCAN_INTERVAL_SECONDS,
    )

    while True:
        try:
            logger.warning("🔄 NUEVO CICLO DE ESCANEO")

            live_matches = fetcher.get_live_matches() or []
            logger.warning("⚽ PARTIDOS EN VIVO: %s", len(live_matches))

            if live_matches:
                _log_live_matches_preview(live_matches)

            scan_result = scan_service.scan(live_matches) or {}

            published_signals = scan_result.get("published_signals", []) or []
            opportunities = scan_result.get("opportunities", []) or []
            blocked = scan_result.get("blocked", []) or []
            scan_stats = scan_result.get("stats", {}) or {}

            logger.warning("📌 CANDIDATAS PUBLICADAS: %s", len(published_signals))
            logger.warning("👁️ OPORTUNIDADES: %s", len(opportunities))
            logger.warning("⛔ BLOQUEADOS: %s", len(blocked))

            _log_published_signals(published_signals)
            _log_opportunities(opportunities)
            _log_blocked(blocked)

            for signal in published_signals:
                history_service.register_published_signal(signal)

            sync_stats = live_signal_manager.sync(
                published_signals=published_signals
            )

            closed_finished = live_signal_manager.resolve_finished_matches(
                live_matches
            )

            closed_signals = []
            if hasattr(live_signal_manager, "pop_recently_closed"):
                closed_signals = live_signal_manager.pop_recently_closed() or []

            _log_closed_signals(closed_signals)

            closed_saved = _register_closed_signals_in_history(
                history_service=history_service,
                closed_signals=closed_signals,
            )

            active_signals = live_signal_manager.get_active_signals()

            runtime_state.update_live_matches(live_matches)
            runtime_state.update_active_signals(active_signals)
            runtime_state.update_opportunities(opportunities)
            runtime_state.update_blocked(blocked)

            history_stats = history_service.get_stats()

            runtime_state.update_stats(
                {
                    **history_stats,
                    **scan_stats,
                    "sync_created": sync_stats.get("created", 0),
                    "sync_updated": sync_stats.get("updated", 0),
                    "sync_invalidated": sync_stats.get("invalidated", 0),
                    "closed_finished_matches": closed_finished,
                    "closed_signals_saved": closed_saved,
                    "live_matches_count": len(live_matches),
                    "active_signals_count": len(active_signals),
                    "updated_at": utc_now_iso(),
                    "scan_interval_seconds": SCAN_INTERVAL_SECONDS,
                }
            )

            runtime_state.set_health_ok()

            _log_cycle_snapshot(
                live_matches=live_matches,
                published_signals=published_signals,
                opportunities=opportunities,
                blocked=blocked,
                active_signals=active_signals,
                closed_signals=closed_signals,
            )

            logger.info(
                "WORKER: ciclo OK | interval=%ss | live=%s | published=%s | opps=%s | blocked=%s | active=%s | closed=%s | saved=%s | history=%s | sync(created=%s updated=%s invalidated=%s)",
                SCAN_INTERVAL_SECONDS,
                len(live_matches),
                len(published_signals),
                len(opportunities),
                len(blocked),
                len(active_signals),
                len(closed_signals),
                closed_saved,
                history_stats.get("history_items", 0),
                sync_stats.get("created", 0),
                sync_stats.get("updated", 0),
                sync_stats.get("invalidated", 0),
            )

        except Exception as exc:
            logger.exception("WORKER: ciclo falló: %s", exc)
            runtime_state.set_health_error(str(exc))

        time.sleep(SCAN_INTERVAL_SECONDS)


def iniciar_worker() -> None:
    """
    Alias compatible con main.py
    """
    run_worker()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    run_worker()
