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
    provider = settings.llm_provider.lower()

    if provider == "openai" and not settings.openai_api_key:
        if voice_debug:
            print("[NOTE] OPENAI_API_KEY is not configured; using local deterministic LLM.\n")
        provider = "local"

    if not settings.rime_api_key and voice_debug:
        print("[NOTE] RIME_API_KEY is unconfigured. Real Rime voice synthesis is disabled.\n")

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

