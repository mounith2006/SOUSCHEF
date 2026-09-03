import json

import httpx
import pytest

from app.config import Settings
from app.services.rime_tts_service import RimeTTSService, RimeTTSUnavailableError


@pytest.mark.asyncio
async def test_synthesize_sends_rime_payload_and_returns_audio() -> None:
    request_seen: httpx.Request | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_seen
        request_seen = request
        return httpx.Response(200, headers={"content-type": "audio/wav"}, content=b"RIFFaudio")

    settings = Settings(rime_api_key="test-key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        audio = await RimeTTSService(settings, client).synthesize("Stir for one minute.")

    assert audio == b"RIFFaudio"
    assert request_seen is not None
    assert request_seen.headers["authorization"] == "Bearer test-key"
    assert json.loads(request_seen.content) == {
        "text": "Stir for one minute.",
        "modelId": "arcana",
        "speaker": "astra",
        "lang": "eng",
    }


@pytest.mark.asyncio
async def test_synthesize_rejects_non_audio_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = RimeTTSService(Settings(rime_api_key="test-key"), client)
        with pytest.raises(RimeTTSUnavailableError, match="invalid audio"):
            await service.synthesize("Hello")
