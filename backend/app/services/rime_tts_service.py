import asyncio
import io
import wave
import logging
import os
import shutil
import subprocess
import tempfile
import httpx
import numpy as np
from typing import Optional

from app.config import get_settings, Settings
from app.conversation.interfaces import TTSInterface

logger = logging.getLogger("souschef.rime_tts")


class RimeTTSUnavailableError(Exception):
    """Rime could not produce audio for a request."""


class AudioPlaybackService:
    """Service to play audio bytes via local speakers with physical cancellation support."""

    def __init__(self):
        self.is_playing = False
        self._playback_task: Optional[asyncio.Task] = None

    def decode_audio(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        if not audio_bytes:
            raise ValueError("Empty audio bytes received")

        # 1. Standard WAV header check and parsing
        if audio_bytes.startswith(b"RIFF"):
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    frames = wav.readframes(wav.getnframes())

                dtype = np.int16 if sample_width == 2 else np.float32
                audio_data = np.frombuffer(frames, dtype=dtype)
                if channels > 1:
                    audio_data = audio_data.reshape(-1, channels)
                return audio_data, sample_rate
            except Exception as e:
                logger.warning(f"[AUDIO DECODER] Standard wave decode failed: {e}")

        # 2. FFmpeg decoding fallback for non-WAV / alternate formats
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            try:
                with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                cmd = [
                    ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-i", tmp_path, "-f", "s16le", "-acodec", "pcm_s16le",
                    "-ac", "1", "-ar", "24000", "pipe:1"
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

                if res.returncode == 0 and res.stdout:
                    audio_data = np.frombuffer(res.stdout, dtype=np.int16)
                    return audio_data, 24000
            except Exception as e:
                logger.warning(f"[AUDIO DECODER] FFmpeg decode failed: {e}")

        raise ValueError("Unsupported or invalid audio format")

    async def play_bytes(self, audio_bytes: bytes) -> None:
        if not audio_bytes:
            return

        self.is_playing = True
        try:
            try:
                import sounddevice as sd
                audio_data, sample_rate = self.decode_audio(audio_bytes)

                sd.play(audio_data, samplerate=sample_rate)
                while sd.get_stream() and getattr(sd.get_stream(), "active", False) is True:
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"[AUDIO PLAYER ERROR] Hardware playback failed: {e}")
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
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
        api_key: Optional[str] = None,
    ):
        self.settings = settings or get_settings()
        self.client = client
        self.api_key = api_key or getattr(self.settings, "rime_api_key", None) or os.getenv("RIME_API_KEY")
        self.playback_service = AudioPlaybackService()
        self._current_speak_task: Optional[asyncio.Task] = None
        self._stop_requested = False

    async def synthesize(self, text: str) -> bytes:
        api_key = (
            self.api_key
            or os.getenv("RIME_API_KEY")
            or (self.settings.rime_api_key if self.settings else None)
        )
        if not api_key or "your_" in api_key.lower():
            raise RimeTTSUnavailableError("RIME_API_KEY is not configured")

        headers = {
            "Accept": "audio/wav",
            "Authorization": f"Bearer {api_key}",
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
            raise RimeTTSUnavailableError(f"Rime text-to-speech request failed: {error}") from error

        content_type = response.headers.get("content-type", "")
        if not content_type.lower().startswith("audio/") or not response.content:
            raise RimeTTSUnavailableError("Rime returned an invalid audio response")

        return response.content

    async def speak(self, text: str) -> None:
        """Synthesize text and play audio through speakers."""
        self._stop_requested = False
        logger.info(f"[RIME TTS START] Synthesizing: '{text}'")

        try:
            try:
                audio_bytes = await self.synthesize(text)
            except RimeTTSUnavailableError as e:
                logger.warning(f"[RIME TTS] Synthesis unavailable: {e}")
                return

            if not audio_bytes or self._stop_requested:
                return

            try:
                print("🔊 SPEAKING...\n", flush=True)
            except Exception:
                pass

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
        self.playback_service.stop_hardware()
        if self._current_speak_task and not self._current_speak_task.done():
            self._current_speak_task.cancel()


