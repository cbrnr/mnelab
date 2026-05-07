# © MNELAB developers
#
# License: BSD (3-clause)

import pytest

from mnelab import settings


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Redirect settings to a temporary file for every test.

    This prevents tests from reading or writing the real user settings, which would
    otherwise cause the Recent files menu to be populated during test runs.
    """
    monkeypatch.setattr(settings, "SETTINGS_PATH", str(tmp_path / "mnelab.ini"))
