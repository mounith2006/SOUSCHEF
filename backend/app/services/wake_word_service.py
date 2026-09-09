import re


class WakeWordService:
    """
    Detect and remove the SOUSCHEF wake word.

    Official wake word:
        Sofi

    Whisper STT recognition variants:
        Sophie
        Sophia
        Oh, Fie / Oh Fie
    """

    WAKE_WORD_VARIANTS = (
        "sofi",
        "sophie",
        "sophia",
        "oh fie",
        "oh, fie",
    )

    # Pattern matching accepted wake word variants at the start of an utterance.
    # Handles punctuation like commas, dashes, colons, ellipses, and whitespace.
    _WAKE_PATTERN = re.compile(
        r"^(?:sofi|sophie|sophia|oh[,\-]?\s*fie)\b(?:[\-_,!?;:.]|\s)*",
        re.IGNORECASE,
    )

    def _clean_input(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"^[\s\-_'\".,…]+", "", text).strip()

    def detect(self, text: str) -> bool:
        """
        Return True when the utterance starts with a recognized
        wake-word variant.
        """
        cleaned = self._clean_input(text)
        if not cleaned:
            return False

        return self._WAKE_PATTERN.match(cleaned) is not None

    def strip_wake_word(self, text: str) -> str:
        """
        Remove the recognized wake word and optional punctuation.

        Examples:
            "Sofi, add salt" -> "add salt"
            "Sophie wait!" -> "wait!"
            "Sophia, what is next?" -> "what is next?"
            "Oh, Fie - let's cook chicken pasta" -> "let's cook chicken pasta"
            "Oh, Fie" -> ""
        """
        cleaned = self._clean_input(text)
        if not self.detect(cleaned):
            return ""

        remainder = self._WAKE_PATTERN.sub("", cleaned, count=1)
        remainder = re.sub(r"^[\-_,!?;:.]+\s*", "", remainder)
        return remainder.strip()
