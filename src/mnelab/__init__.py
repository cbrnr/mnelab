# © MNELAB developers
#
# License: BSD (3-clause)

import multiprocessing as mp
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import matplotlib
from PySide6.QtCore import QLoggingCategory, QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from mnelab.mainwindow import MainWindow
from mnelab.model import Model

try:
    __version__ = version("mnelab")
except PackageNotFoundError:
    __version__ = "unknown"


def main():
    QLoggingCategory.setFilterRules("*.debug=false\n*.warning=false")
    mp.set_start_method("spawn", force=True)  # required for Linux
    if sys.platform.startswith("darwin"):
        # set bundle name on macOS (app name shown in the menu bar)
        # this must be done before the app is created
        from Foundation import NSBundle

        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        info["CFBundleName"] = "MNELAB"

    matplotlib.use("QtAgg")
    app = QApplication(sys.argv)
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
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    model.view.show()
    sys.exit(app.exec())
