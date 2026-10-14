# PyInstaller cannot detect the top-level `<hash>__mypyc` extension modules shipped by
# the mypyc-compiled packages used for code formatting, so add them explicitly.
from importlib.metadata import files

from PyInstaller.utils.hooks import copy_metadata

hiddenimports = [
    path.name.split(".")[0]
    for dist in ("black", "isort", "pytokens")
    for path in files(dist) or []
    if path.name.split(".")[0].endswith("__mypyc")
]

# isort reads its version from the package metadata at import time
datas = copy_metadata("isort")
