from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QSpinBox, QComboBox, QDialogButtonBox)
from PyQt5.QtCore import Qt


class RunICADialog(QDialog):
    def __init__(self, parent, nchan):
        super().__init__(parent)
        self.setWindowTitle("Run ICA")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.methodbox = QComboBox()
        self.methods = {"Extended Infomax": "extended-infomax",
                        "Infomax": "infomax", "FastICA": "fastica"}
        self.methodbox.addItems(self.methods.keys())
        grid.addWidget(self.methodbox, 0, 1)
        grid.addWidget(QLabel("Number of components:"), 1, 0)
        self.numberbox = QSpinBox()
        self.numberbox.setMinimum(0)
        self.numberbox.setMaximum(nchan)
        self.numberbox.setValue(nchan)
        self.numberbox.setAlignment(Qt.AlignRight)
        grid.addWidget(self.numberbox, 1, 1)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
