from src.core.app_config import DEFAULT_APP_TITLE, get_app_title


def test_app_title_uses_default_when_variable_is_missing(
    monkeypatch,
):
    monkeypatch.delenv("APP_TITLE", raising=False)

    assert get_app_title() == DEFAULT_APP_TITLE


def test_app_title_uses_environment_value(monkeypatch):
    monkeypatch.setenv(
        "APP_TITLE",
        "Stanford Plagiarism Detector",
    )

    assert get_app_title() == (
        "Stanford Plagiarism Detector"
    )


def test_app_title_strips_surrounding_whitespace(monkeypatch):
    monkeypatch.setenv(
        "APP_TITLE",
        "  Campus Integrity Portal  ",
    )

    assert get_app_title() == "Campus Integrity Portal"


def test_blank_app_title_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("APP_TITLE", "   ")

    assert get_app_title() == DEFAULT_APP_TITLE
