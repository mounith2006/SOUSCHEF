from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.voice import (
    router as voice_router,
)


app = FastAPI(
    title="SOUSCHEF Voice API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    voice_router
)


@app.get("/health")
def health() -> dict[str, str]:

    return {
        "status": "ok"
    }