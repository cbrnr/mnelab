# © MNELAB developers
#
# License: BSD (3-clause)

"""Self-check for built (e.g., standalone) applications.

This is used by the CI workflow to verify that a freshly built standalone app is
complete (all modules, compiled extensions, data files, and package metadata are
bundled) before it is signed and released. It is only reachable through the hidden
`--smoke-test` command line option.
"""

import importlib
import pkgutil
import sys
import tempfile
import traceback
from pathlib import Path


def _import_all_modules():
    """Import all `mnelab` modules (also catches modules only imported lazily)."""
    import mnelab

    names = [
        module.name
        for module in pkgutil.walk_packages(mnelab.__path__, "mnelab.", onerror=print)
    ]
    # make sure the module discovery itself works (it can silently find nothing)
    assert "mnelab.utils.syntax" in names, f"modules not found: {names}"
    for name in names:
        importlib.import_module(name)


def _format_code():
    """Format code, which uses the mypyc-compiled black, isort, and pytokens."""
    from mnelab.utils.syntax import format_code

    formatted = format_code("import os\nimport sys\nx=sys.argv")
    assert formatted == "import sys\n\nx = sys.argv\n", formatted


def _process_data():
    """Create, filter, save, and load data (needs MNE data files and SciPy)."""
    import mne
    import numpy as np

    info = mne.create_info(["Fz", "Cz", "Pz"], 100, "eeg")
    data = np.random.default_rng(0).standard_normal((3, 1000))
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.set_montage(mne.channels.make_standard_montage("biosemi32"), verbose=False)
    raw.filter(1, 40, verbose=False)
    with tempfile.TemporaryDirectory() as tmp:
        fname = Path(tmp) / "test_raw.fif"
        raw.save(fname, verbose=False)
        loaded = mne.io.read_raw_fif(fname, preload=True, verbose=False)
    assert loaded.ch_names == raw.ch_names


def run(logfile):
    """Run all checks and write the result to a log file.

    Parameters
    ----------
    logfile : str
        Path of the log file (contains `OK` or the traceback of the first failure).

    Returns
    -------
    int
        Exit code (0 if all checks passed, 1 otherwise).
    """
    try:
        _import_all_modules()
        _format_code()
        _process_data()
    except Exception:
        result = traceback.format_exc()
        code = 1
    else:
        result = "OK\n"
        code = 0
    Path(logfile).write_text(result, encoding="utf-8")
    print(result, file=sys.stderr, end="")
    return code
