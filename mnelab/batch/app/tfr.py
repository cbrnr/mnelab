from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import mne

from .tfr_ui import Ui_TimeFreq


def clear_layout(layout):
    """Clear layout."""
    for i in reversed(range(layout.count())):
        layout.itemAt(i).widget().setParent(None)


class TimeFreqDialog(QDialog):
    """Main Window for time-frequency.
    """
    def __init__(self, parent=None):
        super(TimeFreqDialog, self).__init__(parent)
        self.ui = Ui_TimeFreq()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.setup_ui()

    # Setup functions for UI
    # ========================================================================
    def setup_ui(self):
        self.set_bindings()
        self.setup_boxes()
        self.init_tfr_parameters()

    # ---------------------------------------------------------------------
    def setup_boxes(self):
        """Setup the boxes with names.
        """
        self.ui.tfrMethodBox.addItem('stockwell')
        self.ui.tfrMethodBox.addItem('morlet')
        self.ui.tfrMethodBox.addItem('multitaper')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings.
        """
        (self.ui.tfrMethodBox.currentIndexChanged
         .connect(self.init_tfr_parameters))

    # ---------------------------------------------------------------------
    def init_tfr_parameters(self):
        """Set the parameters in the parameters text slot
        """
        clear_layout(self.ui.labels)
        clear_layout(self.ui.lines)
        self.ui.labels.addWidget(QLabel('Fmin (Hz)'))
        self.ui.labels.addWidget(QLabel('Fmax (Hz)'))
        self.fmin = QLineEdit()
        self.fmax = QLineEdit()
        self.ui.lines.addWidget(self.fmin)
        self.ui.lines.addWidget(self.fmax)

        self.fmax.setText('40')
        self.fmin.setText('0')

        if self.ui.tfrMethodBox.currentText() == 'multitaper':
            self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
            self.tfr_param = QComboBox()
            self.tfr_param.addItem('Time Window (s)')
            self.tfr_param.addItem('Number of cycles')
            self.ui.labels.addWidget(self.tfr_param)
            self.ui.labels.addWidget(QLabel('Time Bandwidth (s.Hz)'))
            self.fstep = QLineEdit()
            self.time_bandwidth = QLineEdit()
            self.cycles = QLineEdit()
            self.ui.lines.addWidget(self.fstep)
            self.ui.lines.addWidget(self.cycles)
            self.ui.lines.addWidget(self.time_bandwidth)
            self.fstep.setText('1')
            self.cycles.setText('0.5')
            self.time_bandwidth.setText('4')
        if self.ui.tfrMethodBox.currentText() == 'morlet':
            self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
            self.tfr_param = QComboBox()
            self.tfr_param.addItem('Time Window (s)')
            self.tfr_param.addItem('Number of cycles')
            self.ui.labels.addWidget(self.tfr_param)
            self.fstep = QLineEdit()
            self.cycles = QLineEdit()
            self.ui.lines.addWidget(self.fstep)
            self.ui.lines.addWidget(self.cycles)
            self.fstep.setText('1')
            self.cycles.setText('0.5')
        if self.ui.tfrMethodBox.currentText() == 'stockwell':
            self.ui.labels.addWidget(QLabel('Width'))
            self.ui.labels.addWidget(QLabel('FFT points'))
            self.width = QLineEdit()
            self.n_fft = QLineEdit()
            self.ui.lines.addWidget(self.width)
            self.ui.lines.addWidget(self.n_fft)
            self.width.setText('1')
            self.n_fft.setText('2048')

    # ---------------------------------------------------------------------
    def read_tfr_parameters(self):
        """Read parameters from txt file and sets it up in params"""

        try:
            self.params = {}
            self.params['method'] = self.ui.tfrMethodBox.currentText()
            self.params['fmin'] = float(self.fmin.text())
            self.params['fmax'] = float(self.fmax.text())
            if self.ui.tfrMethodBox.currentText() == 'multitaper':
                self.params['fstep'] = float(self.fstep.text())
                if self.tfr_param.currentText == 'Time Window (s)':
                    self.params['time_window'] = float(self.cycles.text())
                    self.params['n_cycles'] = None
                else:
                    self.params['n_cycles'] = float(self.cycles.text())
                    self.params['time_window'] = None
                self.params['time_bandwidth'] = float(
                    self.time_bandwidth.text())
            if self.ui.tfrMethodBox.currentText() == 'morlet':
                self.params['fstep'] = float(self.fstep.text())
                if self.tfr_param.currentText == 'Time Window (s)':
                    self.params['time_window'] = float(self.cycles.text())
                    self.params['n_cycles'] = None
                else:
                    self.params['n_cycles'] = float(self.cycles.text())
                    self.params['time_window'] = None
            if self.ui.tfrMethodBox.currentText() == 'stockwell':
                self.params['width'] = float(self.width.text())
                self.params['n_fft'] = int(self.n_fft.text())
                self.params['time_window'] = None
                self.params['n_cycles'] = None

            return self.params

        except Exception as e:  # Print exception for parameters
            print(e)
            return None
