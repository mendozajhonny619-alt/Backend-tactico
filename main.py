from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from worker import iniciar_worker

app = FastAPI(
    title="JHONNY ELITE V16",
    version="16.0",
)


# -----------------------------------
# CORS (permite conexión con frontend)
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción puedes restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------
# Rutas API
# -----------------------------------
app.include_router(router)


# -----------------------------------
# Startup → lanza el worker
# -----------------------------------
@app.on_event("startup")
def startup_event():
    """
    Ejecuta el worker en segundo plano.
    """
    Thread(target=iniciar_worker, daemon=True).start()


# -----------------------------------
# Root endpoint
# -----------------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "message": "JHONNY ELITE V16 backend operativo",
    }
