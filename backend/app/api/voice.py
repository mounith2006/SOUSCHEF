from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.rime_tts_service import (
    RimeTTSService,
    RimeTTSUnavailableError,
)
from app.services.stt_service import (
    STTService,
    STTUnavailableError,
)
from app.services.wake_word_service import WakeWordService


router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
)


_stt_service: STTService | None = None

wake_word_service = WakeWordService()


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
                detail="Local Whisper could not be loaded.",
            ) from error

    return _stt_service


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    service: STTService = Depends(get_stt_service),
) -> dict[str, str | bool]:
    """
    Receive audio from the user's browser,
    transcribe it using local Whisper,
    and require the "Sofi" wake word.
    """

    content = await audio.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Audio file is empty.",
        )

    try:
        raw_text = await service.transcribe_bytes_async(
            content,
            filename=audio.filename or "audio.wav",
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

    # Check whether the user started the interaction
    # with the required wake word: "Sofi".
    wake_word_detected = wake_word_service.detect(raw_text)

    if not wake_word_detected:
        return {
            "text": "",
            "wake_word_detected": False,
        }

    # Remove "Sofi" before sending the user's request
    # to Person 1's conversation engine.
    cleaned_text = wake_word_service.strip_wake_word(raw_text)

    return {
        "text": cleaned_text,
        "wake_word_detected": True,
    }


class SynthesisRequest(BaseModel):
    # Rime's HTTP API accepts at most 500 characters per request.
    text: str = Field(
        min_length=1,
        max_length=500,
    )


def get_rime_service(
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> RimeTTSService:
    return RimeTTSService(settings)


@router.post(
    "/synthesize",
    response_class=Response,
)
async def synthesize(
    request: SynthesisRequest,
    service: Annotated[
        RimeTTSService,
        Depends(get_rime_service),
    ],
) -> Response:
    """Turn short assistant text into WAV audio using the configured Rime voice."""

    try:
        audio = await service.synthesize(request.text)
    except RimeTTSUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice synthesis is temporarily unavailable.",
        ) from error

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )