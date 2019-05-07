from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from .ui.time_freq_UI import Ui_TimeFreq


class TimeFreqDialog(QDialog):
    """Main Window for time-frequency
    """
    def __init__(self, parent=None, data=None):
        super(TimeFreqDialog, self).__init__(parent)
        self.ui = Ui_TimeFreq()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.data = data
        try:
            if len(data.get_data().shape) == 3:
                self.type = 'epochs'
        except AttributeError:
            self.type = 'evoked'
        self.setup_ui()

    # Setup functions for UI
    # ========================================================================
    def setup_ui(self):
        self.set_bindings()
        self.setup_boxes()
        self.init_parameters()

    # ---------------------------------------------------------------------
    def setup_boxes(self):
        """Setup the boxes with names
        """
        self.ui.tfrMethodBox.addItem('stockwell')
        self.ui.tfrMethodBox.addItem('morlet')
        self.ui.tfrMethodBox.addItem('multitaper')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings
        """
        (self.ui.tfrMethodBox.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.tfrButton.clicked
         .connect(self.open_tfr_visualizer))

    # Parameters initialization
    # ========================================================================
    def init_parameters(self):
        """Init the parameters in the text editor
        """
        from ..backend.time_freq import _init_tfr_parameters

        _init_tfr_parameters(self)

    # Open TFR Visualizer
    # ========================================================================
    def open_tfr_visualizer(self):
        """Open TFR Visualizer for epochs
        """
        try:
            from ..backend.time_freq import _read_tfr_parameters
            _read_tfr_parameters(self)

        except (AttributeError, FileNotFoundError, OSError):
            print('Cannot find/read file.\n'
                  + 'Please verify the path and extension')
        else:
            try:
                from ..backend.time_freq import _open_tfr_visualizer
                try:
                    self.data.load_data()
                except AttributeError:
                    pass
                _open_tfr_visualizer(self)

            except Exception as e:
                print(e)
