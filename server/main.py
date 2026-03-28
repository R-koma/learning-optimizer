import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import feedback, note, review_schedule
from api.websocket import chat
from core.database import close_pool, get_pool
from graph.builder import build_learning_graph
from graph.checkpointer import get_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()

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

app.include_router(chat.router)


@app.get("/api/health")
async def health_check():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as check")
    return {"status": "ok", "db": row["check"] == 1}
