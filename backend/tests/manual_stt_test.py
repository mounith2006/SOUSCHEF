from app.services.stt_service import STTService


def main():
    stt = STTService(model_name="base")

    text = stt.listen_and_transcribe(duration=5)

    print("\n📝 Recognized text:")
    print(text)


if __name__ == "__main__":
    main()