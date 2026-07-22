from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, links, redirect, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Encurtador de Links", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(links.router)
app.include_router(stats.router)
app.include_router(redirect.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
