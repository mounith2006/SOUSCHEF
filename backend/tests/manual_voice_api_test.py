import io
import json
import wave

import sounddevice as sd
import httpx


SAMPLE_RATE = 16000
CHANNELS = 1
DURATION_SECONDS = 6
API_URL = "http://127.0.0.1:8000/api/voice/transcribe"


def record_wav() -> bytes:
    print("\nRecording...")
    print('Start your conversation with the wake word "Sofi".')
    print('Example: "Sofi, let\'s start cooking."')

    audio = sd.rec(
        int(DURATION_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )

    sd.wait()

    print("Recording complete.")

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(audio.tobytes())

    return buffer.getvalue()


def main():
    audio = record_wav()

    print("Sending audio to FastAPI...")

    response = httpx.post(
        API_URL,
        files={
            "audio": (
                "microphone.wav",
                audio,
                "audio/wav",
            )
        },
        timeout=180,
    )

    print(f"HTTP status: {response.status_code}")

    try:
        result = response.json()

        print("\nAPI response:")
        print(json.dumps(result, indent=2))

    except Exception:
        print("\nAPI returned:")
        print(response.text)


if __name__ == "__main__":
    main()