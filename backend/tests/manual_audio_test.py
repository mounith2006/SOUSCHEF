import asyncio
import sys
from pathlib import Path

# Add backend/ to Python's import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.services.audio_player import AudioPlaybackService
from app.services.rime_tts_service import RimeTTSService


async def main():
    settings = Settings()

    rime = RimeTTSService(settings)
    player = AudioPlaybackService()

    print("Generating Rime audio...")

    audio = await rime.synthesize(
        "Hi, I'm SousChef. What are we cooking?"
    )

    print("Playing audio...")
    player.play(audio)

    print("Playback complete.")


if __name__ == "__main__":
    asyncio.run(main())