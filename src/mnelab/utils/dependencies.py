# © MNELAB developers
#
# License: BSD (3-clause)

from importlib import import_module, metadata

required = [
    "mne",
    "pyside6",
    "matplotlib",
    "numpy",
    "scipy",
    "edfio",
    "pyxdf",
    "pybv",
    "pybvrf",
    "black",
    "isort",
    "onnx",
]
optional = ["autoreject", "mne-qt-browser", "picard", "sklearn"]

_distribution_names = {
    "picard": "python-picard",
    "sklearn": "scikit-learn",
}
_import_names = {
    "pyside6": "PySide6",
}

have = {}
for dep in required + optional:
    distribution_name = _distribution_names.get(dep, dep)
    import_name = _import_names.get(dep, dep).replace("-", "_")
    try:
        version = metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        try:
            mod = import_module(import_name)
        except ImportError:
            version = False
        else:
            version = getattr(mod, "__version__", None) or "unknown"
    have[distribution_name] = version
