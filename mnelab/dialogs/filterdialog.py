from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox)
from ..utils.information import show_info


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
        try:
            return float(low) if low else None
        except ValueError as e:
            show_info('Low filter value was not correctly read.',
                      info=str(e))
            return None

    @property
    def high(self):
        high = self.highedit.text()
        try:
            return float(high) if high else None
        except ValueError as e:
            show_info('High filter value was not correctly read.',
                      info=str(e))
            return None

    @property
    def notch_freqs(self):
        if self.notchedit.text() == '':
            return None
        freqs = self.notchedit.text().split(',')
        try:
            return [float(freq) for freq in freqs]
        except ValueError as e:
            show_info('Notch filter value was not correctly read.',
                      info=str(e))
            return None
