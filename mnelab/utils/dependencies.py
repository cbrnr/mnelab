# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from importlib import import_module
from qtpy import API_NAME


required = ["mne", "numpy", "scipy", "matplotlib", "qtpy", "pyxdf", API_NAME]
optional = ["sklearn", "picard", "pyedflib", "pybv"]

have = {}
for package in required + optional:
    try:
        mod = import_module(package)
    except ModuleNotFoundError:
        have[package] = False
    else:  # module successfully imported
        try:
            version = mod.__version__
        except AttributeError:
            if package == "PyQt5":
                mod = import_module("PyQt5.QtCore")
                version = mod.PYQT_VERSION_STR
            else:
                version = "unknown"
        have[package] = version
