import time

import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_MODEL = "base"

# VAD settings
CHUNK_DURATION = 0.1          # 100 ms chunks
SILENCE_DURATION = 0.8        # End utterance after 0.8 sec silence
MAX_RECORDING_DURATION = 15.0 # Safety limit
ENERGY_THRESHOLD = 0.01       # Adjust based on microphone/environment


class STTService:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        print(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        print("Whisper loaded.")

    def _get_audio_energy(self, audio: np.ndarray) -> float:
        """Calculate RMS energy of an audio chunk."""
        return float(np.sqrt(np.mean(np.square(audio))))

    def record_until_silence(self) -> np.ndarray:
        """
        Record from the microphone until the user stops speaking.

        The recording starts when speech is detected and ends after
        SILENCE_DURATION seconds of continuous silence.
        """

        chunk_size = int(CHUNK_DURATION * SAMPLE_RATE)

        print("\n🎙️ Listening...")
        print("Speak now!")

        chunks = []
        speech_started = False
        silence_start = None
        recording_start = time.time()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:

            while True:
                audio_chunk, overflowed = stream.read(chunk_size)

                if overflowed:
                    print("⚠️ Audio buffer overflow")

                audio_chunk = audio_chunk.flatten()
                energy = self._get_audio_energy(audio_chunk)

                if energy > ENERGY_THRESHOLD:
                    # User is speaking
                    if not speech_started:
                        print("🗣️ Speech detected!")

                    speech_started = True
                    silence_start = None
                    chunks.append(audio_chunk)

                elif speech_started:
                    # User was speaking, but is now silent
                    chunks.append(audio_chunk)

                    if silence_start is None:
                        silence_start = time.time()

                    elif time.time() - silence_start >= SILENCE_DURATION:
                        print("🛑 Speech ended.")
                        break

                # Safety timeout
                if time.time() - recording_start >= MAX_RECORDING_DURATION:
                    print("⏱️ Maximum recording duration reached.")
                    break

        if not chunks:
            return np.array([], dtype=np.float32)

        return np.concatenate(chunks)

    def transcribe(self, audio: np.ndarray) -> str:
        """Convert recorded audio into text using Whisper."""

        if audio.size == 0:
            return ""

        result = self.model.transcribe(
            audio,
            fp16=False,
            language="en",
        )

        return result["text"].strip()

    def listen_and_transcribe(self) -> str:
        """Listen for one utterance and transcribe it."""

        audio = self.record_until_silence()

        return self.transcribe(audio)