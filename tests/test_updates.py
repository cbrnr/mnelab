# © MNELAB developers
#
# License: BSD (3-clause)

import json
from unittest.mock import MagicMock, patch

import pytest

from mnelab.mainwindow import MainWindow
from mnelab.model import Model


@pytest.fixture
def view(qtbot):
    model = Model()
    win = MainWindow(model)
    model.view = win
    qtbot.addWidget(win)
    return win


def _urlopen_mock(tag_name):
    """Return a mock for urlopen that yields a response with the given tag_name."""
    data = json.dumps({"tag_name": tag_name}).encode()
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = data
    cm.__exit__.return_value = False
    return MagicMock(return_value=cm)


def test_check_updates_network_error(view):
    """When the network request fails, a warning dialog is shown."""
    with (
        patch("mnelab.mainwindow.urlopen", side_effect=OSError("no network")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "Could not retrieve" in text
    instance.exec.assert_called_once()


def test_check_updates_update_available(view):
    """When a newer version exists, the dialog mentions both versions."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v99.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.0.0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", False),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "99.0.0" in text
    assert "1.0.0" in text
    instance.exec.assert_called_once()


def test_check_updates_up_to_date(view):
    """When already on the latest version, the dialog says so."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v1.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.0.0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", False),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "latest version" in text
    instance.exec.assert_called_once()


def test_check_updates_dev_version(view):
    """When running a dev version, the dialog mentions that and the latest release."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v1.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.1.0.dev0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", True),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "development version" in text
    informative = instance.setInformativeText.call_args[0][0]
    assert "1.0.0" in informative
    instance.exec.assert_called_once()
