from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.recipes import router as recipes_router
from app.api.sessions import router as sessions_router
from app.api.timers import router as timers_router
from app.services.session_service import SessionService
from app.services.timer_service import TimerService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.session_service = SessionService()
    app.state.timer_service = TimerService()
    yield
    await app.state.timer_service.close()


app = FastAPI(title="SousChef API", version="0.1.0", lifespan=lifespan)
app.include_router(recipes_router)
app.include_router(sessions_router)
app.include_router(timers_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
