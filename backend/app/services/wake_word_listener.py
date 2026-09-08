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
        chunk_duration: float = 1.5,
        overlap_duration: float = 0.5,
        min_energy: float = 0.0015,
    ):
        self.stt = stt
        self.wake_word_service = (
            wake_word_service or WakeWordService()
        )

        self.chunk_duration = max(
            0.5,
            float(chunk_duration),
        )

        self.overlap_duration = min(
            max(0.0, float(overlap_duration)),
            self.chunk_duration * 0.75,
        )

        self.min_energy = max(
            0.0,
            float(min_energy),
        )

        self._running = False

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

        if audio.size == 0:
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
        Blocking continuous wake-word loop.

        Returns:

            (True, text_after_wake_word)

        when wake word is detected.

        Examples:

            Whisper:
                "Sofi"

            returns:
                (True, "")

            Whisper:
                "Sofi, how much salt?"

            returns:
                (True, "how much salt?")
        """

        chunk_size = int(
            self.chunk_duration * SAMPLE_RATE
        )

        overlap_size = int(
            self.overlap_duration * SAMPLE_RATE
        )

        previous_audio = np.array(
            [],
            dtype=np.float32,
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
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=chunk_size,
            ) as stream:

                while self._running:

                    audio_chunk, overflowed = stream.read(
                        chunk_size
                    )

                    if overflowed:
                        logger.warning(
                            "[WAKE LISTENER] Microphone overflow"
                        )

                    audio_chunk = audio_chunk.flatten()

                    energy = self._energy(
                        audio_chunk
                    )

                    # Ignore obvious silence/noise.
                    if energy < self.min_energy:
                        continue

                    if overlap_size > 0 and previous_audio.size:
                        audio_for_whisper = np.concatenate(
                            [
                                previous_audio,
                                audio_chunk,
                            ]
                        )
                    else:
                        audio_for_whisper = audio_chunk

                    audio_for_whisper = self._prepare_audio(
                        audio_for_whisper
                    )

                    try:
                        text = self.stt.transcribe(
                            audio_for_whisper
                        )
                    except Exception as error:
                        logger.warning(
                            "[WAKE LISTENER] Whisper wake check failed: %s",
                            error,
                        )

                        previous_audio = (
                            audio_chunk[-overlap_size:]
                            if overlap_size > 0
                            else np.array(
                                [],
                                dtype=np.float32,
                            )
                        )

                        continue

                    text = text.strip()

                    if text:
                        logger.info(
                            "[WAKE LISTENER] Heard: '%s'",
                            text,
                        )

                        if self.wake_word_service.detect(text):
                            cleaned = (
                                self.wake_word_service
                                .strip_wake_word(text)
                            )

                            logger.info(
                                "[WAKE LISTENER] Wake word detected. "
                                "Command='%s'",
                                cleaned,
                            )

                            return True, cleaned

                    previous_audio = (
                        audio_chunk[-overlap_size:]
                        if overlap_size > 0
                        else np.array(
                            [],
                            dtype=np.float32,
                        )
                    )

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