# © MNELAB developers
#
# License: BSD (3-clause)

from unittest.mock import mock_open, patch

import mnelab.settings as settings
from mnelab.settings import (
    _DEFAULTS,
    _default_memory_limit_mb,
    clear_settings,
    read_settings,
    write_settings,
)


def test_read_default_settings():
    assert read_settings() == _DEFAULTS
    assert read_settings("max_recent") == _DEFAULTS["max_recent"]


def test_write_read_clear_settings():
    write_settings(max_recent=10, dataset_memory_limit_mb=0)
    assert read_settings("max_recent") == 10
    assert read_settings("dataset_memory_limit_mb") == 0
    assert read_settings() == {
        **_DEFAULTS,
        "max_recent": 10,
        "dataset_memory_limit_mb": 0,
    }
    clear_settings()
    assert read_settings() == _DEFAULTS


def test_default_memory_limit_uses_ram_fraction_and_cap(monkeypatch):
    """The adaptive default is 25% of RAM, capped at 8192 MB."""
    monkeypatch.setattr(settings, "platform", "linux")
    meminfo = "MemTotal:       67108864 kB\n"

    with patch("builtins.open", mock_open(read_data=meminfo)):
        assert _default_memory_limit_mb() == 8192


def test_default_memory_limit_fallback(monkeypatch):
    """If RAM detection fails, the documented fallback is used."""
    monkeypatch.setattr(settings, "platform", "linux")

    with patch("builtins.open", side_effect=OSError):
        assert _default_memory_limit_mb() == 4096
