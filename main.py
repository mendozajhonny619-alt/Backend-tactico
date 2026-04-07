from fastapi import FastAPI
import threading

from worker import iniciar_worker
from app.api.routes import router

app = FastAPI(title="JHONNY ELITE V16 API")

app.include_router(router)

worker_started = False

@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    global worker_started
    if not worker_started:
        thread = threading.Thread(target=iniciar_worker, daemon=True)
        thread.start()
        worker_started = True
