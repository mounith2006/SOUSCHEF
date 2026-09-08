import re


class WakeWordService:
    """
    Detect and remove the SOUSCHEF wake word.

    Official wake word:
        Sofi

    Whisper may transcribe "Sofi" as:
        Sophie
        Sophia

    Those are accepted only as STT recognition variants.
    The official wake word remains "Sofi".
    """

    WAKE_WORD_VARIANTS = (
        "sofi",
        "sophie",
        "sophia",
    )

    def detect(self, text: str) -> bool:
        """
        Return True when the utterance starts with a recognized
        wake-word variant.
        """

        normalized = text.strip().lower()

        if not normalized:
            return False

        variants = "|".join(
            re.escape(word)
            for word in self.WAKE_WORD_VARIANTS
        )

        pattern = rf"^(?:{variants})(?:\b|[,!?;:.])"

        return re.match(pattern, normalized) is not None

    def strip_wake_word(self, text: str) -> str:
        """
        Remove the recognized wake word and optional punctuation.

        Examples:

            "Sofi, add salt"
                -> "add salt"

            "Sophie wait!"
                -> "wait!"

            "Sophia, how long?"
                -> "how long?"
        """

        if not self.detect(text):
            return ""

        variants = "|".join(
            re.escape(word)
            for word in self.WAKE_WORD_VARIANTS
        )

        pattern = rf"^(?:{variants})(?:\b)?[,!?;:.]?\s*"

        cleaned = re.sub(
            pattern,
            "",
            text.strip(),
            count=1,
            flags=re.IGNORECASE,
        )

        return cleaned.strip()