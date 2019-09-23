# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import sys
import matplotlib
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import multiprocessing as mp

from mnelab import MainWindow, Model


def main():
    app_name = "MNELAB"
    if sys.platform.startswith("darwin"):
        try:  # set bundle name on macOS (app name shown in the menu bar)
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = (bundle.localizedInfoDictionary() or
                        bundle.infoDictionary())
                if info:
                    info["CFBundleName"] = app_name
        except ImportError:
            pass
    mp.set_start_method("spawn")  # required for Linux/macOS
    matplotlib.use("Qt5Agg")
    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setOrganizationName("cbrnr")
    if sys.platform.startswith("darwin"):
        app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    model = Model()
    view = MainWindow(model)
    model.view = view
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    view.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
