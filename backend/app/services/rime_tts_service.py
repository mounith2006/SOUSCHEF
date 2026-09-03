"""Small adapter around Rime's HTTP text-to-speech API."""

import httpx

from app.config import Settings


class RimeTTSUnavailableError(Exception):
    """Rime could not produce audio for a request."""


class RimeTTSService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client

    async def synthesize(self, text: str) -> bytes:
        if not self.settings.rime_api_key:
            raise RimeTTSUnavailableError("RIME_API_KEY is not configured")

        headers = {
            "Accept": "audio/wav",
            "Authorization": f"Bearer {self.settings.rime_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "modelId": self.settings.rime_model_id,
            "speaker": self.settings.rime_speaker,
            "lang": self.settings.rime_language,
        }

        try:
            if self.client is not None:
                response = await self.client.post(self.settings.rime_api_url, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(timeout=self.settings.rime_timeout_seconds) as client:
                    response = await client.post(self.settings.rime_api_url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RimeTTSUnavailableError("Rime text-to-speech request failed") from error

        content_type = response.headers.get("content-type", "")
        if not content_type.lower().startswith("audio/") or not response.content:
            raise RimeTTSUnavailableError("Rime returned an invalid audio response")

        return response.content
