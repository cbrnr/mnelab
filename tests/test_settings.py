# © MNELAB developers
#
# License: BSD (3-clause)

import json

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget

from mnelab import settings
from mnelab.settings import (
    _DEFAULTS,
    SettingsDialog,
    clear_settings,
    read_profile,
    read_settings,
    set_overrides,
    write_profile,
    write_settings,
)


@pytest.fixture(autouse=True)
def temp_settings(tmp_path, monkeypatch):
    """Redirect settings to a temporary folder for tests."""
    temp_file = str(tmp_path / "mnelab.ini")
    monkeypatch.setattr(settings, "SETTINGS_PATH", temp_file)
    monkeypatch.setattr(settings, "_overrides", {})


def test_read_default_settings():
    assert read_settings() == _DEFAULTS
    assert read_settings("max_recent") == _DEFAULTS["max_recent"]


def test_write_read_clear_settings():
    write_settings(max_recent=10)
    assert read_settings("max_recent") == 10
    assert read_settings() == {**_DEFAULTS, "max_recent": 10}
    clear_settings()
    assert read_settings() == _DEFAULTS


def test_profile_round_trip(tmp_path):
    path = tmp_path / "profile.json"
    write_profile(path, {**_DEFAULTS, "duration": 600})
    profile = read_profile(path)
    assert profile["duration"] == 600
    assert set(profile) == set(settings.PROFILE_KEYS)  # no window or session state


def test_partial_profile(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text('{"duration": 600}')
    assert read_profile(path) == {"duration": 600}


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[1, 2]",
        '{"unknown": 1}',
        '{"recent": []}',  # session state is not part of a profile
        '{"duration": "600"}',
        '{"duration": true}',
        '{"scalings": "huge"}',
        '{"toolbar_actions": [1, 2]}',
    ],
)
def test_invalid_profile(tmp_path, content):
    path = tmp_path / "profile.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_profile(path)


def test_overrides_are_not_persisted():
    set_overrides({"duration": 600})
    assert read_settings("duration") == 600
    assert read_settings()["duration"] == 600
    settings._overrides.clear()  # the ini file was never touched
    assert read_settings("duration") == _DEFAULTS["duration"]


def test_write_and_clear_drop_overrides():
    set_overrides({"duration": 600, "epochs": 5})
    write_settings(duration=30)
    assert read_settings("duration") == 30
    assert read_settings("epochs") == 5
    clear_settings()
    assert read_settings() == _DEFAULTS


def test_set_overrides_invalid_key():
    with pytest.raises(KeyError):
        set_overrides({"invalid": 1})


class _Parent(QWidget):
    def __init__(self):
        super().__init__()
        self.recent = []
        self.all_actions = {"open_file": QAction("Open", self)}

    def _apply_toolbar(self, keys):
        pass


def test_dialog_import_and_write_only_changes(qtbot, tmp_path):
    set_overrides({"duration": 600})
    parent = _Parent()
    qtbot.addWidget(parent)
    dialog = SettingsDialog(parent, ["Matplotlib", "Qt"])
    qtbot.addWidget(dialog)
    assert dialog.duration.value() == 600
    dialog._set_values({"epochs": 5, "toolbar_actions": ["open_file"]})
    assert dialog.duration.value() == 600  # keys missing from a profile stay unchanged
    assert dialog._get_values()["toolbar_actions"] == ["open_file"]
    dialog.on_ok_clicked()
    assert read_settings("epochs") == 5
    assert read_settings("toolbar_actions") == ["open_file"]
    settings._overrides.clear()  # duration override was not written to the ini file
    assert read_settings("duration") == _DEFAULTS["duration"]


def test_dialog_export(qtbot, tmp_path):
    parent = _Parent()
    qtbot.addWidget(parent)
    dialog = SettingsDialog(parent, ["Matplotlib", "Qt"])
    qtbot.addWidget(dialog)
    dialog.duration.setValue(600)
    path = tmp_path / "profile.json"
    write_profile(path, dialog._get_values())
    assert json.loads(path.read_text())["duration"] == 600
