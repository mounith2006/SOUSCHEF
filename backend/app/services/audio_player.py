"""Local WAV audio playback for synthesized voice output."""

import io
import wave

import numpy as np
import sounddevice as sd


class AudioPlaybackService:
    """Play WAV audio bytes through the local system speaker."""

    def play(self, audio: bytes) -> None:
        if not audio:
            return

        try:
            with wave.open(io.BytesIO(audio), "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frames = wav.readframes(wav.getnframes())

            if sample_width == 1:
                dtype = np.uint8
            elif sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                raise ValueError(
                    f"Unsupported WAV sample width: {sample_width} bytes"
                )

            audio_data = np.frombuffer(frames, dtype=dtype)

            if channels > 1:
                audio_data = audio_data.reshape(-1, channels)

            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()

        except Exception as error:
            raise RuntimeError("Audio playback failed") from error

    def stop(self) -> None:
        """Stop any currently playing audio."""
        sd.stop()