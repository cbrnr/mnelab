from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def show_error(msg, info=None):
    """Display window with an error message."""
    error = QMessageBox()
    error.setIcon(QMessageBox.Critical)
    error.setText(msg)
    error.setInformativeText(info)
    error.setWindowTitle('Error')
    error.setStandardButtons(QMessageBox.Ok)
    error.exec()
