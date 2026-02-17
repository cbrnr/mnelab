# © MNELAB developers
#
# License: BSD (3-clause)

from importlib import metadata

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
optional = ["mne-qt-browser", "picard", "sklearn"]

_distribution_names = {
    "python-picard": "picard",
    "scikit-learn": "sklearn",
}
have = {}
for dep in required + optional:
    distribution_name = {v: k for k, v in _distribution_names.items()}.get(dep, dep)
    try:
        version = metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        version = False
    have[distribution_name] = version
