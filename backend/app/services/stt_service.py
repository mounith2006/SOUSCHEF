import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_MODEL = "base"


class STTService:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        print(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        print("Whisper loaded.")

    def record_audio(self, duration: int = 5) -> np.ndarray:
        """Record audio from the microphone."""
        print(f"\n🎙️ Recording for {duration} seconds...")
        print("Speak now!")

        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
        )

        sd.wait()

        print("Recording finished.")

        return audio.flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        """Convert recorded audio into text using Whisper."""
        result = self.model.transcribe(
            audio,
            fp16=False,
            language="en",
        )

        return result["text"].strip()

    def listen_and_transcribe(self, duration: int = 5) -> str:
        """Record from microphone and transcribe the recording."""
        audio = self.record_audio(duration)

        return self.transcribe(audio)
