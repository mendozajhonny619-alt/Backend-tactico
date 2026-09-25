from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config.config import Config

logger = logging.getLogger(__name__)


class OfficialResultsStore:
    """Persistencia durable opcional para resultados oficiales.

    - Si DATABASE_URL apunta a PostgreSQL, los resultados sobreviven deploys,
      reinicios y spin-down del web service.
    - Si no hay DATABASE_URL, SignalTracker mantiene el archivo JSON local como
      fallback. Esto permite desarrollo local, pero en hosts con filesystem
      efimero se recomienda configurar PostgreSQL o un disco persistente.
    """

    TABLE = "jhonny_elite_official_results"

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = str(database_url if database_url is not None else getattr(Config, "DATABASE_URL", "") or "").strip()
        self.enabled = self.database_url.startswith("postgres://") or self.database_url.startswith("postgresql://")
        self._initialized = False

    def _connect(self):
        if not self.enabled:
            return None
        try:
            import psycopg
            return psycopg.connect(self.database_url, connect_timeout=5)
        except Exception as exc:
            logger.warning("OfficialResultsStore PostgreSQL unavailable: %s", exc)
            return None

    def _ensure_schema(self, conn) -> bool:
        if self._initialized:
            return True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.TABLE} (
                        signal_id TEXT PRIMARY KEY,
                        signal_key TEXT,
                        resolved_at TIMESTAMPTZ,
                        result_day_key TEXT,
                        result_status TEXT,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_resolved_at ON {self.TABLE}(resolved_at DESC)")
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_day ON {self.TABLE}(result_day_key)")
            conn.commit()
            self._initialized = True
            return True
        except Exception as exc:
            logger.warning("OfficialResultsStore schema error: %s", exc)
            return False

    def load(self, limit: int = 5000) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        conn = self._connect()
        if conn is None:
            return []
        try:
            if not self._ensure_schema(conn):
                return []
            with conn.cursor() as cur:
                cur.execute(f"SELECT payload FROM {self.TABLE} ORDER BY resolved_at DESC NULLS LAST, updated_at DESC LIMIT %s", (int(limit),))
                rows = cur.fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                payload = row[0]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict):
                    result.append(payload)
            return result
        except Exception as exc:
            logger.warning("OfficialResultsStore load error: %s", exc)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def upsert(self, item: Dict[str, Any]) -> bool:
        if not self.enabled or not isinstance(item, dict):
            return False
        signal_id = str(item.get("signal_id") or "").strip()
        if not signal_id:
            return False
        conn = self._connect()
        if conn is None:
            return False
        try:
            if not self._ensure_schema(conn):
                return False
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.TABLE}
                        (signal_id, signal_key, resolved_at, result_day_key, result_status, payload, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (signal_id) DO UPDATE SET
                        signal_key = EXCLUDED.signal_key,
                        resolved_at = EXCLUDED.resolved_at,
                        result_day_key = EXCLUDED.result_day_key,
                        result_status = EXCLUDED.result_status,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (
                        signal_id,
                        str(item.get("signal_key") or ""),
                        item.get("resolved_at"),
                        str(item.get("result_day_key") or ""),
                        str(item.get("result_status") or ""),
                        json.dumps(item, ensure_ascii=False, default=str),
                    ),
                )
            conn.commit()
            return True
        except Exception as exc:
            logger.warning("OfficialResultsStore upsert error: %s", exc)
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass
