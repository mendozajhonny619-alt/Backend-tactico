from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from worker import iniciar_worker
from app.api.routes import router

app = FastAPI(title="JHONNY ELITE V16 API")

# 🔥 CORS para permitir conexión con el panel (React/Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"  # opcional para evitar problemas
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Rutas API
app.include_router(router)

worker_started = False

# 🧠 Endpoint raíz
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "JHONNY_ELITE V16",
        "message": "API funcionando 🚀"
    }

# ❤️ Health check
@app.get("/health")
def health():
    return {
        "status": "ok"
    }

# 🚀 Worker en segundo plano
@app.on_event("startup")
def startup_event():
    global worker_started
    if not worker_started:
        thread = threading.Thread(target=iniciar_worker, daemon=True)
        thread.start()
        worker_started = True
