# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class FilterDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Filter data")

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Low cutoff frequency (Hz):"), 0, 0)
        self.lowedit = QLineEdit()
        grid.addWidget(self.lowedit, 0, 1)

        grid.addWidget(QLabel("High cutoff frequency (Hz):"), 1, 0)
        self.highedit = QLineEdit()
        grid.addWidget(self.highedit, 1, 1)

        grid.addWidget(QLabel("Notch frequency (Hz):"), 2, 0)
        self.notchedit = QLineEdit()
        grid.addWidget(self.notchedit, 2, 1)

        grid.addWidget(QLabel("Savgol frequency (Hz):"), 3, 0)
        self.savgoledit = QLineEdit()
        grid.addWidget(self.savgoledit, 3, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def low(self):
        low = self.lowedit.text()
        return float(low) if low else None

    @property
    def high(self):
        high = self.highedit.text()
        return float(high) if high else None

    @property
    def notch(self):
        notch = self.notchedit.text()
        return float(notch) if notch else None

    @property
    def savgol(self):
        savgol = self.savgoledit.text()
        return float(savgol) if savgol else None
