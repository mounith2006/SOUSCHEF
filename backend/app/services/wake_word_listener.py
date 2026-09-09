"""
Continuous microphone wake-word listener.

This service continuously reads short microphone chunks and uses
the existing Whisper STT service to detect the SOUSCHEF wake word.

It does NOT own conversation state.

ConversationEngine remains responsible for:
    - interruption
    - cancellation
    - stale-response protection
    - conversation context
    - LLM
    - TTS
"""

import logging
import time
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd

from .stt_service import (
    STTService,
    SAMPLE_RATE,
    CHANNELS,
)
from .wake_word_service import WakeWordService


logger = logging.getLogger("souschef.wake_listener")


class WakeWordListener:
    """
    Continuously listens for the SOUSCHEF wake word.

    Detection strategy:

        microphone
            ↓
        short audio chunk
            ↓
        Whisper
            ↓
        WakeWordService
            ↓
        detected / not detected
    """

    def __init__(
        self,
        stt: STTService,
        wake_word_service: Optional[WakeWordService] = None,
        chunk_duration: float = 0.5,
        overlap_duration: float = 1.5,
        buffer_duration: float = 2.0,
        min_energy: float = 0.0015,
        **kwargs,
    ):
        self.stt = stt
        self.wake_word_service = (
            wake_word_service or WakeWordService()
        )

        self.chunk_duration = max(
            0.3,
            float(chunk_duration),
        )

        self.buffer_duration = max(
            1.5,
            float(buffer_duration),
        )

        self.overlap_duration = max(
            0.0,
            float(overlap_duration),
        )

        self.min_energy = max(
            0.0,
            float(min_energy),
        )

        self._running = False
        self._rolling_buffer = np.array([], dtype=np.float32)

    @property
    def running(self) -> bool:
        return self._running

    def stop(self) -> None:
        """
        Request the wake listener to stop.

        The active microphone read will finish its current chunk,
        then the loop exits.
        """
        self._running = False

    def reset(self) -> None:
        """Clear rolling buffer context."""
        self._rolling_buffer = np.array([], dtype=np.float32)

    def _energy(self, audio: np.ndarray) -> float:
        """
        Calculate RMS energy for a microphone chunk.
        """

        if audio.size == 0:
            return 0.0

        audio = audio.astype(np.float32)

        return float(
            np.sqrt(
                np.mean(
                    np.square(audio)
                )
            )
        )

    def _prepare_audio(
        self,
        audio: np.ndarray,
    ) -> np.ndarray:
        """
        Normalize microphone audio before Whisper.
        """

        if audio is None or getattr(audio, "size", 0) == 0:
            return np.array(
                [],
                dtype=np.float32,
            )

        audio = audio.astype(np.float32)

        audio = audio - np.mean(audio)

        peak = float(
            np.max(np.abs(audio))
        )

        if peak <= 0:
            return audio

        if peak < 0.35:
            gain = min(
                0.85 / max(peak, 0.05),
                4.0,
            )

            audio = audio * gain

        return np.clip(
            audio,
            -0.98,
            0.98,
        )

    def listen_for_wake_word_sync(
        self,
    ) -> Tuple[bool, str]:
        """
        Blocking continuous wake-word loop using a rolling audio buffer.

        Returns:
            (True, text_after_wake_word)
        when wake word is detected.

        Examples:
            Whisper: "Sofi" -> (True, "")
            Whisper: "Sophie wait!" -> (True, "wait!")
            Whisper: "Oh, Fie - let's cook chicken pasta" -> (True, "let's cook chicken pasta")
        """
        chunk_samples = int(
            self.chunk_duration * SAMPLE_RATE
        )

        max_buffer_samples = int(
            self.buffer_duration * SAMPLE_RATE
        )

        self._running = True

        logger.info(
            "[WAKE LISTENER] Waiting for wake word 'Sofi'..."
        )

        print(
            "\n🟢 SOUSCHEF sleeping. Say 'Sofi' to activate.\n",
            flush=True,
        )

        try:
            while self._running:
                audio_chunk = sd.rec(
                    chunk_samples,
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="float32",
                    blocking=True,
                ).flatten()

                if not self._running:
                    break

                if audio_chunk.size == 0:
                    continue

                if self._rolling_buffer.size > 0:
                    self._rolling_buffer = np.concatenate(
                        [self._rolling_buffer, audio_chunk]
                    )
                    if self._rolling_buffer.size > max_buffer_samples:
                        self._rolling_buffer = self._rolling_buffer[-max_buffer_samples:]
                else:
                    self._rolling_buffer = audio_chunk

                # Energy check: calculate recent chunk and rolling buffer energy.
                # Skip Whisper if both are silent, but do NOT discard useful audio context.
                chunk_energy = self._energy(audio_chunk)
                buffer_energy = self._energy(self._rolling_buffer)

                if chunk_energy < self.min_energy and buffer_energy < self.min_energy:
                    continue

                audio_for_whisper = self._prepare_audio(self._rolling_buffer)

                try:
                    text = self.stt.transcribe(audio_for_whisper)
                except Exception as error:
                    logger.warning(
                        "[WAKE LISTENER] Whisper wake check failed: %s",
                        error,
                    )
                    continue

                text = text.strip() if text else ""

                if text:
                    logger.info("[WAKE LISTENER] Heard: '%s'", text)

                    if self.wake_word_service.detect(text):
                        cleaned = self.wake_word_service.strip_wake_word(text)
                        logger.info(
                            "[WAKE LISTENER] Wake word detected. Command='%s'",
                            cleaned,
                        )
                        self.reset()
                        return True, cleaned

        finally:
            self._running = False

        return False, ""

    async def listen_for_wake_word(
        self,
    ) -> Tuple[bool, str]:
        """
        Async wrapper around the blocking microphone loop.
        """

        import asyncio

        return await asyncio.to_thread(
            self.listen_for_wake_word_sync
        )
