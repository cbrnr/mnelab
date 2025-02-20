import pytest
from PySide6.QtCore import QSettings

from mnelab.settings import _DEFAULTS, clear_settings, read_settings, write_settings


@pytest.fixture(autouse=True)
def temp_settings(tmp_path):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    settings = QSettings()
    settings.clear()
    yield
    settings.clear()


def test_read_default_settings():
    assert read_settings() == _DEFAULTS
    assert read_settings("max_recent") == _DEFAULTS["max_recent"]


def test_write_and_read_settings():
    write_settings(max_recent=10)
    assert read_settings("max_recent") == 10
    assert read_settings() == {**_DEFAULTS, "max_recent": 10}
    clear_settings()
    assert read_settings() == _DEFAULTS
