from app.services.wake_word_service import WakeWordService


def test_detects_sofi():
    service = WakeWordService()

    assert service.detect("Sofi, add salt") is True
    assert service.detect("sofi add salt") is True
    assert service.detect("SOFI, wait!") is True


def test_rejects_missing_wake_word():
    service = WakeWordService()

    assert service.detect("Add salt") is False
    assert service.detect("Wait!") is False


def test_strips_sofi():
    service = WakeWordService()

    assert service.strip_wake_word("Sofi, add salt") == "add salt"
    assert service.strip_wake_word("SOFI wait!") == "wait!"


def test_missing_wake_word_returns_empty_text():
    service = WakeWordService()

    assert service.strip_wake_word("add salt") == ""