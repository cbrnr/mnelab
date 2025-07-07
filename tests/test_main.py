import sys
from unittest.mock import patch

from mnelab import main
from mnelab.mainwindow import MainWindow


def test_main_app_startup(qapp):
    """Test that the main() function starts the application correctly."""
    with (
        patch.object(sys, "exit") as mock_exit,
        patch.object(sys, "argv", ["mnelab"]),
        patch("mnelab.QApplication", return_value=qapp),
        patch.object(qapp, "exec", return_value=0) as mock_exec,
    ):
        main()

    mainwindow = next(
        (w for w in qapp.topLevelWidgets() if isinstance(w, MainWindow)), None
    )
    assert mainwindow is not None
    assert mainwindow.windowTitle() == "MNELAB"

    mock_exec.assert_called_once()
    mock_exit.assert_called_once_with(0)
