"""Pytest configuration and fixtures."""

from collections.abc import Generator

import pytest


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
