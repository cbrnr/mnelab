# © MNELAB developers
#
# License: BSD (3-clause)

import pytest
from PySide6.QtGui import QPalette

from mnelab import settings
from mnelab.settings import (
    _DEFAULTS,
    apply_theme,
    clear_settings,
    read_settings,
    write_settings,
)


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


def test_apply_theme_palette_fallback(qapp):
    base_window = qapp.palette().color(QPalette.ColorRole.Window).name()
    try:
        apply_theme("Dark")
        dark_window = qapp.palette().color(QPalette.ColorRole.Window).name()

        apply_theme("Light")
        light_window = qapp.palette().color(QPalette.ColorRole.Window).name()

        apply_theme("Auto")
        auto_window = qapp.palette().color(QPalette.ColorRole.Window).name()
    finally:
        apply_theme("Auto")

    assert dark_window != light_window
    assert auto_window == base_window
