from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from .ui.psd_UI import Ui_PSD


class TimeFreqDialog(QDialog):
    """Main Window for time-frequency
    """
    def __init__(self, parent=None, data=None):
        super(TimeFreqDialog, self).__init__(parent)
        self.ui = Ui_TimeFreq()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setup_ui()
        self.data = data
        try:
            if len(data.get_data().shape) == 3:
                self.type = 'epochs'
            else:
                self.type = 'raw'
        except AttributeError:
            self.type = 'evoked'

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
        self.ui.psdMethod.addItem('welch')
        self.ui.psdMethod.addItem('multitaper')
        self.ui.tfrMethodBox.addItem('stockwell')
        self.ui.tfrMethodBox.addItem('morlet')
        self.ui.tfrMethodBox.addItem('multitaper')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings
        """

        (self.ui.psdMethod.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.tfrMethodBox.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.psdButton.clicked
         .connect(self.open_psd_visualizer))

        (self.ui.tfrButton.clicked
         .connect(self.open_tfr_visualizer))

        (self.ui.savePsdButton.clicked
         .connect(self.choose_save_path))

    # Parameters initialization
    # ========================================================================
    def init_parameters(self):
        """Init the parameters in the text editor
        """
        from ..backend.time_freq import \
            _init_psd_parameters, _init_tfr_parameters

        _init_psd_parameters(self)
        _init_tfr_parameters(self)

    # Open PSD Visualizer
    # ========================================================================
    def open_psd_visualizer(self):
        """Redirect to PSD Visualize app
        """
        try:
            from ..backend.time_freq import _read_parameters
            _read_parameters(self)

        except (AttributeError, FileNotFoundError, OSError):
            print('Cannot find/read Parameters.\n'
                  + 'Please verify the path and extension')
        else:
            #try:
            if self.type == 'epochs':
                from ..backend.time_freq import _open_epochs_psd_visualizer
                _open_epochs_psd_visualizer(self)
            elif self.type == 'raw' or self.type == 'evoked':
                from ..backend.time_freq import _open_raw_psd_visualizer
                _open_raw_psd_visualizer(self)
            else:
                print('Please initialize the EEG data '
                      + 'before proceeding.')
            #except Exception as e:
            #    print(e)

    # Open TFR Visualizer
    # ========================================================================
    def open_tfr_visualizer(self):
        """Open TFR Visualizer for epochs
        """
        try:
            from ..backend.time_freq import _read_parameters
            _read_parameters(self, True)

        except (AttributeError, FileNotFoundError, OSError):
            print('Cannot find/read file.\n'
                  + 'Please verify the path and extension')
        else:
            try:
                from ..backend.time_freq import _open_tfr_visualizer
                self.data.load_data()
                _open_tfr_visualizer(self)
            except Exception as e:
                print(e)

    # Saving
    # ========================================================================
    def choose_save_path(self):
        """Open window for choosing save path
        """
        if len(self.filePaths) == 1:
            self.savepath, _ = QFileDialog.getSaveFileName(self)
        else:
            self.savepath = QFileDialog.getExistingDirectory(self)

        try:
            self.read_parameters()
        except (AttributeError, FileNotFoundError, OSError):
            print('Cannot find/read file:(\n'
                  + 'Please verify the path and extension')
        else:
            self.save_matrix()

    # ---------------------------------------------------------------------
    def save_matrix(self):
        """Save the matrix containing the PSD
        """
        from ..backend.time_freq import _save_matrix
        _save_matrix(self)
