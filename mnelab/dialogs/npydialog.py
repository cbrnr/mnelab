from qtpy.QtWidgets import (QGridLayout, QDoubleSpinBox, QVBoxLayout, QDialogButtonBox, QDialog,
                            QLabel)


class NpyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.fs = 256

        self.setWindowTitle("Set sampling frequency")

        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Sampling frequency (Hz):"), 0, 0)

        self.fsedit = QDoubleSpinBox()
        self.fsedit.setRange(0, 20e3)
        self.fsedit.setValue(self.fs)
        self.fsedit.setSuffix(" Hz")

        grid.addWidget(self.fsedit, 0, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)
