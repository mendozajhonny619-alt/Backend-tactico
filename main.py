from fastapi import FastAPI

app = FastAPI(title="JHONNY ELITE V16 API")

@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}
