from app.services.wake_word_service import WakeWordService


def test_detects_sofi():
    service = WakeWordService()

    assert service.detect("Sofi, add salt") is True
    assert service.detect("sofi add salt") is True
    assert service.detect("SOFI, wait!") is True
    assert service.detect("Sofi") is True
    assert service.detect("sofi") is True


def test_rejects_missing_wake_word():
    service = WakeWordService()

    assert service.detect("Add salt") is False
    assert service.detect("Wait!") is False
    assert service.detect("Okay.") is False
    assert service.detect("Thank you.") is False
    assert service.detect("So") is False


def test_strips_sofi():
    service = WakeWordService()

    assert service.strip_wake_word("Sofi, add salt") == "add salt"
    assert service.strip_wake_word("SOFI wait!") == "wait!"
    assert service.strip_wake_word("Sofi") == ""


def test_missing_wake_word_returns_empty_text():
    service = WakeWordService()

    assert service.strip_wake_word("add salt") == ""
    assert service.strip_wake_word("") == ""


def test_detects_sophie_variant():
    service = WakeWordService()

    assert service.detect("Sophie, add salt") is True
    assert service.detect("SOPHIE wait!") is True
    assert service.detect("sophie") is True
    assert service.detect("Sophie") is True


def test_strips_sophie_variant():
    service = WakeWordService()

    assert service.strip_wake_word("Sophie, add salt") == "add salt"
    assert service.strip_wake_word("SOPHIE wait!") == "wait!"
    assert service.strip_wake_word("Sophie") == ""


def test_detects_and_strips_sophia_variant():
    service = WakeWordService()

    assert service.detect("Sophia, what is next?") is True
    assert service.detect("SOPHIA, add pepper") is True
    assert service.detect("sophia") is True

    assert service.strip_wake_word("Sophia, what is next?") == "what is next?"
    assert service.strip_wake_word("Sophia") == ""


def test_detects_and_strips_oh_fie_whisper_variant():
    service = WakeWordService()

    assert service.detect("Oh, Fie") is True
    assert service.detect("Oh, Fie-") is True
    assert service.detect("Oh Fie") is True
    assert service.detect("oh fie") is True
    assert service.detect("Oh, Fie - let's cook chicken pasta") is True
    assert service.detect("Oh, Fie, wait!") is True

    assert service.strip_wake_word("Oh, Fie") == ""
    assert service.strip_wake_word("Oh, Fie-") == ""
    assert service.strip_wake_word("Oh, Fie - let's cook chicken pasta") == "let's cook chicken pasta"
    assert service.strip_wake_word("Oh, Fie, wait!") == "wait!"


def test_punctuation_and_capitalization_handling():
    service = WakeWordService()

    assert service.detect("- Sofi, wait!") is True
    assert service.detect("...Sophie") is True
    assert service.detect("Sofi: start timer") is True
    assert service.detect("SOPHIE - wait") is True

    assert service.strip_wake_word("- Sofi, wait!") == "wait!"
    assert service.strip_wake_word("Sofi: start timer") == "start timer"
    assert service.strip_wake_word("SOPHIE - wait") == "wait"


def test_inline_commands():
    service = WakeWordService()

    assert service.detect("Sofi, let's cook chicken pasta") is True
    assert service.strip_wake_word("Sofi, let's cook chicken pasta") == "let's cook chicken pasta"

    assert service.detect("Sophie wait") is True
    assert service.strip_wake_word("Sophie wait") == "wait"

    assert service.detect("Sophia, what is next?") is True
    assert service.strip_wake_word("Sophia, what is next?") == "what is next?"


def test_rejects_wake_word_in_middle_or_substring():
    service = WakeWordService()

    # Wake word not at start
    assert service.detect("I think sofi is awesome") is False
    assert service.detect("Please ask Sophie") is False
    assert service.detect("What do you think, Sophia?") is False

    # Substring / partial words
    assert service.detect("philosophy") is False
    assert service.detect("sofitel hotel") is False
