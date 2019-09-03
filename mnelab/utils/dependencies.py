# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from importlib import import_module


# contains information whether a specific package is available or not
have = {d: False for d in ["PyQt5", "numpy", "scipy", "matplotlib", "mne",
                           "sklearn", "picard", "pyedflib", "pyxdf", "pybv"]}

for key, value in have.items():
    try:
        mod = import_module(key)
    except ModuleNotFoundError:
        pass
    else:  # module successfully imported
        try:
            version = mod.__version__
        except AttributeError:
            if key == "PyQt5":
                mod = import_module("PyQt5.QtCore")
                version = mod.PYQT_VERSION_STR
            else:
                version = True  # no __version__ found but the module exists
        have[key] = version
