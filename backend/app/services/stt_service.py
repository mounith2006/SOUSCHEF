import asyncio
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave
from collections import deque

import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16000
CHANNELS = 1

# CPU-friendly model for deployment.
DEFAULT_MODEL = "base"

CHUNK_DURATION = 0.1
MAX_RECORDING_DURATION = 60.0

SILENCE_DURATION = 1.5
NOISE_CALIBRATION_DURATION = 0.7

SPEECH_MULTIPLIER = 2.5
CONTINUE_MULTIPLIER = 1.15

MIN_START_THRESHOLD = 0.0025
MIN_CONTINUE_THRESHOLD = 0.0012

MIN_SPEECH_DURATION = 0.15
PRE_BUFFER_DURATION = 0.5
ENERGY_SMOOTHING_CHUNKS = 3


class STTUnavailableError(Exception):
    """Raised when local speech-to-text cannot process the audio."""


class STTService:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        language: str = "en",
    ):
        print(f"Loading Whisper model: {model_name}...")

        self.model = whisper.load_model(model_name)

        self.language = language

        print("Whisper loaded.")

    # =========================================================
    # LOCAL MICROPHONE / VAD
    # =========================================================

    def _get_audio_energy(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0

        audio = audio.astype(np.float32)

        return float(
            np.sqrt(np.mean(np.square(audio)))
        )

    def _calibrate_noise(
        self,
        stream,
        chunk_size: int,
    ) -> float:

        print("🔇 Calibrating background noise...")

        energies = []

        calibration_chunks = int(
            NOISE_CALIBRATION_DURATION
            / CHUNK_DURATION
        )

        for _ in range(calibration_chunks):

            audio_chunk, overflowed = stream.read(
                chunk_size
            )

            if overflowed:
                print("⚠️ Audio overflow during calibration")

            audio_chunk = audio_chunk.flatten()

            energy = self._get_audio_energy(
                audio_chunk
            )

            energies.append(energy)

        if not energies:
            return 0.001

        noise_floor = float(
            np.median(energies)
        )

        noise_floor = max(
            noise_floor,
            0.0005
        )

        print(
            f"🔊 Noise floor: {noise_floor:.6f}"
        )

        return noise_floor

    def _normalize_audio(
        self,
        audio: np.ndarray,
    ) -> np.ndarray:

        if audio.size == 0:
            return audio.astype(np.float32)

        audio = audio.astype(np.float32)

        audio = audio - np.mean(audio)

        peak = float(
            np.max(np.abs(audio))
        )

        if peak <= 0:
            return audio

        target_peak = 0.85

        if peak < 0.35:

            gain = target_peak / max(
                peak,
                0.05
            )

            gain = min(
                gain,
                4.0
            )

            audio = audio * gain

        audio = np.clip(
            audio,
            -0.98,
            0.98
        )

        return audio

    def record_until_silence(self) -> np.ndarray:

        chunk_size = int(
            CHUNK_DURATION * SAMPLE_RATE
        )

        pre_buffer_chunks = max(
            1,
            int(
                PRE_BUFFER_DURATION
                / CHUNK_DURATION
            )
        )

        print("\n🎙️ Listening...")

        chunks = []

        pre_buffer = deque(
            maxlen=pre_buffer_chunks
        )

        energy_history = deque(
            maxlen=ENERGY_SMOOTHING_CHUNKS
        )

        speech_started = False

        speech_start_time = None
        silence_start_time = None
        recording_start_time = None

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:

            noise_floor = self._calibrate_noise(
                stream,
                chunk_size
            )

            start_threshold = max(
                noise_floor * SPEECH_MULTIPLIER,
                MIN_START_THRESHOLD
            )

            continue_threshold = max(
                noise_floor * CONTINUE_MULTIPLIER,
                MIN_CONTINUE_THRESHOLD
            )

            print(
                f"🎚️ Start threshold: "
                f"{start_threshold:.6f}"
            )

            print(
                f"🎚️ Continue threshold: "
                f"{continue_threshold:.6f}"
            )

            print("🗣️ Speak now!")

            recording_start_time = time.time()

            while True:

                audio_chunk, overflowed = stream.read(
                    chunk_size
                )

                if overflowed:
                    print("⚠️ Audio buffer overflow")

                audio_chunk = audio_chunk.flatten()

                energy = self._get_audio_energy(
                    audio_chunk
                )

                energy_history.append(
                    energy
                )

                smoothed_energy = float(
                    np.mean(energy_history)
                )

                if not speech_started:
                    pre_buffer.append(
                        audio_chunk
                    )

                if not speech_started:

                    if smoothed_energy >= start_threshold:

                        if speech_start_time is None:
                            speech_start_time = time.time()

                        elapsed = (
                            time.time()
                            - speech_start_time
                        )

                        if elapsed >= MIN_SPEECH_DURATION:

                            print(
                                "🗣️ Speech detected!"
                            )

                            speech_started = True

                            silence_start_time = None

                            chunks.extend(
                                list(pre_buffer)
                            )

                    else:

                        speech_start_time = None

                else:

                    chunks.append(
                        audio_chunk
                    )

                    if (
                        smoothed_energy
                        >= continue_threshold
                    ):

                        silence_start_time = None

                    else:

                        if silence_start_time is None:
                            silence_start_time = time.time()

                        silence_elapsed = (
                            time.time()
                            - silence_start_time
                        )

                        if (
                            silence_elapsed
                            >= SILENCE_DURATION
                        ):

                            print(
                                "🛑 Speech ended."
                            )

                            break

                elapsed_total = (
                    time.time()
                    - recording_start_time
                )

                if (
                    elapsed_total
                    >= MAX_RECORDING_DURATION
                ):

                    print(
                        "⏱️ Maximum recording duration reached."
                    )

                    break

        if not chunks:

            print("⚠️ No speech detected.")

            return np.array(
                [],
                dtype=np.float32
            )

        audio = np.concatenate(
            chunks
        )

        audio = self._normalize_audio(
            audio
        )

        duration = (
            len(audio)
            / SAMPLE_RATE
        )

        print(
            f"🎧 Captured audio: "
            f"{duration:.2f} seconds"
        )

        return audio

    # =========================================================
    # CLEAN TRANSCRIPTION
    # =========================================================

    def _clean_transcription(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        text = text.strip()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = re.sub(
            r"!{2,}",
            "!",
            text
        )

        text = re.sub(
            r"\?{2,}",
            "?",
            text
        )

        text = re.sub(
            r"^[,.;:!?]+\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*[,;:]+\s*$",
            "",
            text
        )

        text = re.sub(
            r"\s+([,.!?;:])",
            r"\1",
            text
        )

        return text.strip()

    # =========================================================
    # BROWSER AUDIO → NUMPY
    # =========================================================

    def _audio_bytes_to_numpy(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> np.ndarray:

        if not audio_bytes:
            return np.array(
                [],
                dtype=np.float32
            )

        suffix = os.path.splitext(
            filename or "audio.wav"
        )[1].lower()

        content_type = (
            content_type or ""
        ).lower()

        is_wav = (
            suffix in {".wav", ".wave"}
            or content_type in {
                "audio/wav",
                "audio/x-wav",
                "audio/wave",
            }
        )

        # -----------------------------------------------------
        # WAV
        # -----------------------------------------------------

        if is_wav:

            try:

                with wave.open(
                    io.BytesIO(audio_bytes),
                    "rb"
                ) as wav_file:

                    channels = (
                        wav_file.getnchannels()
                    )

                    sample_width = (
                        wav_file.getsampwidth()
                    )

                    sample_rate = (
                        wav_file.getframerate()
                    )

                    frames = (
                        wav_file.readframes(
                            wav_file.getnframes()
                        )
                    )

            except (
                wave.Error,
                EOFError
            ) as error:

                raise STTUnavailableError(
                    "Invalid WAV audio file."
                ) from error

            if sample_width != 2:

                raise STTUnavailableError(
                    "WAV audio must use 16-bit PCM."
                )

            pcm = (
                np.frombuffer(
                    frames,
                    dtype=np.int16
                )
                .astype(np.float32)
                / 32768.0
            )

            if channels > 1:

                pcm = pcm.reshape(
                    -1,
                    channels
                ).mean(axis=1)

            if sample_rate != SAMPLE_RATE:

                raise STTUnavailableError(
                    f"WAV sample rate must be "
                    f"{SAMPLE_RATE} Hz; "
                    f"received {sample_rate} Hz."
                )

            return pcm

        # -----------------------------------------------------
        # WEBM / OPUS / OTHER BROWSER FORMATS
        # -----------------------------------------------------

        ffmpeg = shutil.which("ffmpeg")

        if ffmpeg is None:

            raise STTUnavailableError(
                "ffmpeg is required to decode "
                "browser audio such as WebM/Opus."
            )

        suffix = (
            suffix
            if suffix and len(suffix) <= 8
            else ".audio"
        )

        source_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False
            ) as source:

                source.write(
                    audio_bytes
                )

                source_path = source.name

            command = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source_path,
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                "pipe:1",
            ]

            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )

        except (
            OSError,
            subprocess.SubprocessError
        ) as error:

            raise STTUnavailableError(
                "Could not decode uploaded audio."
            ) from error

        finally:

            if source_path:

                try:
                    os.remove(
                        source_path
                    )
                except FileNotFoundError:
                    pass

        if (
            result.returncode != 0
            or not result.stdout
        ):

            detail = (
                result.stderr
                .decode(
                    "utf-8",
                    errors="replace"
                )
                .strip()
            )

            raise STTUnavailableError(
                "Could not decode uploaded audio."
                + (
                    f" {detail}"
                    if detail
                    else ""
                )
            )

        return (
            np.frombuffer(
                result.stdout,
                dtype=np.int16
            )
            .astype(np.float32)
            / 32768.0
        )

    # =========================================================
    # HTTP AUDIO → WHISPER
    # =========================================================

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
    ) -> str:

        try:

            audio = self._audio_bytes_to_numpy(
                audio_bytes,
                filename,
                content_type
            )

        except STTUnavailableError:

            raise

        except Exception as error:

            raise STTUnavailableError(
                "Could not decode uploaded audio."
            ) from error

        return self.transcribe(
            audio
        )

    async def transcribe_bytes_async(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
    ) -> str:

        return await asyncio.to_thread(
            self.transcribe_bytes,
            audio_bytes,
            filename,
            content_type,
        )

    # =========================================================
    # WHISPER
    # =========================================================

    def transcribe(
        self,
        audio: np.ndarray,
    ) -> str:

        if audio.size == 0:
            return ""

        print(
            "🧠 Transcribing with local Whisper..."
        )

        result = self.model.transcribe(
            audio,
            fp16=False,
            language=self.language,
            condition_on_previous_text=False,
            temperature=0,
            initial_prompt=(
                "You are transcribing a cooking "
                "assistant conversation. "
                "The speaker may talk about recipes, "
                "ingredients, quantities, measurements, "
                "temperatures, timers, cooking steps, "
                "pots, pans, ovens, stoves, frying, "
                "boiling, baking, roasting, chopping, "
                "mixing, stirring, seasoning, salt, "
                "pepper, oil, garlic, onion, chicken, "
                "beef, vegetables, rice, pasta, sauces, "
                "and cooking steps. "
                "Preserve the speaker's actual words."
            ),
        )

        text = self._clean_transcription(
            result.get("text", "")
        )

        print(
            f"📝 Recognized: {text}"
        )

        print(
            "✅ Transcription complete."
        )

        return text

    # =========================================================
    # LOCAL TESTING ONLY
    # =========================================================

    def listen_and_transcribe(self) -> str:

        audio = self.record_until_silence()

        return self.transcribe(
            audio
        )