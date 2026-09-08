from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.recipes import router as recipes_router
from app.api.sessions import router as sessions_router
from app.api.timers import router as timers_router
from app.api.voice import router as voice_router
from app.services.session_service import SessionService
from app.services.timer_service import TimerService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.session_service = SessionService()
    app.state.timer_service = TimerService()
    yield
    await app.state.timer_service.close()


app = FastAPI(
    title="SOUSCHEF API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router)
app.include_router(recipes_router)
app.include_router(sessions_router)
app.include_router(timers_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }

