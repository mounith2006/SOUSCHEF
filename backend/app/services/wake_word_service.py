import re


class WakeWordService:
    """Detect and remove the SOUSCHEF wake word."""

    WAKE_WORD = "sofi"

    def detect(self, text: str) -> bool:
        """
        Return True when the user's utterance starts with the wake word.

        Examples:
            "Sofi, add salt" -> True
            "sofi start the timer" -> True
            "Add salt" -> False
        """
        normalized = text.strip().lower()

        if not normalized:
            return False

        pattern = rf"^{re.escape(self.WAKE_WORD)}(?:\b|[,!?;:.])"

        return re.match(pattern, normalized) is not None

    def strip_wake_word(self, text: str) -> str:
        """
        Remove the wake word from the beginning of an utterance.

        Example:
            "Sofi, add two teaspoons of salt"
            -> "add two teaspoons of salt"
        """
        if not self.detect(text):
            return ""

        pattern = rf"^{re.escape(self.WAKE_WORD)}(?:\b)?[,!?;:.]?\s*"

        cleaned = re.sub(
            pattern,
            "",
            text.strip(),
            count=1,
            flags=re.IGNORECASE,
        )

        return cleaned.strip()