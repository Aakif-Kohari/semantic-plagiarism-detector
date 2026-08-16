import ast
import importlib
import json
import logging
import os
import pathlib

import pytest
from pathlib import Path  # noqa: F401
from unittest.mock import patch, mock_open  # noqa: F401

from src.core import app_config
from src.core.app_config import (
    DEFAULT_APP_TITLE,
    BrandingConfig,
    clear_branding_config_cache,
    get_app_title,
    get_branding_config,
    get_lock_timeout,
    load_branding_config,
)

MODULE_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Tests for get_app_title
# ---------------------------------------------------------------------------


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

    assert get_app_title() == ("Stanford Plagiarism Detector")


def test_app_title_strips_surrounding_whitespace(monkeypatch):
    monkeypatch.setenv(
        "APP_TITLE",
        "  Campus Integrity Portal  ",
    )

    assert get_app_title() == "Campus Integrity Portal"


def test_blank_app_title_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("APP_TITLE", "   ")

    assert get_app_title() == DEFAULT_APP_TITLE


# ---------------------------------------------------------------------------
# Tests for get_lock_timeout
# ---------------------------------------------------------------------------


def test_get_lock_timeout_default(mocker):
    mocker.patch("os.getenv", return_value="30")

    assert get_lock_timeout() == 30


def test_get_lock_timeout_custom(mocker):
    mocker.patch("os.getenv", return_value="60")

    assert get_lock_timeout() == 60


def test_get_lock_timeout_invalid(mocker):
    mocker.patch("os.getenv", return_value="invalid")

    assert get_lock_timeout() == 30


def test_get_lock_timeout_minimum(mocker):
    mocker.patch("os.getenv", return_value="0")

    assert get_lock_timeout() == 1


# ---------------------------------------------------------------------------
# Tests for BrandingConfig Dataclass (Issue #2025)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure the branding config cache is cleared before and after each test."""
    clear_branding_config_cache()
    yield
    clear_branding_config_cache()


class TestBrandingConfigDataclass:
    """Test suite for the BrandingConfig dataclass structure."""

    def test_default_values(self):
        """Verify all fields have sensible default values."""
        config = BrandingConfig()

        assert config.app_name == "Semantic Plagiarism Detection System"
        assert config.tagline == "Advanced AI-Powered Academic Integrity Tool"
        assert config.primary_color == "#2563EB"
        assert config.secondary_color == "#1E40AF"
        assert config.logo_path == "assets/logo.png"
        assert "©" in config.footer_text

    def test_app_name_default_is_a_single_source_of_truth_with_default_app_title(self):
        """Regression test: BrandingConfig.app_name previously hardcoded its
        own literal ("Semantic Plagiarism Detector") independently of
        DEFAULT_APP_TITLE ("Semantic Plagiarism Detection System"), so the
        displayed app name silently differed depending on which config
        route a caller used. app_name must be defined in terms of
        DEFAULT_APP_TITLE, not merely happen to equal the same string."""
        config = BrandingConfig()

        assert config.app_name == DEFAULT_APP_TITLE

    def test_custom_initialization(self):
        """Verify fields can be overridden during initialization."""
        config = BrandingConfig(app_name="Custom App", primary_color="#FF0000")

        assert config.app_name == "Custom App"
        assert config.primary_color == "#FF0000"
        # Other fields should retain defaults
        assert config.tagline == "Advanced AI-Powered Academic Integrity Tool"

    def test_to_dict_serialization(self):
        """Verify to_dict() returns a valid dictionary representation."""
        config = BrandingConfig()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["app_name"] == "Semantic Plagiarism Detection System"
        assert "primary_color" in data


# ---------------------------------------------------------------------------
# Tests for load_branding_config
# ---------------------------------------------------------------------------


class TestLoadBrandingConfig:
    """Test suite for the load_branding_config() file loader."""

    def test_loads_valid_json(self, tmp_path):
        """Verify loader correctly parses a valid JSON configuration file."""
        config_file = tmp_path / "branding_config.json"
        custom_data = {
            "app_name": "University Portal",
            "primary_color": "#00FF00",
            "footer_text": "Custom Footer",
        }
        config_file.write_text(json.dumps(custom_data), encoding="utf-8")

        config = load_branding_config(config_file)

        assert config.app_name == "University Portal"
        assert config.primary_color == "#00FF00"
        assert config.footer_text == "Custom Footer"
        # Unspecified fields should retain defaults
        assert config.tagline == "Advanced AI-Powered Academic Integrity Tool"

    def test_fallback_on_missing_file(self, tmp_path):
        """Verify loader returns defaults when the config file does not exist."""
        missing_file = tmp_path / "nonexistent.json"

        config = load_branding_config(missing_file)

        # Should return default config
        assert config.app_name == "Semantic Plagiarism Detection System"
        assert config.primary_color == "#2563EB"

    def test_fallback_on_invalid_json(self, tmp_path):
        """Verify loader returns defaults when the file contains malformed JSON."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text("{ this is not valid json }", encoding="utf-8")

        config = load_branding_config(config_file)

        assert config.app_name == "Semantic Plagiarism Detection System"

    def test_fallback_on_non_dict_json(self, tmp_path):
        """Verify loader returns defaults when JSON root is not an object."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text('["array", "instead", "of", "object"]', encoding="utf-8")

        config = load_branding_config(config_file)

        assert config.app_name == "Semantic Plagiarism Detection System"

    def test_ignores_unknown_keys(self, tmp_path):
        """Verify loader ignores JSON keys that don't map to dataclass fields."""
        config_file = tmp_path / "branding_config.json"
        data = {
            "app_name": "Test App",
            "unknown_field": "should be ignored",
            "another_fake": 123,
        }
        config_file.write_text(json.dumps(data), encoding="utf-8")

        config = load_branding_config(config_file)

        assert config.app_name == "Test App"
        assert not hasattr(config, "unknown_field")

    def test_ignores_invalid_types(self, tmp_path):
        """Verify loader ignores fields with incorrect types (e.g., int for string)."""
        config_file = tmp_path / "branding_config.json"
        data = {
            "app_name": 12345,  # Invalid: should be string
            "primary_color": "#FF0000",  # Valid
        }
        config_file.write_text(json.dumps(data), encoding="utf-8")

        config = load_branding_config(config_file)

        # app_name should retain default because 12345 is not a string
        assert config.app_name == "Semantic Plagiarism Detection System"
        assert config.primary_color == "#FF0000"

    def test_handles_empty_json_object(self, tmp_path):
        """Verify loader handles an empty JSON object {} gracefully."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text("{}", encoding="utf-8")

        config = load_branding_config(config_file)

        # All fields should be defaults
        assert config.app_name == "Semantic Plagiarism Detection System"
        assert config.primary_color == "#2563EB"

    def test_keeps_existing_logo_path(self, tmp_path):
        """Verify a custom logo_path pointing at a real file is preserved."""
        logo_file = tmp_path / "custom_logo.png"
        logo_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        config_file = tmp_path / "branding_config.json"
        config_file.write_text(
            json.dumps({"logo_path": str(logo_file)}), encoding="utf-8"
        )

        config = load_branding_config(config_file)

        assert config.logo_path == str(logo_file)

    def test_falls_back_to_default_when_logo_missing(self, tmp_path, caplog):
        """Verify a missing logo file logs a warning and falls back to default."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text(
            json.dumps({"logo_path": str(tmp_path / "nonexistent_logo.png")}),
            encoding="utf-8",
        )

        with caplog.at_level("WARNING", logger="src.core.app_config"):
            config = load_branding_config(config_file)

        assert config.logo_path == "assets/logo.png"
        assert "Falling back to default logo" in caplog.text


# ---------------------------------------------------------------------------
# Tests for get_branding_config Cache
# ---------------------------------------------------------------------------


class TestGetBrandingConfigCache:
    """Test suite for the get_branding_config() caching mechanism."""

    def test_caches_result(self, tmp_path):
        """Verify get_branding_config() caches the result and doesn't re-read file."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text('{"app_name": "Cached App"}', encoding="utf-8")

        # Patch the loader to track calls
        with patch(
            "src.core.app_config.load_branding_config", wraps=load_branding_config
        ) as mock_load:
            # First call should hit the loader
            config1 = get_branding_config()
            assert mock_load.call_count == 1

            # Second call should use cache
            config2 = get_branding_config()
            assert mock_load.call_count == 1  # Still 1

            assert config1.app_name == config2.app_name

    def test_clear_cache_forces_reload(self, tmp_path):
        """Verify clear_branding_config_cache() forces a fresh file read."""
        config_file = tmp_path / "branding_config.json"
        config_file.write_text('{"app_name": "App V1"}', encoding="utf-8")

        with patch(
            "src.core.app_config.load_branding_config", wraps=load_branding_config
        ) as mock_load:
            get_branding_config()
            assert mock_load.call_count == 1

            clear_branding_config_cache()

            get_branding_config()
            assert mock_load.call_count == 2


# ---------------------------------------------------------------------------
# Module layout guards (Issue #2557)
# ---------------------------------------------------------------------------


class TestModuleLayout:
    """``app_config.py`` had two statements prepended above its docstring.

    That pushed ``from __future__ import annotations`` down to line 31, which
    is a hard ``SyntaxError`` on Python 3.12 -- the version this project
    targets -- and silently demoted the module docstring to a dead expression.
    Notably it is *not* an error on 3.14, so a contributor on a newer local
    interpreter can push this and only see it break in CI.
    """

    MODULE_PATH = MODULE_ROOT / "src" / "core" / "app_config.py"

    def test_source_compiles(self):
        """The assertion that Issue #2557 failed on Python 3.12."""
        compile(
            self.MODULE_PATH.read_text(encoding="utf-8"),
            "src/core/app_config.py",
            "exec",
        )

    def test_module_has_a_docstring(self):
        """A statement above the docstring turns it into a dead expression."""
        assert app_config.__doc__ is not None
        assert app_config.__doc__.lstrip().startswith(
            "Application-level environment configuration"
        )

    def test_docstring_is_the_first_statement(self):
        tree = ast.parse(self.MODULE_PATH.read_text(encoding="utf-8"))
        first = tree.body[0]

        assert isinstance(first, ast.Expr), (
            "the module docstring must be the first statement"
        )
        assert isinstance(first.value, ast.Constant)
        assert isinstance(first.value.value, str)

    def test_future_import_immediately_follows_the_docstring(self):
        tree = ast.parse(self.MODULE_PATH.read_text(encoding="utf-8"))
        second = tree.body[1]

        assert isinstance(second, ast.ImportFrom)
        assert second.module == "__future__", (
            "'from __future__ import annotations' must be the first statement "
            "after the docstring; anything above it is a SyntaxError"
        )

    def test_os_is_imported_exactly_once(self):
        """The prepended block added a duplicate ``import os``."""
        tree = ast.parse(self.MODULE_PATH.read_text(encoding="utf-8"))
        os_imports = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name == "os"
        ]

        assert len(os_imports) == 1, f"'import os' appears at lines {os_imports}"


# ---------------------------------------------------------------------------
# Tests for FUZZY_THRESHOLD (Issue #2557)
# ---------------------------------------------------------------------------


def _reload_app_config():
    """Re-import the module so a module-level constant is recomputed."""
    return importlib.reload(app_config)


@pytest.fixture
def restore_app_config():
    """Leave the imported module holding its unmodified value."""
    yield
    os.environ.pop("FUZZY_SEARCH_THRESHOLD", None)
    importlib.reload(app_config)


class TestFuzzyThreshold:
    """``FUZZY_THRESHOLD`` is a module-level constant in a module that
    virtually everything imports, so a malformed environment variable must
    degrade to the default rather than stopping the app from starting.
    """

    def test_default_when_unset(self, monkeypatch, restore_app_config):
        monkeypatch.delenv("FUZZY_SEARCH_THRESHOLD", raising=False)

        assert _reload_app_config().FUZZY_THRESHOLD == 75

    def test_default_constant_is_exported(self):
        assert app_config.DEFAULT_FUZZY_THRESHOLD == 75

    def test_reads_a_valid_value(self, monkeypatch, restore_app_config):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "90")

        assert _reload_app_config().FUZZY_THRESHOLD == 90

    @pytest.mark.parametrize("raw", ["0", "100"])
    def test_accepts_the_range_boundaries(
        self, monkeypatch, restore_app_config, raw
    ):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", raw)

        assert _reload_app_config().FUZZY_THRESHOLD == int(raw)

    def test_strips_surrounding_whitespace(self, monkeypatch, restore_app_config):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "  80  ")

        assert _reload_app_config().FUZZY_THRESHOLD == 80

    @pytest.mark.parametrize(
        "raw",
        ["high", "", "   ", "75.5", "seventy-five", "0x4B"],
    )
    def test_non_integer_falls_back_to_the_default(
        self, monkeypatch, restore_app_config, raw
    ):
        """A bad value must not raise at import time.

        Before this fix the constant was built with a bare ``int(os.getenv(...))``,
        so ``FUZZY_SEARCH_THRESHOLD=high`` raised ValueError while importing
        ``src.core.app_config`` -- and therefore while importing most of the
        application.
        """
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", raw)

        assert _reload_app_config().FUZZY_THRESHOLD == 75

    @pytest.mark.parametrize("raw", ["-1", "-5", "101", "1000"])
    def test_out_of_range_falls_back_to_the_default(
        self, monkeypatch, restore_app_config, raw
    ):
        """The value is a thefuzz match score, so it must be 0-100."""
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", raw)

        assert _reload_app_config().FUZZY_THRESHOLD == 75

    def test_warns_on_a_non_integer_value(
        self, monkeypatch, restore_app_config, caplog
    ):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "high")

        with caplog.at_level(logging.WARNING):
            _reload_app_config()

        assert "FUZZY_SEARCH_THRESHOLD" in caplog.text
        assert "not an integer" in caplog.text

    def test_warns_on_an_out_of_range_value(
        self, monkeypatch, restore_app_config, caplog
    ):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "150")

        with caplog.at_level(logging.WARNING):
            _reload_app_config()

        assert "outside the valid 0-100 range" in caplog.text

    def test_does_not_warn_on_a_valid_value(
        self, monkeypatch, restore_app_config, caplog
    ):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "88")

        with caplog.at_level(logging.WARNING):
            _reload_app_config()

        assert "FUZZY_SEARCH_THRESHOLD" not in caplog.text

    def test_is_an_int_not_a_bool_or_str(self, monkeypatch, restore_app_config):
        monkeypatch.setenv("FUZZY_SEARCH_THRESHOLD", "90")
        value = _reload_app_config().FUZZY_THRESHOLD

        assert isinstance(value, int)
        assert not isinstance(value, bool)

    def test_warning_list_can_still_import_the_name(self):
        """``src/utils/warning_list.py`` imports this constant by name."""
        from src.core.app_config import FUZZY_THRESHOLD

        assert isinstance(FUZZY_THRESHOLD, int)
