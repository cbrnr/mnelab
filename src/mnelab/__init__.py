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

IS_DEV_VERSION = __version__.split(".")[-1].startswith("dev")


def main():
    mp.freeze_support()
    mp.set_start_method("spawn", force=True)

    import os
    import signal
    from pathlib import Path

    if getattr(sys, "frozen", False):
        cache_dir = Path.home() / ".matplotlib"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(cache_dir)

    import matplotlib
    from PySide6.QtCore import QEvent, QLoggingCategory, Qt, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from mnelab.mainwindow import MainWindow
    from mnelab.model import Model
    from mnelab.settings import read_settings

    QLoggingCategory.setFilterRules("*.debug=false\n*.warning=false")

    matplotlib.use("QtAgg")

    class MNELAB(QApplication):
        """MNELAB application."""

        def __init__(self, argv):
            super().__init__(argv)
            self.mainwindow = None

        def event(self, event):
            if event.type() == QEvent.Type.FileOpen:
                self.mainwindow.open_data(event.file())
                return True
            return super().event(event)

    app = MNELAB(sys.argv)
    app.setApplicationName("mnelab")
    app.setApplicationDisplayName("MNELAB")
    app.setDesktopFileName("mnelab")
    app.setOrganizationName("mnelab")
    if sys.platform.startswith("darwin"):
        # prevent any code from changing the dock icon (the app bundle handles it)
        app.setWindowIcon = lambda icon: None
    else:
        app.setWindowIcon(QIcon(f"{Path(__file__).parent}/icons/mnelab-logo.svg"))
    app.setAttribute(
        Qt.ApplicationAttribute.AA_DontShowIconsInMenus,
        not read_settings("menu_icons"),
    )
    if sys.platform.startswith("win"):
        app.setStyle("fusion")
    model = Model()
    model.view = MainWindow(model)
    app.mainwindow = model.view
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.view.open_data(f)
    model.view.show()

    # allow Ctrl-C in the terminal to shut down gracefully (only for dev versions)
    if IS_DEV_VERSION:
        signal.signal(signal.SIGINT, lambda *_: app.quit())
        sigint_timer = QTimer()
        sigint_timer.start(200)
        sigint_timer.timeout.connect(lambda: None)

    sys.exit(app.exec())
