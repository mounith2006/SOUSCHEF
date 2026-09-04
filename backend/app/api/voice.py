from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from app.config import Settings, get_settings
from app.services.stt_service import (
    STTService,
    STTUnavailableError,
)


router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
)


_stt_service: STTService | None = None


def get_stt_service(
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> STTService:

    global _stt_service

    if _stt_service is None:

        try:

            _stt_service = STTService(
                model_name=settings.whisper_model,
                language=settings.whisper_language,
            )

        except Exception as error:

            raise HTTPException(
                status_code=503,
                detail=(
                    "Local Whisper could not be loaded."
                ),
            ) from error

    return _stt_service


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    service: STTService = Depends(
        get_stt_service
    ),
) -> dict[str, str]:

    """
    Receive audio from the user's browser
    and transcribe it using local Whisper.
    """

    content = await audio.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Audio file is empty.",
        )

    try:

        text = await service.transcribe_bytes_async(
            content,
            filename=(
                audio.filename
                or "audio.wav"
            ),
            content_type=(
                audio.content_type
                or "application/octet-stream"
            ),
        )

    except STTUnavailableError as error:

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        "text": text
    }