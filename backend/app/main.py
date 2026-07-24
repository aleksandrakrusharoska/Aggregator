from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ads

app = FastAPI(
    title="Ad Aggregator API",
    description="Мулти-агентски систем за агрегирање огласи за техника",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ads.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
