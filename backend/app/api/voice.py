from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.rime_tts_service import RimeTTSService, RimeTTSUnavailableError

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SynthesisRequest(BaseModel):
    # Rime's HTTP API accepts at most 500 characters per request.
    text: str = Field(min_length=1, max_length=500)


def get_rime_service(settings: Annotated[Settings, Depends(get_settings)]) -> RimeTTSService:
    return RimeTTSService(settings)


@router.post("/synthesize", response_class=Response)
async def synthesize(
    request: SynthesisRequest,
    service: Annotated[RimeTTSService, Depends(get_rime_service)],
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
