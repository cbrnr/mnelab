# © MNELAB developers
#
# License: BSD (3-clause)

import sys
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from mnelab import main


def test_main_app_startup(no_qapp, monkeypatch):
    """Test that the main() function starts the application correctly."""
    monkeypatch.setattr(sys, "argv", ["mnelab"])

    with (
        patch("PySide6.QtWidgets.QApplication.exec", return_value=0) as mock_exec,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0
    mock_exec.assert_called_once()

    app = QApplication.instance()
    assert app.mainwindow.windowTitle() == "MNELAB"
