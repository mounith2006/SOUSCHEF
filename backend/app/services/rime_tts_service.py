import asyncio
import io
import wave
import logging
import httpx
import numpy as np
from typing import Optional
from ..conversation.interfaces import TTSInterface
from ..config import get_settings

logger = logging.getLogger("souschef.rime_tts")

class RimeTTSUnavailableError(Exception):
    """Raised when Rime TTS synthesis fails or is unconfigured."""
    pass


class AudioPlaybackService:
    """Service to play WAV audio bytes via local speakers with physical cancellation support."""

    def __init__(self):
        self.is_playing = False
        self._playback_task: Optional[asyncio.Task] = None

    async def play_bytes(self, audio_bytes: bytes) -> None:
        if not audio_bytes:
            return

        self.is_playing = True
        try:
            # Check sounddevice availability
            try:
                import sounddevice as sd
                with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    frames = wav.readframes(wav.getnframes())

                dtype = np.int16 if sample_width == 2 else np.float32
                audio_data = np.frombuffer(frames, dtype=dtype)
                if channels > 1:
                    audio_data = audio_data.reshape(-1, channels)

                sd.play(audio_data, samplerate=sample_rate)
                # Poll playback completion while allowing async cancellation
                while sd.get_stream() and sd.get_stream().active:
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.info(f"[AUDIO PLAYER] Hardware playback fallback (sounddevice unavailable: {e})")
                await asyncio.sleep(0.3)
        finally:
            self.is_playing = False

    def stop_hardware(self) -> None:
        """Immediately stop local speaker playback."""
        self.is_playing = False
        try:
            import sounddevice as sd
            sd.stop()
            logger.info("[AUDIO PLAYER] sounddevice.stop() executed - hardware audio halted")
        except Exception as e:
            logger.warning(f"[AUDIO PLAYER] Hardware stop error: {e}")


class RimeTTSService(TTSInterface):
    """
    Rime TTS Service Adapter with physical audio playback and instant stop() support.
    
    RIME DEVELOPER CONTRACT:
      1. `speak(text)` synthesizes text via Rime API (or fallback) and streams audio to speaker.
      2. `stop()` cancels active synthesis/playback and calls `sounddevice.stop()`.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.rime_api_key
        self.playback_service = AudioPlaybackService()
        self._current_speak_task: Optional[asyncio.Task] = None
        self._stop_requested = False

    async def synthesize(self, text: str) -> bytes:
        """Call Rime HTTP API to synthesize WAV bytes for given text."""
        if not self.api_key:
            logger.info("[RIME TTS] RIME_API_KEY environment variable is not configured; skipping synthesis.")
            return b""

        headers = {
            "Accept": "audio/wav",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "modelId": self.settings.rime_model_id,
            "speaker": self.settings.rime_speaker,
            "lang": self.settings.rime_language,
        }

        async with httpx.AsyncClient(timeout=self.settings.rime_timeout_seconds) as client:
            response = await client.post(self.settings.rime_api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.content

    async def speak(self, text: str) -> None:
        """Synthesize text and play audio through speakers."""
        self._stop_requested = False
        logger.info(f"[RIME TTS START] Synthesizing & Speaking: '{text}'")

        try:
            # 1. Synthesize audio bytes
            audio_bytes = await self.synthesize(text)
            if not audio_bytes:
                return

            if self._stop_requested:
                logger.info("[RIME TTS] Playback aborted before audio start due to stop request")
                return

            # 2. Play audio bytes
            self._current_speak_task = asyncio.create_task(self.playback_service.play_bytes(audio_bytes))
            await self._current_speak_task
            logger.info(f"[RIME TTS COMPLETE] Finished speaking: '{text}'")
        except asyncio.CancelledError:
            logger.info("[RIME TTS] Speak task cancelled by engine")
            self.playback_service.stop_hardware()
            raise
        except Exception as e:
            logger.error(f"[RIME TTS ERROR] {e}")
            self.playback_service.stop_hardware()

    async def stop(self) -> None:
        """Instantly cancel active speak task and halt speaker hardware."""
        logger.info("[RIME TTS STOP] Halting playback and stopping audio hardware immediately...")
        self._stop_requested = True

        # Stop hardware speaker output
        self.playback_service.stop_hardware()

        # Cancel active speak task if running
        if self._current_speak_task and not self._current_speak_task.done():
            self._current_speak_task.cancel()
