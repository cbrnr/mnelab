# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
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
        self.lowpass_button = QRadioButton("Lowpass")
        self.lowpass_button.setChecked(True)
        self.highpass_button = QRadioButton("Highpass")
        self.bandpass_button = QRadioButton("Bandpass")
        self.notch_button = QRadioButton("Notch")

        self.filter_group = QButtonGroup(self)
        self.filter_group.addButton(self.lowpass_button)
        self.filter_group.addButton(self.highpass_button)
        self.filter_group.addButton(self.bandpass_button)
        self.filter_group.addButton(self.notch_button)

        filter_type_layout.addWidget(self.lowpass_button)
        filter_type_layout.addWidget(self.highpass_button)
        filter_type_layout.addWidget(self.bandpass_button)
        filter_type_layout.addWidget(self.notch_button)

        self.filter_group.buttonToggled.connect(self._on_filter_type_changed)

        filter_type_groupbox.setLayout(filter_type_layout)
        vbox.addWidget(filter_type_groupbox)

        # filter settings
        filter_settings_groupbox = QGroupBox("Filter settings")
        self.grid = QGridLayout()
        self.lower_label = QLabel("Lower cutoff frequency (Hz):")
        self.lower_edit = QDoubleSpinBox()
        self.lower_edit.setMinimum(0)
        self.lower_edit.setDecimals(2)
        self.lower_edit.setValue(1)
        self.lower_edit.setAlignment(Qt.AlignRight)
        self.upper_label = QLabel("Upper cutoff frequency (Hz):")
        self.upper_edit = QDoubleSpinBox()
        self.upper_edit.setMinimum(0)
        self.upper_edit.setDecimals(2)
        self.upper_edit.setValue(30)
        self.upper_edit.setAlignment(Qt.AlignRight)
        self.notch_label = QLabel("Notch frequency (Hz):")
        self.notch_edit = QDoubleSpinBox()
        self.notch_edit.setMinimum(0)
        self.notch_edit.setDecimals(2)
        self.notch_edit.setValue(50)
        self.notch_edit.setAlignment(Qt.AlignRight)

        self.grid.addWidget(self.lower_label, 0, 0)
        self.grid.addWidget(self.lower_edit, 0, 1)
        self.grid.addWidget(self.upper_label, 1, 0)
        self.grid.addWidget(self.upper_edit, 1, 1)
        self.grid.addWidget(self.notch_label, 2, 0)
        self.grid.addWidget(self.notch_edit, 2, 1)

        filter_settings_groupbox.setLayout(self.grid)
        vbox.addWidget(filter_settings_groupbox)

        # buttons
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttonbox.button(QDialogButtonBox.Ok)
        vbox.addWidget(self.buttonbox)
        self.ok_button.setEnabled(False)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.lower_edit.valueChanged.connect(self.validate_inputs)
        self.upper_edit.valueChanged.connect(self.validate_inputs)
        self.notch_edit.valueChanged.connect(self.validate_inputs)

        self._param_widgets_config = {
            "lower": (self.lower_label, self.lower_edit),
            "upper": (self.upper_label, self.upper_edit),
            "notch": (self.notch_label, self.notch_edit),
        }

        self._filter_type_config = {
            self.lowpass_button: {"name": "Lowpass", "widgets": ["upper"]},
            self.highpass_button: {"name": "Highpass", "widgets": ["lower"]},
            self.bandpass_button: {"name": "Bandpass", "widgets": ["lower", "upper"]},
            self.notch_button: {"name": "Notch", "widgets": ["notch"]},
        }

        self._on_filter_type_changed(self.filter_group.checkedButton(), True)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def _on_filter_type_changed(self, button, checked):
        if not checked:
            return

        config = self._filter_type_config[button]
        self.selected_filter_type = config["name"]
        visible_widget_keys = config["widgets"]

        # hide all parameter widgets first
        for key in self._param_widgets_config:
            for widget in self._param_widgets_config[key]:
                widget.setVisible(False)

        # show only the relevant ones for the selected filter type
        for key in visible_widget_keys:
            for widget in self._param_widgets_config[key]:
                widget.setVisible(True)

        self.validate_inputs()

    def validate_inputs(self):
        is_valid = False
        if self.selected_filter_type == "Bandpass":
            is_valid = self.upper_edit.value() > self.lower_edit.value()
        elif self.selected_filter_type == "Lowpass":
            is_valid = self.upper_edit.value() > 0
        elif self.selected_filter_type == "Highpass":
            is_valid = self.lower_edit.value() > 0
        elif self.selected_filter_type == "Notch":
            is_valid = self.notch_edit.value() > 0

        self.ok_button.setEnabled(is_valid)

    @property
    def lower(self):
        return (
            float(self.lower_edit.value())
            if self.selected_filter_type in ["Bandpass", "Highpass"]
            else None
        )

    @property
    def upper(self):
        return (
            float(self.upper_edit.value())
            if self.selected_filter_type in ["Bandpass", "Lowpass"]
            else None
        )

    @property
    def notch(self):
        return (
            float(self.notch_edit.value())
            if self.selected_filter_type == "Notch"
            else None
        )
