from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def show_info(msg, info=None):
    """Display window with an error message."""
    error = QMessageBox()
    error.setIcon(QMessageBox.Information)
    error.setText(msg)
    error.setInformativeText(info)
    error.setWindowTitle('Information')
    error.setStandardButtons(QMessageBox.Ok)
    error.exec()
