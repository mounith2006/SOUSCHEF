import sys
from unittest.mock import MagicMock

# Bypass PyTorch DLL crash on this environment during collection
if "whisper" not in sys.modules:
    sys.modules["whisper"] = MagicMock()
if "sounddevice" not in sys.modules:
    mock_sd = MagicMock()
    mock_sd.get_stream.return_value = None
    sys.modules["sounddevice"] = mock_sd
