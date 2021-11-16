# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from importlib import import_module

required = ["mne", "numpy", "scipy", "matplotlib", "PyQt6"]
optional = ["sklearn", "picard", "pyedflib", "pyxdf", "pybv"]

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
            version = "unknown"
        have[package] = version
