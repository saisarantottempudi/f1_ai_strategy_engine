from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(
    title="F1 AI Strategy & Performance Optimization System",
    version="0.1.0",
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "f1-ai-strategy", "version": "0.1.0"}
