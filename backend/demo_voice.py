import os
import asyncio
import sys
import logging
from app.config import get_settings
from app.services.stt_service import DefaultSTTService, STTUnavailableError
from app.services.rime_tts_service import RimeTTSService, RimeTTSUnavailableError
from app.services.llm_service import get_llm_service, LLMUnavailableError
from app.services.conversation_service import get_conversation_engine
from app.services.voice_orchestrator import VoiceOrchestrator

voice_debug = os.getenv("VOICE_DEBUG", "0").lower() in ("1", "true", "yes")
log_level = logging.INFO if voice_debug else logging.WARNING

# Configure logging levels (suppress internal noise unless VOICE_DEBUG=1)
logging.basicConfig(level=log_level, format="%(asctime)s | %(message)s")
for name in ("souschef", "httpx", "asyncio", "openai", "whisper", "sounddevice"):
    logging.getLogger(name).setLevel(log_level)

logger = logging.getLogger("souschef.demo")

async def main():
    print("=" * 50)
    print("SOUSCHEF VOICE DEMO")
    print("===================\n")

    settings = get_settings()
    rime_key = getattr(settings, "rime_api_key", None) or os.getenv("RIME_API_KEY")
    is_rime_configured = bool(rime_key and "your_" not in rime_key.lower())

    print(f"Rime API key: {'CONFIGURED' if is_rime_configured else 'NOT CONFIGURED'}\n")

    provider = (getattr(settings, "llm_provider", "local") or os.getenv("LLM_PROVIDER", "local")).lower()

    if provider == "nvidia":
        nvidia_key = getattr(settings, "nvidia_api_key", None) or os.getenv("NVIDIA_API_KEY")
        is_nvidia_configured = bool(nvidia_key and "your_" not in nvidia_key.lower())
        print(f"NVIDIA API key: {'CONFIGURED' if is_nvidia_configured else 'NOT CONFIGURED'}\n")
    elif provider == "openai":
        openai_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        is_openai_configured = bool(openai_key and "your_" not in openai_key.lower())
        print(f"OpenAI API key: {'CONFIGURED' if is_openai_configured else 'NOT CONFIGURED'}\n")
    else:
        print(f"LLM Provider: LOCAL\n")




    try:
        stt = DefaultSTTService()
        llm = get_llm_service(provider=provider)
        tts = RimeTTSService()

        engine = get_conversation_engine(session_id="voice_demo_session", tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=True)

        if voice_debug:
            print("🎙️ Listening for user speech on microphone...")
            print("   Interrupt anytime while SOUSCHEF is speaking by talking into mic.")
            print("   Press Ctrl+C to exit.\n")
            print("-" * 50 + "\n")

        await orchestrator.run_voice_loop()

    except STTUnavailableError as e:
        print(f"\n❌ [STT ERROR] {e}\n")
    except RimeTTSUnavailableError as e:
        print(f"\n❌ [RIME TTS ERROR] {e}\n")
    except LLMUnavailableError as e:
        print(f"\n❌ [LLM ERROR] {e}\n")
    except KeyboardInterrupt:
        print("\n\n[DEMO] Voice loop terminated by user.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

