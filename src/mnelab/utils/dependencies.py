# © MNELAB developers
#
# License: BSD (3-clause)

from importlib import import_module

required = ["mne", "numpy", "scipy", "matplotlib", "PySide6", "pyxdf"]
optional = ["sklearn", "picard", "pyedflib", "pybv", "mne-qt-browser"]

have = {}
for package in required + optional:
    try:
        mod = import_module(package.replace("-", "_"))
    except ModuleNotFoundError:
        have[package] = False
    else:  # module successfully imported
        try:
            version = mod.__version__
        except AttributeError:
            version = "unknown"
        have[package] = version
