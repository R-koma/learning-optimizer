from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import get_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()

app = FastAPI(title="Learning Optimizer API", lifespan=lifespan)


@app.get("/api/helth")
async def helth_check():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as check")
    return {"status": "ok", "db": row["check"] == 1}
