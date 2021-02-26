import sys
from PyQt5.QtCore import Qt
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QComboBox,
    QSlider,
    QDialogButtonBox,
    QDialog
)

MIN_FS = 100
MAX_FS = 1000
STEP_SIZE = 100
MIN_ALLOWABLE_FS = 0.0001
DECIMAL_PLACES = 4
SUPPORTED_CHANNEL_TYPES = ["", "ecg", "bio", "stim", "eog",
                           "misc", "seeg", "ecog", "mag",
                           "eeg", "ref_meg", "grad", "emg", "hbr", "hbo"]


class NpyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        # initialize settings:
        self.settings = {'ch_type': "misc", 'fs': None, 'standardize': False}

        self.setWindowTitle("Parameters")
        # Create layout for all items.
        outer_form = QVBoxLayout()
        # create form for the text box:
        top_form = QFormLayout()
        # Create a text box for reading the sample rate:
        self.fs = QLineEdit()
        self.fs.setValidator(
            QDoubleValidator(
                MIN_ALLOWABLE_FS,
                sys.float_info.max,
                DECIMAL_PLACES))
        top_form.addRow("Sample Rate (Hz):", self.fs)

        # initialize slider for fs:
        self.fs_slider = QSlider(Qt.Horizontal)
        self.fs_slider.setMinimum(MIN_FS)
        self.fs_slider.setMaximum(MAX_FS)
        self.fs_slider.setValue(MIN_FS)
        self.fs_slider.setTickPosition(QSlider.TicksBelow)
        self.fs_slider.setTickInterval(STEP_SIZE)
        self.fs_slider.setSingleStep(STEP_SIZE)
        self.fs_slider.valueChanged.connect(self.value_change)

        # initialize dropdown for selecting channel type:
        self.ch_type_dropdown = QComboBox()
        self.ch_type_dropdown.addItems(SUPPORTED_CHANNEL_TYPES)
        self.ch_type_dropdown.activated.connect(self.set_type)

        # initialize checkbox for controlling standardization:
        self.standardize = QCheckBox("Standardize Data")

        # initialize accept/deny buttons:
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.button_accept)
        self.buttonbox.rejected.connect(self.reject)

        # build dialog window:
        outer_form.addLayout(top_form)
        outer_form.addWidget(self.fs_slider)
        outer_form.addWidget(self.ch_type_dropdown)
        outer_form.addWidget(self.standardize)
        outer_form.addWidget(self.buttonbox)
        self.setLayout(outer_form)

    def set_type(self):
        """
        sets the channel type based off of the selected item in the dropdown
        menu.
        """
        self.settings['ch_type'] = self.ch_type_dropdown.currentText()
        if self.settings['ch_type'] != "":
            self.settings['ch_type'] = "misc"

    def value_change(self):
        """
        Sets the text bar to match the slider. Is only called when the slider
        is used.
        """
        self.fs.setText(str(self.fs_slider.value()))

    def get_values(self):
        """
        gets the settings from the dialog box
        """
        return self.settings

    def set_values(self):
        """
        Takes the settings from the text box and checkbox, and stores them in
        their respective settings.
        In this case, sets the sample frequency and standardization flag.
        """
        fs = self.fs.text()
        if fs != "":
            fs = float(fs)
        self.settings['fs'] = fs
        self.settings['standardize'] = self.standardize.isChecked()

    def button_accept(self):
        """
        function called when dialog is accepted. Sets all values before closing
        the dialog window.
        """
        self.set_values()
        return self.accept()
