import numpy as np
import pytest
from unittest.mock import MagicMock, patch

import app.services.wake_word_listener as wwl
from app.services.stt_service import STTService
from app.services.wake_word_service import WakeWordService
from app.services.wake_word_listener import WakeWordListener


@pytest.fixture
def mock_stt():
    stt = MagicMock(spec=STTService)
    return stt


def test_wake_word_split_across_rolling_chunks(mock_stt):
    """
    Focused regression test:
    Prove that a wake word split across rolling chunks can still activate.
    Example:
        chunk 1 Whisper -> "Oh,"
        chunk 2 Whisper -> "Oh, Fie"
    The listener must eventually return: (True, "")
    """
    wake_service = WakeWordService()
    listener = WakeWordListener(
        stt=mock_stt,
        wake_word_service=wake_service,
        chunk_duration=0.5,
        buffer_duration=2.0,
        min_energy=0.001,
    )

    # Simulate 2 chunks with audible energy
    dummy_audio = np.ones((8000, 1), dtype=np.float32) * 0.05
    with patch.object(wwl.sd, "rec", return_value=dummy_audio):
        # Whisper output sequence: chunk 1 -> "Oh,", chunk 2 -> "Oh, Fie"
        mock_stt.transcribe.side_effect = ["Oh,", "Oh, Fie"]

        detected, inline_cmd = listener.listen_for_wake_word_sync()

        assert detected is True
        assert inline_cmd == ""
        assert mock_stt.transcribe.call_count == 2


def test_wake_word_with_inline_command_across_chunks(mock_stt):
    """
    Prove that an inline command split across rolling chunks activates with the full command.
    Example:
        chunk 1 Whisper -> "So"
        chunk 2 Whisper -> "Sofi, let's cook chicken pasta"
    The listener returns: (True, "let's cook chicken pasta")
    """
    wake_service = WakeWordService()
    listener = WakeWordListener(
        stt=mock_stt,
        wake_word_service=wake_service,
        chunk_duration=0.5,
        buffer_duration=2.0,
        min_energy=0.001,
    )

    dummy_audio = np.ones((8000, 1), dtype=np.float32) * 0.05
    with patch.object(wwl.sd, "rec", return_value=dummy_audio):
        mock_stt.transcribe.side_effect = ["So", "Sofi, let's cook chicken pasta"]

        detected, inline_cmd = listener.listen_for_wake_word_sync()

        assert detected is True
        assert inline_cmd == "let's cook chicken pasta"


def test_silence_does_not_clear_rolling_buffer(mock_stt):
    """
    Silence should skip Whisper inference to save CPU, but NOT purge
    useful audio context from the rolling buffer.
    """
    wake_service = WakeWordService()
    listener = WakeWordListener(
        stt=mock_stt,
        wake_word_service=wake_service,
        chunk_duration=0.5,
        buffer_duration=2.0,
        min_energy=0.01,
    )

    silent_audio = np.zeros((8000, 1), dtype=np.float32)
    audible_audio = np.ones((8000, 1), dtype=np.float32) * 0.05

    # Sequence: silence chunk, then speech chunk
    with patch.object(wwl.sd, "rec", side_effect=[silent_audio, audible_audio]):
        mock_stt.transcribe.return_value = "Sophie wait!"

        detected, inline_cmd = listener.listen_for_wake_word_sync()

        assert detected is True
        assert inline_cmd == "wait!"
        # Whisper was only called once on the audible chunk, skipping the pure silence
        assert mock_stt.transcribe.call_count == 1

