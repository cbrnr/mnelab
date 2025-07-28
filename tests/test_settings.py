import pytest

from mnelab import settings
from mnelab.settings import _DEFAULTS, clear_settings, read_settings, write_settings


@pytest.fixture(autouse=True)
def temp_settings(tmp_path, monkeypatch):
    """Redirect settings to a temporary folder for tests."""
    temp_file = str(tmp_path / "mnelab.ini")
    monkeypatch.setattr(settings, "SETTINGS_PATH", temp_file)


def test_read_default_settings():
    assert read_settings() == _DEFAULTS
    assert read_settings("max_recent") == _DEFAULTS["max_recent"]


def test_write_read_clear_settings():
    write_settings(max_recent=10)
    assert read_settings("max_recent") == 10
    assert read_settings() == {**_DEFAULTS, "max_recent": 10}
    clear_settings()
    assert read_settings() == _DEFAULTS
