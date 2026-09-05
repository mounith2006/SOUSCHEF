import asyncio
import inspect
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave
from collections import deque
from typing import Callable, Awaitable, Optional, Any

import numpy as np

from ..conversation.interfaces import STTInterface
from ..config import get_settings

logger = logging.getLogger("souschef.stt")

SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_MODEL = "base"
CHUNK_DURATION = 0.1
MAX_RECORDING_DURATION = 60.0
SILENCE_DURATION = 1.5
NOISE_CALIBRATION_DURATION = 0.7
SPEECH_MULTIPLIER = 2.5
CONTINUE_MULTIPLIER = 1.15
MIN_START_THRESHOLD = 0.0025
MIN_CONTINUE_THRESHOLD = 0.0012
MIN_SPEECH_DURATION = 0.15
PRE_BUFFER_DURATION = 0.5
ENERGY_SMOOTHING_CHUNKS = 3


class STTUnavailableError(Exception):
    """Raised when local speech-to-text or microphone cannot process audio."""
    pass


class DefaultSTTService(STTInterface):
    """
    Real STT Service using local Microphone capture & Whisper transcription.
    Directly supports instant speech-start barge-in interruption.
    """

    def __init__(self, model_name: Optional[str] = None, language: str = "en"):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.whisper_model or DEFAULT_MODEL
        self.language = language or self.settings.stt_language
        self._on_speech_started: Optional[Callable[[], Awaitable[None]]] = None
        self._on_transcript: Optional[Callable[[str], Awaitable[None]]] = None

        self._whisper_model = None

    def _get_whisper_model(self):
        """Lazy load Whisper model."""
        if self._whisper_model is None:
            try:
                import whisper
                logger.info(f"[STT] Loading Whisper model '{self.model_name}'...")
                self._whisper_model = whisper.load_model(self.model_name)
                logger.info("[STT] Whisper model loaded successfully.")
            except Exception as e:
                raise STTUnavailableError(
                    f"Whisper STT model failed to load. Please ensure openai-whisper is installed. Error: {e}"
                ) from e
        return self._whisper_model

    def set_on_speech_started(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._on_speech_started = callback

    def set_on_transcript(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._on_transcript = callback

    def notify_speech_started_sync(self) -> None:
        """Synchronous notification helper for thread callbacks."""
        logger.info("[STT] Speech onset detected (Barge-in signal)")
        if self._on_speech_started:
            try:
                loop = asyncio.get_running_loop()
                if inspect.iscoroutinefunction(self._on_speech_started):
                    asyncio.run_coroutine_threadsafe(self._on_speech_started(), loop)
                else:
                    loop.call_soon_threadsafe(self._on_speech_started)
            except RuntimeError:
                pass

    async def simulate_speech_started(self) -> None:
        await self.notify_speech_started()

    async def simulate_transcript(self, text: str) -> None:
        await self.notify_transcript(text)

    async def notify_speech_started(self) -> None:
        """Trigger immediate barge-in interruption signal when user speech onset is detected."""
        logger.info("[STT] Speech onset detected (Barge-in signal)")
        if self._on_speech_started:
            if inspect.iscoroutinefunction(self._on_speech_started):
                await self._on_speech_started()
            else:
                self._on_speech_started()

    async def notify_transcript(self, text: str) -> None:
        """Deliver transcribed user input to the conversation engine."""
        logger.info(f"[STT] Transcript ready: '{text}'")
        if self._on_transcript:
            if inspect.iscoroutinefunction(self._on_transcript):
                await self._on_transcript(text)
            else:
                self._on_transcript(text)

    def _get_audio_energy(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        audio = audio.astype(np.float32)
        return float(np.sqrt(np.mean(np.square(audio))))

    def _calibrate_noise(self, stream, chunk_size: int) -> float:
        logger.info("[STT] Calibrating background noise...")
        energies = []
        calibration_chunks = int(NOISE_CALIBRATION_DURATION / CHUNK_DURATION)

        for _ in range(calibration_chunks):
            audio_chunk, overflowed = stream.read(chunk_size)
            audio_chunk = audio_chunk.flatten()
            energy = self._get_audio_energy(audio_chunk)
            energies.append(energy)

        if not energies:
            return 0.001

        noise_floor = float(np.median(energies))
        noise_floor = max(noise_floor, 0.0005)
        logger.info(f"[STT] Noise floor calibrated: {noise_floor:.6f}")
        return noise_floor

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        if audio.size == 0:
            return audio.astype(np.float32)
        audio = audio.astype(np.float32)
        audio = audio - np.mean(audio)
        peak = float(np.max(np.abs(audio)))
        if peak <= 0:
            return audio
        target_peak = 0.85
        if peak < 0.35:
            gain = target_peak / max(peak, 0.05)
            gain = min(gain, 4.0)
            audio = audio * gain
        return np.clip(audio, -0.98, 0.98)

    def record_until_silence(self) -> np.ndarray:
        """Record audio from local microphone until silence is detected, firing speech_started barge-in onset."""
        try:
            import sounddevice as sd
        except ImportError as e:
            raise STTUnavailableError("sounddevice package is required for microphone audio capture.") from e

        chunk_size = int(CHUNK_DURATION * SAMPLE_RATE)
        pre_buffer_chunks = max(1, int(PRE_BUFFER_DURATION / CHUNK_DURATION))
        logger.info("[STT] Listening on microphone...")

        chunks = []
        pre_buffer = deque(maxlen=pre_buffer_chunks)
        energy_history = deque(maxlen=ENERGY_SMOOTHING_CHUNKS)

        speech_started = False
        speech_start_time = None
        silence_start_time = None
        recording_start_time = time.time()

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=chunk_size,
            ) as stream:
                noise_floor = self._calibrate_noise(stream, chunk_size)
                start_threshold = max(noise_floor * SPEECH_MULTIPLIER, MIN_START_THRESHOLD)
                continue_threshold = max(noise_floor * CONTINUE_MULTIPLIER, MIN_CONTINUE_THRESHOLD)

                logger.info(f"[STT] Thresholds -> Start: {start_threshold:.6f}, Continue: {continue_threshold:.6f}")

                while True:
                    audio_chunk, overflowed = stream.read(chunk_size)
                    audio_chunk = audio_chunk.flatten()
                    energy = self._get_audio_energy(audio_chunk)
                    energy_history.append(energy)
                    smoothed_energy = float(np.mean(energy_history))

                    if not speech_started:
                        pre_buffer.append(audio_chunk)

                        if smoothed_energy >= start_threshold:
                            if speech_start_time is None:
                                speech_start_time = time.time()
                            elapsed = time.time() - speech_start_time
                            if elapsed >= MIN_SPEECH_DURATION:
                                # SPEECH START DETECTED - TRIGGER INSTANT BARGE-IN INTERRUPTION
                                speech_started = True
                                logger.info("[STT] Speech start onset confirmed!")
                                self.notify_speech_started_sync()
                                silence_start_time = None
                                chunks.extend(list(pre_buffer))
                        else:
                            speech_start_time = None

                    else:
                        chunks.append(audio_chunk)

                        if smoothed_energy >= continue_threshold:
                            silence_start_time = None
                        else:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            silence_elapsed = time.time() - silence_start_time
                            if silence_elapsed >= SILENCE_DURATION:
                                logger.info("[STT] Silence threshold reached. End of utterance.")
                                break

                    # Timeout check
                    if (time.time() - recording_start_time) >= MAX_RECORDING_DURATION:
                        logger.info("[STT] Max recording duration reached.")
                        break

        except Exception as e:
            raise STTUnavailableError(f"Microphone audio capture failed: {e}") from e

        if not chunks:
            return np.array([], dtype=np.float32)

        raw_audio = np.concatenate(chunks, axis=0)
        return self._normalize_audio(raw_audio)

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe numpy audio array using local Whisper model."""
        if audio.size == 0:
            return ""

        model = self._get_whisper_model()
        logger.info("[STT] Transcribing audio with local Whisper model...")

        result = model.transcribe(
            audio,
            fp16=False,
            language=self.language,
            condition_on_previous_text=False,
            temperature=0,
        )

        text = result.get("text", "").strip()
        logger.info(f"[STT] Whisper recognized transcript: '{text}'")
        return text

    def listen_and_transcribe_sync(self) -> str:
        """Record audio until silence and return transcribed text."""
        audio = self.record_until_silence()
        return self.transcribe(audio)

    async def listen_and_transcribe(self) -> str:
        """Async entry point for recording and transcribing user speech."""
        text = await asyncio.to_thread(self.listen_and_transcribe_sync)
        clean_text = text.strip() if text else ""
        if clean_text:
            await self.notify_transcript(clean_text)
        return clean_text

