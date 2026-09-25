from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import Config
from app.v17.api.routes import router as api_router
from app.v17.routes.v17_chat import router as chat_router
from worker import iniciar_worker

logger = logging.getLogger("JHONNY_ELITE_MAIN")
_worker_lock_handle = None


def _acquire_worker_lock() -> bool:
    """Prevent duplicate scanners without disabling the worker on Windows.

    Linux/Render uses ``fcntl`` while local Windows uses ``msvcrt``.  The old
    implementation imported ``fcntl`` unconditionally, so the API could start
    on Windows while the scanner silently remained read-only.
    """
    global _worker_lock_handle
    if not getattr(Config, "WORKER_SINGLE_PROCESS_ONLY", True):
        return True

    path = os.getenv("JHONNY_WORKER_LOCK") or os.path.join(
        tempfile.gettempdir(), "jhonny_elite_worker.lock"
    )
    try:
        _worker_lock_handle = open(path, "a+", encoding="utf-8")
        _worker_lock_handle.seek(0)

        if os.name == "nt":
            import msvcrt

            # msvcrt.locking needs at least one byte to lock.
            if not _worker_lock_handle.read(1):
                _worker_lock_handle.seek(0)
                _worker_lock_handle.write("0")
                _worker_lock_handle.flush()
            _worker_lock_handle.seek(0)
            msvcrt.locking(_worker_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(_worker_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        _worker_lock_handle.seek(0)
        _worker_lock_handle.truncate()
        _worker_lock_handle.write(str(os.getpid()))
        _worker_lock_handle.flush()
        return True
    except Exception as exc:
        try:
            if _worker_lock_handle is not None:
                _worker_lock_handle.close()
        except Exception:
            pass
        _worker_lock_handle = None
        logger.warning("worker lock not acquired; API process will stay read-only: %s", exc)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(Config, "WORKER_ENABLED", True) and _acquire_worker_lock():
        Thread(target=iniciar_worker, name="jhonny-elite-worker", daemon=True).start()
        logger.info("JHONNY ELITE live worker started")
    yield


app = FastAPI(
    title="JHONNY ELITE Football Intelligence",
    version="20.0",
    description="Live football intelligence: global scan, candidate-first pre-match enrichment, mathematical validation and signal tracking.",
    lifespan=lifespan,
)

origins = list(getattr(Config, "CORS_ORIGINS", []) or [])
if not origins:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "ok": True,
        "name": "JHONNY ELITE",
        "version": "20.0",
        "protocol": "LIVE -> NORMALIZE/FUSION -> DATATRUTH -> MEMORY -> CANDIDATE -> PREMATCH/ODDS -> MATH -> MASTER -> TRACK",
        "dashboard": "/v17/dashboard",
        "health": "/v17/health",
    }


@app.get("/ready")
def ready():
    return {"ok": True, "version": "20.0"}
