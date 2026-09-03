import re
import time
from collections import deque

import numpy as np
import sounddevice as sd
import whisper


SAMPLE_RATE = 16000
CHANNELS = 1

# Use "small" for better recognition if your machine can handle it.
# Use "base" if small is too slow.
DEFAULT_MODEL = "small"

# Recording
CHUNK_DURATION = 0.1
MAX_RECORDING_DURATION = 60.0

# Silence detection
# Longer silence prevents quiet pauses from cutting off words.
SILENCE_DURATION = 1.5

# Background-noise calibration
NOISE_CALIBRATION_DURATION = 0.7

# VAD thresholds
#
# Speech must be clearly above the noise floor to START.
# Once speech has started, we use a lower threshold so quiet
# words do not accidentally look like silence.
SPEECH_MULTIPLIER = 2.5
CONTINUE_MULTIPLIER = 1.15

# Absolute minimum thresholds.
# These prevent the threshold from becoming absurdly sensitive
# when the microphone is extremely quiet.
MIN_START_THRESHOLD = 0.0025
MIN_CONTINUE_THRESHOLD = 0.0012

# Require speech to persist briefly before starting.
MIN_SPEECH_DURATION = 0.15

# Keep audio from immediately before speech detection.
# This helps preserve the first consonants/syllables.
PRE_BUFFER_DURATION = 0.5

# Smooth energy over several chunks.
ENERGY_SMOOTHING_CHUNKS = 3


class STTService:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        print(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        print("Whisper loaded.")

    # ---------------------------------------------------------
    # AUDIO
    # ---------------------------------------------------------

    def _get_audio_energy(self, audio: np.ndarray) -> float:
        """Calculate RMS energy of an audio chunk."""
        if audio.size == 0:
            return 0.0

        audio = audio.astype(np.float32)

        return float(np.sqrt(np.mean(np.square(audio))))

    def _calibrate_noise(
        self,
        stream,
        chunk_size: int,
    ) -> float:
        """
        Estimate background noise.

        Median energy is used instead of average energy so that
        one cough, click, pan noise, etc. doesn't destroy calibration.
        """

        print("🔇 Calibrating background noise...")

        energies = []

        calibration_chunks = int(
            NOISE_CALIBRATION_DURATION / CHUNK_DURATION
        )

        for _ in range(calibration_chunks):
            audio_chunk, overflowed = stream.read(chunk_size)

            if overflowed:
                print("⚠️ Audio overflow during calibration")

            audio_chunk = audio_chunk.flatten()

            energy = self._get_audio_energy(audio_chunk)

            energies.append(energy)

        if not energies:
            return 0.001

        noise_floor = float(np.median(energies))

        # Don't allow an unrealistically tiny threshold.
        noise_floor = max(noise_floor, 0.0005)

        print(f"🔊 Noise floor: {noise_floor:.6f}")

        return noise_floor

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Gentle normalization.

        We intentionally do NOT use an aggressive noise gate.
        Quiet speech contains useful consonants and small words.
        """

        if audio.size == 0:
            return audio.astype(np.float32)

        audio = audio.astype(np.float32)

        # Remove DC offset.
        audio = audio - np.mean(audio)

        # Find peak.
        peak = float(np.max(np.abs(audio)))

        if peak <= 0:
            return audio

        # Normalize only when the recording is very quiet.
        #
        # This boosts quiet speech without constantly amplifying
        # background noise.
        target_peak = 0.85

        if peak < 0.35:
            gain = target_peak / max(peak, 0.05)

            # Don't apply ridiculous amounts of gain.
            gain = min(gain, 4.0)

            audio = audio * gain

        # Safety limiter.
        audio = np.clip(audio, -0.98, 0.98)

        return audio

    # ---------------------------------------------------------
    # RECORDING
    # ---------------------------------------------------------

    def record_until_silence(self) -> np.ndarray:
        """
        Record natural speech until sustained silence.

        The VAD uses:
          1. noise calibration
          2. start threshold
          3. lower continuation threshold
          4. smoothed energy
          5. pre-buffering
          6. sustained silence timeout

        This is designed for hands-free cooking speech.
        """

        chunk_size = int(
            CHUNK_DURATION * SAMPLE_RATE
        )

        pre_buffer_chunks = max(
            1,
            int(
                PRE_BUFFER_DURATION
                / CHUNK_DURATION
            ),
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

            # ---------------------------------------------
            # NOISE CALIBRATION
            # ---------------------------------------------

            noise_floor = self._calibrate_noise(
                stream,
                chunk_size,
            )

            start_threshold = max(
                noise_floor * SPEECH_MULTIPLIER,
                MIN_START_THRESHOLD,
            )

            continue_threshold = max(
                noise_floor * CONTINUE_MULTIPLIER,
                MIN_CONTINUE_THRESHOLD,
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

            # ---------------------------------------------
            # LISTEN LOOP
            # ---------------------------------------------

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

                energy_history.append(energy)

                smoothed_energy = float(
                    np.mean(energy_history)
                )

                # Always maintain the pre-buffer.
                if not speech_started:
                    pre_buffer.append(audio_chunk)

                # -----------------------------------------
                # WAITING FOR SPEECH
                # -----------------------------------------

                if not speech_started:

                    if smoothed_energy >= start_threshold:

                        if speech_start_time is None:
                            speech_start_time = time.time()

                        elapsed = (
                            time.time()
                            - speech_start_time
                        )

                        if elapsed >= MIN_SPEECH_DURATION:

                            print("🗣️ Speech detected!")

                            speech_started = True

                            silence_start_time = None

                            # Include the audio immediately
                            # before speech detection.
                            chunks.extend(
                                list(pre_buffer)
                            )

                    else:
                        # Energy dropped before enough
                        # speech was detected.
                        speech_start_time = None

                # -----------------------------------------
                # SPEECH ACTIVE
                # -----------------------------------------

                else:

                    chunks.append(audio_chunk)

                    if (
                        smoothed_energy
                        >= continue_threshold
                    ):
                        # User is still talking.
                        silence_start_time = None

                    else:

                        if silence_start_time is None:

                            silence_start_time = (
                                time.time()
                            )

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

                # -----------------------------------------
                # MAXIMUM RECORDING TIME
                # -----------------------------------------

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

        # -------------------------------------------------
        # NO AUDIO
        # -------------------------------------------------

        if not chunks:

            print("⚠️ No speech detected.")

            return np.array(
                [],
                dtype=np.float32,
            )

        # -------------------------------------------------
        # JOIN AUDIO
        # -------------------------------------------------

        audio = np.concatenate(chunks)

        # -------------------------------------------------
        # GENTLE NORMALIZATION
        # -------------------------------------------------

        audio = self._normalize_audio(audio)

        duration = len(audio) / SAMPLE_RATE

        print(
            f"🎧 Captured audio: "
            f"{duration:.2f} seconds"
        )

        return audio

    # ---------------------------------------------------------
    # TRANSCRIPTION
    # ---------------------------------------------------------

    def _clean_transcription(
        self,
        text: str,
    ) -> str:
        """
        Only remove obvious formatting artifacts.

        IMPORTANT:
        We do NOT remove repeated words.

        Example:
            "stir stir stir"
        must remain exactly that.

        The conversation engine can decide later
        whether repetition is meaningful.
        """

        if not text:
            return ""

        text = text.strip()

        # Collapse excessive whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        # Repeated punctuation.
        text = re.sub(
            r"!{2,}",
            "!",
            text,
        )

        text = re.sub(
            r"\?{2,}",
            "?",
            text,
        )

        # Remove random punctuation at beginning.
        text = re.sub(
            r"^[,.;:!?]+\s*",
            "",
            text,
        )

        # Remove random punctuation at end.
        text = re.sub(
            r"\s*[,;:]+\s*$",
            "",
            text,
        )

        # Fix spaces before punctuation.
        text = re.sub(
            r"\s+([,.!?;:])",
            r"\1",
            text,
        )

        return text.strip()

    def transcribe(
        self,
        audio: np.ndarray,
    ) -> str:
        """
        Send audio to Whisper.
        """

        if audio.size == 0:
            return ""

        print("🧠 Transcribing...")

        result = self.model.transcribe(
            audio,

            # CPU-friendly.
            fp16=False,

            # SousChef is currently English.
            language="en",

            # Each user utterance should be interpreted
            # independently.
            condition_on_previous_text=False,

            # Deterministic decoding.
            temperature=0,

            # Helps Whisper understand cooking vocabulary.
            initial_prompt=(
                "You are transcribing a cooking assistant "
                "conversation. The speaker may talk about "
                "recipes, ingredients, food preparation, "
                "measurements, cooking temperatures, timers, "
                "pots, pans, knives, ovens, stoves, frying, "
                "boiling, baking, roasting, chopping, mixing, "
                "stirring, seasoning, salt, pepper, oil, "
                "garlic, onion, chicken, beef, vegetables, "
                "rice, pasta, sauces, and cooking steps. "
                "Preserve the speaker's actual words."
            ),
        )

        text = result.get(
            "text",
            "",
        ).strip()

        text = self._clean_transcription(
            text
        )

        print(
            f"📝 Recognized: {text}"
        )

        print("✅ Transcription complete.")

        return text

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def listen_and_transcribe(self) -> str:
        """
        Record speech and return transcription.
        """

        audio = self.record_until_silence()

        return self.transcribe(audio)