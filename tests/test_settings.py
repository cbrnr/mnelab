from mnelab.settings import _DEFAULTS, read_settings


def test_read_settings():
    assert read_settings() == _DEFAULTS
