# © MNELAB developers
#
# License: BSD (3-clause)

import io
import sys

if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

import multiprocessing as mp
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mnelab")
except PackageNotFoundError:
    __version__ = "unknown"


def main():
    mp.freeze_support()
    mp.set_start_method("spawn", force=True)

    import os
    from pathlib import Path

    import matplotlib
    from PySide6.QtCore import QEvent, QLoggingCategory, Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from mnelab.mainwindow import MainWindow
    from mnelab.model import Model

    QLoggingCategory.setFilterRules("*.debug=false\n*.warning=false")

    matplotlib.use("QtAgg")

    class MNELAB(QApplication):
        """MNELAB application."""

        def __init__(self, argv):
            super().__init__(argv)
            self.mainwindow = None

        def event(self, event):
            if event.type() == QEvent.FileOpen:
                self.mainwindow.open_data(event.file())
                return True
            return super().event(event)

    app = MNELAB(sys.argv)
    if os.environ.get("FLATPAK_ID"):
        # Inside the Flatpak sandbox, QT_QPA_PLATFORMTHEME=xdgdesktopportal is
        # set so Qt reads the desktop color-scheme via D-Bus.  In Qt 6.8+ the
        # D-Bus call is async, so colorScheme() is Unknown when QApplication is
        # first polished.  We flush the event queue here (before any widget is
        # created) so the portal reply arrives, then explicitly apply a matching
        # palette for the Fusion style which does not self-update on theme change.
        app.processEvents()
        app.setStyle("fusion")
        if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
            from PySide6.QtGui import QColor, QPalette

            dark = QColor(45, 45, 45)
            dark_base = QColor(18, 18, 18)
            disabled = QColor(127, 127, 127)
            link = QColor(42, 130, 218)

            pal = QPalette()
            pal.setColor(QPalette.ColorRole.Window, dark)
            pal.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            pal.setColor(QPalette.ColorRole.Base, dark_base)
            pal.setColor(QPalette.ColorRole.AlternateBase, dark)
            pal.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
            pal.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            pal.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled
            )
            pal.setColor(QPalette.ColorRole.Button, dark)
            pal.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            pal.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled
            )
            pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
            pal.setColor(QPalette.ColorRole.Link, link)
            pal.setColor(QPalette.ColorRole.Highlight, link)
            pal.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.Highlight,
                QColor(80, 80, 80),
            )
            pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            pal.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.HighlightedText,
                disabled,
            )
            app.setPalette(pal)
    app.setApplicationName("mnelab")
    app.setApplicationDisplayName("MNELAB")
    app.setDesktopFileName("mnelab")
    app.setOrganizationName("mnelab")
    if sys.platform.startswith("darwin"):
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
        # prevent any code from changing the dock icon (the app bundle handles it)
        app.setWindowIcon = lambda icon: None
    else:
        app.setWindowIcon(QIcon(f"{Path(__file__).parent}/icons/mnelab-logo.svg"))
    if sys.platform.startswith("win"):
        app.setStyle("fusion")
    model = Model()
    model.view = MainWindow(model)
    app.mainwindow = model.view
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.view.open_data(f)
    model.view.show()
    sys.exit(app.exec())
