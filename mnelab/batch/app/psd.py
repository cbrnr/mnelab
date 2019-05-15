from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import mne

from .psd_ui import Ui_PSD


def clear_layout(layout):
    """Clear layout."""
    for i in reversed(range(layout.count())):
        layout.itemAt(i).widget().setParent(None)


class PSDDialog(QDialog):
    """Main Window for time-frequency
    """
    def __init__(self, parent=None, data=None):
        super(PSDDialog, self).__init__(parent)
        self.ui = Ui_PSD()
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
        self.init_parameters()

    # ---------------------------------------------------------------------
    def setup_boxes(self):
        """Setup the boxes with names.
        """
        self.ui.psdMethod.addItem('welch')
        self.ui.psdMethod.addItem('multitaper')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings.
        """
        (self.ui.psdMethod.currentIndexChanged
         .connect(self.init_parameters))

    # Parameters initialization
    # ========================================================================
    def init_parameters(self):
        """Init the parameters in the text editor."""
        self.init_psd_parameters()

    # ---------------------------------------------------------------------
    def init_psd_parameters(self):
        """Set the parameters in the parameters text slot."""
        clear_layout(self.ui.labels)
        clear_layout(self.ui.lines)
        self.ui.labels.addWidget(QLabel('Fmin (Hz)'))
        self.ui.labels.addWidget(QLabel('Fmax (Hz)'))
        self.ui.labels.addWidget(QLabel('Tmin (s)'))
        self.ui.labels.addWidget(QLabel('Tmax (s)'))
        self.fmin = QLineEdit()
        self.fmax = QLineEdit()
        self.tmin = QLineEdit()
        self.tmax = QLineEdit()
        self.ui.lines.addWidget(self.fmin)
        self.ui.lines.addWidget(self.fmax)
        self.ui.lines.addWidget(self.tmin)
        self.ui.lines.addWidget(self.tmax)

        self.fmax.setText('40')
        self.fmin.setText('0')

        if self.ui.psdMethod.currentText() == 'welch':
            self.ui.labels.addWidget(QLabel('FFT points'))
            self.ui.labels.addWidget(QLabel('Length of segments (points)'))
            self.ui.labels.addWidget(
                QLabel('Overlapping of segments (points)'))
            self.n_fft = QLineEdit()
            self.n_per_seg = QLineEdit()
            self.n_overlap = QLineEdit()
            self.ui.lines.addWidget(self.n_fft)
            self.ui.lines.addWidget(self.n_per_seg)
            self.ui.lines.addWidget(self.n_overlap)
            self.n_fft.setText('2048')
            self.n_per_seg.setText(str(int(int(self.n_fft.text()) / 2)))
            self.n_overlap.setText(str(int(int(self.n_fft.text()) / 4)))
        if self.ui.psdMethod.currentText() == 'multitaper':
            self.ui.labels.addWidget(QLabel('Bandwidth (Hz)'))
            self.bandwidth = QLineEdit()
            self.ui.lines.addWidget(self.bandwidth)
            self.bandwidth.setText('4')

    # ---------------------------------------------------------------------
    def read_psd_parameters(self):
        """Read parameters and sets it in a dictionnary."""

        try:
            self.params = {}
            self.params['method'] = self.ui.psdMethod.currentText()
            self.params['fmin'] = float(self.fmin.text())
            self.params['fmax'] = float(self.fmax.text())
            try:
                self.params['tmin'] = float(self.tmin.text())
            except Exception:
                self.params['tmin'] = None
            try:
                self.params['tmax'] = float(self.tmax.text())
            except Exception:
                self.params['tmax'] = None
            if self.ui.psdMethod.currentText() == 'multitaper':
                self.params['bandwidth'] = float(self.bandwidth.text())
            if self.ui.psdMethod.currentText() == 'welch':
                self.params['n_fft'] = int(self.n_fft.text())
                self.params['n_per_seg'] = int(self.n_per_seg.text())
                self.params['n_overlap'] = int(self.n_overlap.text())
            return self.params

        except Exception as e:  # Print exception for parameters
            print(e)
            return None
