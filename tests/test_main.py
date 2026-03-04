# © MNELAB developers
#
# License: BSD (3-clause)

import subprocess
import sys


def test_main_app_startup():
    """Test that the main() function starts the application correctly.

    Runs in a subprocess so that it always starts with a clean Qt environment. pytest-qt
    creates a session-scoped QApplication for tests using qtbot, and Qt enforces a hard
    per-process singleton: instantiating a second QApplication (the MNELAB subclass
    created inside main()) in the same process triggers SIGABRT. Python-level cleanup
    (app.shutdown(), del, gc.collect()) does not reliably reset Qt's internal C++
    QCoreApplication::self pointer, making the failure intermittent. A subprocess is the
    only safe solution that avoids touching production code.
    """
    script = """
import sys
from unittest.mock import patch

sys.argv = ["mnelab"]

from mnelab import main

with patch("PySide6.QtWidgets.QApplication.exec", return_value=0):
    try:
        main()
    except SystemExit as e:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            print(app.mainwindow.windowTitle())
        sys.exit(e.code)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"main() subprocess exited with code {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "MNELAB", (
        f"Expected window title 'MNELAB', got: {result.stdout.strip()!r}\n"
        f"stderr: {result.stderr}"
    )
