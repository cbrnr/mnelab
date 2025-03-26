# © MNELAB developers
#
# License: BSD (3-clause)

from importlib.metadata import version, PackageNotFoundError
from itertools import chain

required = ("mne", "PySide6", "edfio", "matplotlib", "numpy", "pyxdf", "scipy", "pybv")
optional = ("mne-qt-browser", "picard", "scikit-learn")

have = {}
for package in chain(required, optional):
    try:
        have[package] = version(package)
    except PackageNotFoundError:
        have[package] = False
