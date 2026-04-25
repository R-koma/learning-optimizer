import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import dialogue_session, feedback, note, review_schedule
from api.websocket import chat
from core.database import close_pool, get_pool
from graph.builder import build_learning_graph
from graph.checkpointer import get_checkpointer
from repositories import dialogue_session_repository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = await get_pool()
    await dialogue_session_repository.reset_stuck_generations(pool)

    async with get_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.graph = build_learning_graph(checkpointer)
        yield

    await close_pool()


app = FastAPI(title="Learning Optimizer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(note.router)
app.include_router(feedback.router)
app.include_router(review_schedule.router)
app.include_router(dialogue_session.router)

app.include_router(chat.router)


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as check")
    if row is None:
        return {"status": "error", "db": False}
    return {"status": "ok", "db": row["check"] == 1}
