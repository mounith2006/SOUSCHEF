from fastapi import FastAPI

from app.api.voice import router as voice_router

app = FastAPI(title="SousChef Voice API", version="0.1.0")
app.include_router(voice_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
