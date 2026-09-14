from __future__ import annotations

import logging
import os
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
    """Prevent duplicate scanners when the process manager forks workers."""
    global _worker_lock_handle
    if not getattr(Config, "WORKER_SINGLE_PROCESS_ONLY", True):
        return True
    try:
        import fcntl
        path = os.getenv("JHONNY_WORKER_LOCK", "/tmp/jhonny_elite_worker.lock")
        _worker_lock_handle = open(path, "w", encoding="utf-8")
        fcntl.flock(_worker_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _worker_lock_handle.write(str(os.getpid()))
        _worker_lock_handle.flush()
        return True
    except Exception as exc:
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
