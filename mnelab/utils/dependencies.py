# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from importlib import import_module


# contains information whether a specific package is available or not
have = {d: False for d in ["numpy", "scipy", "mne", "matplotlib", "pyxdf",
                           "pyedflib", "picard", "sklearn", "PyQt5", "pybv"]}

for key, value in have.items():
    try:
        mod = import_module(key)
    except ModuleNotFoundError:
        pass
    else:
        try:
            version = mod.__version__
        except AttributeError:
            if key == "PyQt5":
                mod = import_module("PyQt5.QtCore")
                version = mod.PYQT_VERSION_STR
            else:
                version = True  # no __version__ found but the module exists
        have[key] = version
