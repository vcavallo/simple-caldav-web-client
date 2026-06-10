import pytest


@pytest.fixture(autouse=True)
def _clear_caldav_env(monkeypatch):
    """Ensure CALDAV_CAL_*_PASSWORD env vars don't leak between tests."""
    import os
    for key in list(os.environ):
        if key.startswith("CALDAV_CAL_"):
            monkeypatch.delenv(key, raising=False)
    yield
