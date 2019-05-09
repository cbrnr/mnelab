from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox)


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
        grid.addWidget(QLabel("Notch filter frequencies (Hz):"), 2, 0)
        self.notchedit = QLineEdit()
        grid.addWidget(self.notchedit, 2, 1)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
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
    def notch_freqs(self):
        freqs = self.notchedit.text().split(',')
        try:
            return [float(freq) for freq in freqs]
        except ValueError:
            return None
