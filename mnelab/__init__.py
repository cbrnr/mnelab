# © MNELAB developers
#
# License: BSD (3-clause)

import multiprocessing as mp
import sys
from pathlib import Path

import matplotlib
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .mainwindow import MainWindow
from .model import Model

__version__ = "0.9.0.dev0"


def main():
    mp.set_start_method("spawn", force=True)  # required for Linux
    app_name = "MNELAB"
    if sys.platform.startswith("darwin"):
        # set bundle name on macOS (app name shown in the menu bar)
        # this must be done before the app is created
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        info["CFBundleName"] = app_name

    matplotlib.use("QtAgg")
    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setOrganizationName("cbrnr")
    QIcon.setThemeSearchPaths([str(Path(__file__).parent / "icons")])
    QIcon.setFallbackThemeName("default")
    if sys.platform.startswith("darwin"):
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
        app.setWindowIcon(QIcon.fromTheme("mnelab-logo-macos"))
    else:
        app.setWindowIcon(QIcon.fromTheme("mnelab-logo"))
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    model = Model()
    model.view = MainWindow(model)
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    model.view.show()
    sys.exit(app.exec())
