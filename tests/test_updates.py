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


@pytest.mark.parametrize(
    ("tag", "version", "is_dev", "expected_text", "expected_informative"),
    [
        ("v99.0.0", "1.0.0", False, ("99.0.0", "1.0.0"), None),
        ("v1.0.0", "1.0.0", False, ("latest version",), None),
        ("v1.0.0", "1.1.0.dev0", True, ("development version",), "1.0.0"),
    ],
    ids=["update_available", "up_to_date", "development_version"],
)
def test_check_updates_response(
    view, tag, version, is_dev, expected_text, expected_informative
):
    """Show the appropriate message for each release comparison."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock(tag)),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", version),
        patch("mnelab.mainwindow.IS_DEV_VERSION", is_dev),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert all(value in text for value in expected_text)
    if expected_informative is not None:
        informative = instance.setInformativeText.call_args[0][0]
        assert expected_informative in informative
    instance.exec.assert_called_once()
