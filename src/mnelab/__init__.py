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
from pathlib import Path

import matplotlib
from PySide6.QtCore import QEvent, QLoggingCategory, QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from mnelab.mainwindow import MainWindow
from mnelab.model import Model

try:
    __version__ = version("mnelab")
except PackageNotFoundError:
    __version__ = "unknown"


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


def main():
    QLoggingCategory.setFilterRules("*.debug=false\n*.warning=false")
    mp.set_start_method("spawn", force=True)  # required for Linux

    matplotlib.use("QtAgg")
    app = MNELAB(sys.argv)
    app.setApplicationName("mnelab")
    app.setApplicationDisplayName("MNELAB")
    app.setDesktopFileName("mnelab")
    app.setOrganizationName("cbrnr")
    if sys.platform.startswith("darwin"):
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
        app.setWindowIcon(QIcon(f"{Path(__file__).parent}/icons/mnelab-logo-macos.svg"))
    else:
        app.setWindowIcon(QIcon(f"{Path(__file__).parent}/icons/mnelab-logo.svg"))
    if sys.platform.startswith("win"):
        app.setStyle("fusion")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    model = Model()
    model.view = MainWindow(model)
    app.mainwindow = model.view
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    model.view.show()
    sys.exit(app.exec())
