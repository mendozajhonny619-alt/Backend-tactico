"""JHONNY ELITE V3 - unico proceso local FastAPI/worker/panel PC y telefono.

Los contratos internos V17/20 se mantienen para compatibilidad durante la
migracion progresiva al Protocolo V3. Las decisiones oficiales siguen en Master.
"""
from __future__ import annotations

import base64
import ipaddress
import logging
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config.config import Config
from app.v17.api.routes import router as api_router
from app.v17.routes.v17_chat import router as chat_router
from worker import iniciar_worker

logger = logging.getLogger("JHONNY_ELITE_MAIN")
BASE = Path(__file__).resolve().parent
_worker_lock_handle = None
_stop_worker = Event()
_worker_thread: Thread | None = None


def _acquire_worker_lock() -> bool:
    global _worker_lock_handle
    if not getattr(Config, "WORKER_SINGLE_PROCESS_ONLY", True):
        logger.warning("WORKER_SINGLE_PROCESS_ONLY disabled: duplicate scans may waste API credits")
        return True
    path = os.getenv("JHONNY_WORKER_LOCK") or os.path.join(tempfile.gettempdir(), "jhonny_elite_worker.lock")
    try:
        _worker_lock_handle = open(path, "a+", encoding="utf-8")
        _worker_lock_handle.seek(0)
        if os.name == "nt":
            import msvcrt
            if not _worker_lock_handle.read(1):
                _worker_lock_handle.seek(0)
                _worker_lock_handle.write("0")
                _worker_lock_handle.flush()
            _worker_lock_handle.seek(0)
            msvcrt.locking(_worker_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_worker_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Do not truncate the locked byte (Windows lock semantics).
        _worker_lock_handle.seek(0)
        _worker_lock_handle.write(str(os.getpid()).ljust(16))
        _worker_lock_handle.flush()
        return True
    except Exception as exc:
        logger.warning("Worker lock unavailable. This process will be read-only: %s", exc)
        if _worker_lock_handle:
            _worker_lock_handle.close()
            _worker_lock_handle = None
        return False


def _release_worker_lock() -> None:
    global _worker_lock_handle
    if _worker_lock_handle is None:
        return
    try:
        _worker_lock_handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(_worker_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_worker_lock_handle.fileno(), fcntl.LOCK_UN)
    finally:
        _worker_lock_handle.close()
        _worker_lock_handle = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_thread
    _stop_worker.clear()
    key_present = bool(getattr(Config, "API_FOOTBALL_KEY", "") or getattr(Config, "FOOTBALL_DATA_KEY", ""))
    if getattr(Config, "WORKER_ENABLED", False) and not key_present:
        logger.warning("Worker is DISABLED: no football provider API key configured in .env")
    elif getattr(Config, "WORKER_ENABLED", False) and _acquire_worker_lock():
        _worker_thread = Thread(target=iniciar_worker, args=(_stop_worker,), name="jhonny-elite-worker", daemon=True)
        _worker_thread.start()
        logger.info("JHONNY ELITE V3 live worker started (SHADOW_MODE=%s)", getattr(Config, "SHADOW_MODE", True))
    else:
        logger.warning("JHONNY ELITE started without a scanner; the panel is read-only")
    try:
        yield
    finally:
        _stop_worker.set()
        if _worker_thread:
            _worker_thread.join(timeout=5)
            _worker_thread = None
        _release_worker_lock()


app = FastAPI(
    title="JHONNY ELITE V3 | Elite Live Intelligence",
    version="3.0-local",
    description="Local Windows scanner with PC/mobile panel and simulation-first policy",
    lifespan=lifespan,
)

origins = list(getattr(Config, "CORS_ORIGINS", []) or [])
if not origins:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials="*" not in origins,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


def _is_lan_client(address: str) -> bool:
    if address in {"testclient", "localhost"}:
        return True
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_loopback or ip.is_private or ip.is_link_local
    except ValueError:
        return False


def _authorized(header: str, password: str) -> bool:
    if not header.lower().startswith("basic "):
        return False
    try:
        raw = base64.b64decode(header.split(" ", 1)[1], validate=True).decode("utf-8")
        user, sep, supplied = raw.partition(":")
        return bool(sep) and secrets.compare_digest(user, "jhonny") and secrets.compare_digest(supplied, password)
    except (UnicodeDecodeError, ValueError):
        return False


@app.middleware("http")
async def local_access_guard(request: Request, call_next):
    client = request.client.host if request.client else ""
    local_password = os.getenv("JHONNY_LAN_PASSWORD", "").strip()
    if not _is_lan_client(client):
        return Response("Only local/private LAN access is allowed", status_code=403)
    # If somebody starts Uvicorn on 0.0.0.0 without configuring a password,
    # reject phone/LAN access rather than accidentally exposing the API.
    if not local_password and client not in {"testclient", "localhost", "127.0.0.1", "::1"}:
        return Response("LAN access requires JHONNY_LAN_PASSWORD", status_code=403)
    if local_password and not _authorized(request.headers.get("authorization", ""), local_password):
        return Response("Authentication required", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="JHONNY ELITE V3"', "Cache-Control": "no-store"})
    response = await call_next(request)
    if request.url.path.startswith(("/v17/", "/elite-live/", "/health", "/ready")):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(api_router)
app.include_router(chat_router)


@app.get("/ready")
def ready():
    return {"ok": True, "version": "3.0-local", "shadow_mode": bool(getattr(Config, "SHADOW_MODE", True))}


@app.get("/elite-live/dashboard")
def elite_dashboard_alias():
    return RedirectResponse(url="/v17/dashboard", status_code=307)


@app.get("/elite-live/matches")
def elite_matches_alias():
    return RedirectResponse(url="/v17/live", status_code=307)


@app.get("/elite-live/matches/{fixture_id}")
def elite_match_alias(fixture_id: str):
    return RedirectResponse(url=f"/v17/match/{fixture_id}", status_code=307)


@app.get("/elite-live/signals")
def elite_signals_alias():
    return RedirectResponse(url="/v17/signals", status_code=307)


@app.get("/elite-live/history")
def elite_history_alias():
    return RedirectResponse(url="/v17/history", status_code=307)


@app.get("/elite-live/system-health")
def elite_health_alias():
    return RedirectResponse(url="/v17/health", status_code=307)


@app.get("/info")
def info():
    return {"name": "JHONNY ELITE V3", "version": "3.0-local", "ui": "/panel",
            "api": "/v17/dashboard", "mode": "SHADOW" if Config.SHADOW_MODE else "OPERATIVE"}


# The full React interface is used when built. If Node is absent, the bundled
# responsive read-only local panel still works on PC and phone without a CDN.
DIST = BASE / "dist"
LOCAL_PANEL = BASE / "web_local" / "index.html"
if (DIST / "index.html").is_file():
    if (DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="react-assets")
    frontend_page = DIST / "index.html"
else:
    frontend_page = LOCAL_PANEL


@app.get("/")
@app.get("/panel")
def panel():
    return FileResponse(frontend_page, media_type="text/html", headers={"Cache-Control": "no-store"})
