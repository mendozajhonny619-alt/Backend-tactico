from fastapi import FastAPI
import threading

# IMPORTAMOS EL WORKER
from worker import iniciar_worker

app = FastAPI(title="JHONNY ELITE V16 API")

@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}


# 🚀 INICIAR WORKER EN SEGUNDO PLANO
def start_worker():
    iniciar_worker()


threading.Thread(target=start_worker, daemon=True).start()
