"""Pytest configuration and fixtures."""

from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    """Force anyio tests to use asyncio only (trio not installed)."""
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset the config singleton before each test.

    This ensures test isolation by clearing the cached config instance.
    """
    import config as config_module

    # Reset before test
    config_module._config = None
    yield
    # Reset after test
    config_module._config = None


@pytest.fixture(scope="session", autouse=True)
def protect_user_settings_file() -> Generator[None, None, None]:
    """Backup and restore user-settings.yaml across the entire test session.

    Tests that call handle_config_save_click() without mocking
    save_user_settings will write empty/partial data to the real file.
    This fixture guarantees the file is restored to its original state
    after all tests complete, even if tests crash.
    """
    from config import USER_SETTINGS_PATH

    backup: str | None = None
    existed = USER_SETTINGS_PATH.exists()
    if existed:
        backup = USER_SETTINGS_PATH.read_text(encoding="utf-8")

    yield

    # Restore original file contents (or remove if it didn't exist)
    if existed and backup is not None:
        USER_SETTINGS_PATH.write_text(backup, encoding="utf-8")
    elif not existed and USER_SETTINGS_PATH.exists():
        USER_SETTINGS_PATH.unlink()


@pytest.fixture(autouse=True)
def mock_save_user_settings() -> Generator[None, None, None]:
    """Prevent every test from writing to the real user-settings.yaml.

    save_user_settings is imported into app.py via
    `from config import save_user_settings`, so the app module holds its
    own reference.  We patch both namespaces to be safe.
    """
    with (
        patch("config.save_user_settings"),
        patch("app.save_user_settings", create=True),
    ):
        yield
