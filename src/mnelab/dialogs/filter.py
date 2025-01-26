# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)


class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter data")
        vbox = QVBoxLayout(self)

        # filter type
        filter_type_groupbox = QGroupBox("Filter type")
        filter_type_layout = QHBoxLayout()

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

        filter_type_layout.addWidget(self.bandpass_button)
        filter_type_layout.addWidget(self.lowpass_button)
        filter_type_layout.addWidget(self.highpass_button)
        filter_type_layout.addWidget(self.notch_button)

        self.bandpass_button.toggled.connect(self.update_fields)
        self.lowpass_button.toggled.connect(self.update_fields)
        self.highpass_button.toggled.connect(self.update_fields)
        self.notch_button.toggled.connect(self.update_fields)

        filter_type_groupbox.setLayout(filter_type_layout)
        vbox.addWidget(filter_type_groupbox)

        # filter settings
        filter_settings_groupbox = QGroupBox("Filter settings")
        self.grid = QGridLayout()
        self.low_label = QLabel("Low cutoff frequency (Hz):")
        self.lowedit = QDoubleSpinBox()
        self.lowedit.setRange(0.0, 10000.0)
        self.lowedit.setDecimals(3)
        self.high_label = QLabel("High cutoff frequency (Hz):")
        self.highedit = QDoubleSpinBox()
        self.highedit.setRange(0.0, 10000.0)
        self.highedit.setDecimals(3)
        self.notch_label = QLabel("Notch frequency (Hz):")
        self.notchedit = QDoubleSpinBox()
        self.notchedit.setRange(0.0, 10000.0)
        self.notchedit.setDecimals(3)

        self.grid.addWidget(self.low_label, 0, 0)
        self.grid.addWidget(self.lowedit, 0, 1)
        self.grid.addWidget(self.high_label, 1, 0)
        self.grid.addWidget(self.highedit, 1, 1)
        self.grid.addWidget(self.notch_label, 2, 0)
        self.grid.addWidget(self.notchedit, 2, 1)

        filter_settings_groupbox.setLayout(self.grid)
        vbox.addWidget(filter_settings_groupbox)

        # buttons
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttonbox.button(QDialogButtonBox.Ok)
        vbox.addWidget(self.buttonbox)
        self.ok_button.setEnabled(False)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        # validation message
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: gray;")
        vbox.addWidget(self.error_label)
        self.lowedit.valueChanged.connect(self.validate_inputs)
        self.highedit.valueChanged.connect(self.validate_inputs)
        self.notchedit.valueChanged.connect(self.validate_inputs)

        self.update_fields()
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def update_fields(self):
        if self.bandpass_button.isChecked():
            self.selected_filter_type = "Bandpass"
            self.low_label.setVisible(True)
            self.lowedit.setVisible(True)
            self.high_label.setVisible(True)
            self.highedit.setVisible(True)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.lowpass_button.isChecked():
            self.selected_filter_type = "Lowpass"
            self.low_label.setVisible(True)
            self.lowedit.setVisible(True)
            self.high_label.setVisible(False)
            self.highedit.setVisible(False)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.highpass_button.isChecked():
            self.selected_filter_type = "Highpass"
            self.low_label.setVisible(False)
            self.lowedit.setVisible(False)
            self.high_label.setVisible(True)
            self.highedit.setVisible(True)
            self.notch_label.setVisible(False)
            self.notchedit.setVisible(False)
        elif self.notch_button.isChecked():
            self.selected_filter_type = "Notch"
            self.low_label.setVisible(False)
            self.lowedit.setVisible(False)
            self.high_label.setVisible(False)
            self.highedit.setVisible(False)
            self.notch_label.setVisible(True)
            self.notchedit.setVisible(True)

        self.validate_inputs()

    def validate_inputs(self):
        error_message = ""
        is_valid = True

        if self.selected_filter_type == "Bandpass":
            if self.highedit.value() <= self.lowedit.value():
                error_message = "High cutoff must be greater than low cutoff."
                is_valid = False
        elif self.selected_filter_type == "Lowpass":
            if self.lowedit.value() <= 0:
                error_message = "Low cutoff must be greater than 0."
                is_valid = False
        elif self.selected_filter_type == "Highpass":
            if self.highedit.value() <= 0:
                error_message = "High cutoff must be greater than 0."
                is_valid = False
        elif self.selected_filter_type == "Notch":
            if self.notchedit.value() <= 0:
                error_message = "Notch frequency must be greater than 0."
                is_valid = False

        self.error_label.setText(error_message)
        self.ok_button.setEnabled(is_valid)

    @property
    def low(self):
        return (
            float(self.lowedit.value())
            if self.selected_filter_type in ["Bandpass", "Lowpass"]
            else None
        )

    @property
    def high(self):
        return (
            float(self.highedit.value())
            if self.selected_filter_type in ["Bandpass", "Highpass"]
            else None
        )

    @property
    def notch(self):
        return (
            float(self.notchedit.value())
            if self.selected_filter_type == "Notch"
            else None
        )
