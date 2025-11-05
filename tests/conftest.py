import gc

import pytest
from PySide6.QtWidgets import QApplication


def _cleanup_qapp():
    """Helper to cleanup QApplication instance."""
    app = QApplication.instance()
    if app is not None:
        app.quit()
        app.shutdown()
        del app
        gc.collect()


@pytest.fixture
def no_qapp():
    """Ensure no QApplication exists before and after the test."""
    _cleanup_qapp()
    yield
    _cleanup_qapp()
