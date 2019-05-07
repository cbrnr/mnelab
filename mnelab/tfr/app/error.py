from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def show_error(self, msg):
    """Display window with an error message
    """
    error = QMessageBox()
    error.setBaseSize(QSize(800, 200))
    error.setIcon(QMessageBox.Warning)
    error.setInformativeText(msg)
    error.setWindowTitle('Error')
    error.setStandardButtons(QMessageBox.Ok)
    error.exec_()
