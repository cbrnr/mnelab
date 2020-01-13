# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from importlib import import_module


# required packages
required = dict(PyQt5="5.10.0",
                numpy="1.14.0",
                scipy="1.0.0",
                matplotlib="2.0.0",
                mne="0.19.0")

# optional packages
optional = dict(sklearn=None,
                picard=None,
                pyedflib=None,
                pyxdf=None,
                pybv=None)

have = {}
for package in {**required, **optional}:
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
