import re


class WakeWordService:
    """Detect and remove the SOUSCHEF wake word."""

    WAKE_WORD_VARIANTS = (
        "sofi",
        "sophie",
    )

    def detect(self, text: str) -> bool:
        """Return True if the utterance starts with a recognized wake word."""

        normalized = text.strip().lower()

        if not normalized:
            return False

        variants = "|".join(
            re.escape(word) for word in self.WAKE_WORD_VARIANTS
        )

        pattern = rf"^(?:{variants})(?:\b|[,!?;:.])"

        return re.match(pattern, normalized) is not None

    def strip_wake_word(self, text: str) -> str:
        """Remove the recognized wake word and optional punctuation."""

        if not self.detect(text):
            return ""

        variants = "|".join(
            re.escape(word) for word in self.WAKE_WORD_VARIANTS
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