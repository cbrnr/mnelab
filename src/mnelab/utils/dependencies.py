# © MNELAB developers
#
# License: BSD (3-clause)

import importlib.util
from importlib import import_module

required = ["mne", "PySide6", "edfio", "matplotlib", "numpy", "pyxdf", "scipy", "pybv"]
optional = ["mne-qt-browser", "picard", "sklearn"]


have = {}
for package in required + optional:
    module_name = package.replace("-", "_")
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        have[package] = False
    else:
        mod = import_module(module_name)
        try:
            version = getattr(mod, "__version__", "unknown")
        except Exception:
            version = "unknown"
        have[package] = version
