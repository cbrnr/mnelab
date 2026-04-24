# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt

from mnelab.mainwindow import MainWindow, _resolve_icon_theme_name
from mnelab.model import Model


def test_initial_actions(qtbot):
    """Test if initial actions are correctly enabled/disabled."""
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)

    for name, action in view.all_actions.items():
        if name in view.always_enabled:
            assert action.isEnabled()
        else:
            assert not action.isEnabled()


def test_resolve_icon_theme_name_manual_override():
    assert _resolve_icon_theme_name("Light", Qt.ColorScheme.Dark) == "light"
    assert _resolve_icon_theme_name("Dark", Qt.ColorScheme.Light) == "dark"


def test_resolve_icon_theme_name_auto_follows_system():
    assert _resolve_icon_theme_name("Auto", Qt.ColorScheme.Dark) == "dark"
    assert _resolve_icon_theme_name("Auto", Qt.ColorScheme.Unknown) == "light"
