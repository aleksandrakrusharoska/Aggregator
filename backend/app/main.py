"""FastAPI апликација + WebSocket live feed за агентска активност."""
import asyncio

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, listings
from app.core.agent_log import CHANNEL
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Ad Aggregator API",
    description="Мулти-агентски систем за агрегирање огласи за техника",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev сервер
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router)
app.include_router(agents.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/agent-feed")
async def agent_feed(websocket: WebSocket):
    """Live feed: Redis pub/sub → WebSocket (за Agent Status страницата)."""
    await websocket.accept()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await r.aclose()
