# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import sys
import os
import multiprocessing as mp
import matplotlib
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from mnelab import MainWindow, Model


def _run():
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
    matplotlib.use("Qt5Agg")
    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setOrganizationName("cbrnr")
    if sys.platform.startswith("darwin"):
        app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    model = Model()
    model.view = MainWindow(model)
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    model.view.show()
    sys.exit(app.exec_())


def _run_pythonw():
    """Execute this script again through pythonw.

    This ensures we're using a framework build of Python on macOS.
    """
    import pathlib
    import subprocess

    cwd = pathlib.Path.cwd()
    python_path = pathlib.Path(sys.exec_prefix) / 'bin' / 'pythonw'

    if not python_path.exists():
        msg = ('pythonw executable not found. '
               'Please install python.app via conda.')
        raise RuntimeError(msg)

    cmd = [python_path, '-m', 'mnelab']

    # Append command line arguments.
    if len(sys.argv) > 1:
        cmd.append(*sys.argv[1:])

    env = os.environ.copy()
    env["MNELAB_RUNNING_PYTHONW"] = "True"

    subprocess.run(cmd, env=env, cwd=cwd)
    sys.exit()


def main():
    # Ensure we're always using a "framework build" on macOS.
    _MACOS_CONDA = sys.platform == "darwin" and "CONDA_PREFIX" in os.environ
    _RUNNING_PYTHONW = "MNELAB_RUNNING_PYTHONW" in os.environ

    if _MACOS_CONDA and not _RUNNING_PYTHONW:
        _run_pythonw()
    else:
        _run()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)  # required for Linux/macOS
    main()
