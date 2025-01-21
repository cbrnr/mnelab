# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)


class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter data")
        vbox = QVBoxLayout(self)

        # radio buttons
        self.bandpass_button = QRadioButton("Bandpass")
        self.bandpass_button.setChecked(True)
        self.lowpass_button = QRadioButton("Lowpass")
        self.highpass_button = QRadioButton("Highpass")
        self.notch_button = QRadioButton("Notch")

        self.filter_group = QButtonGroup(self)
        self.filter_group.addButton(self.bandpass_button)
        self.filter_group.addButton(self.lowpass_button)
        self.filter_group.addButton(self.highpass_button)
        self.filter_group.addButton(self.notch_button)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.bandpass_button)
        radio_layout.addWidget(self.lowpass_button)
        radio_layout.addWidget(self.highpass_button)
        radio_layout.addWidget(self.notch_button)

        self.bandpass_button.toggled.connect(self.update_fields)
        self.lowpass_button.toggled.connect(self.update_fields)
        self.highpass_button.toggled.connect(self.update_fields)
        self.notch_button.toggled.connect(self.update_fields)

        vbox.addLayout(radio_layout)

        # input fields
        self.grid = QGridLayout()
        self.low_label = QLabel("Low cutoff frequency (Hz):")
        self.lowedit = QLineEdit()
        self.high_label = QLabel("High cutoff frequency (Hz):")
        self.highedit = QLineEdit()
        self.notch_label = QLabel("Notch frequency (Hz):")
        self.notchedit = QLineEdit()

        self.grid.addWidget(self.low_label, 0, 0)
        self.grid.addWidget(self.lowedit, 0, 1)
        self.grid.addWidget(self.high_label, 1, 0)
        self.grid.addWidget(self.highedit, 1, 1)
        self.grid.addWidget(self.notch_label, 2, 0)
        self.grid.addWidget(self.notchedit, 2, 1)

        vbox.addLayout(self.grid)

        # buttons
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self.update_fields()
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def update_fields(self):
        if self.bandpass_button.isChecked():
            self.low_label.setVisible(True)
            self.lowedit.setVisible(True)
            self.high_label.setVisible(True)
            self.highedit.setVisible(True)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.lowpass_button.isChecked():
            self.low_label.setVisible(True)
            self.lowedit.setVisible(True)
            self.high_label.setVisible(False)
            self.highedit.setVisible(False)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.highpass_button.isChecked():
            self.low_label.setVisible(False)
            self.lowedit.setVisible(False)
            self.high_label.setVisible(True)
            self.highedit.setVisible(True)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.notch_button.isChecked():
            self.low_label.setVisible(False)
            self.lowedit.setVisible(False)
            self.high_label.setVisible(False)
            self.highedit.setVisible(False)
            self.notch_label.setVisible(True)
            self.notchedit.setVisible(True)

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
