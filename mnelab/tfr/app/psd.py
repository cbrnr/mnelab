from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from collections import Counter
import mne

from .ui.psd_UI import Ui_PSD


class PSDDialog(QDialog):
    """Main Window for time-frequency
    """
    def __init__(self, parent=None, data=None):
        super(PSDDialog, self).__init__(parent)
        self.ui = Ui_PSD()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.data = data
        try:
            if len(data.get_data().shape) == 3:
                self.type = 'epochs'
            else:
                self.type = 'raw'
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
        """Setup the boxes with names.
        """
        self.ui.psdMethod.addItem('welch')
        self.ui.psdMethod.addItem('multitaper')
        chans = Counter([mne.io.pick.channel_type(self.data.info, i)
                         for i in range(self.data.info["nchan"])])
        if chans['eeg']:
            self.ui.typeBox.addItem('eeg')
        if chans['mag']:
            self.ui.typeBox.addItem('mag')
        if chans['grad']:
            self.ui.typeBox.addItem('grad')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings.
        """
        (self.ui.psdMethod.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.psdButton.clicked
         .connect(self.open_psd_visualizer))

    # Parameters initialization
    # ========================================================================
    def init_parameters(self):
        """Init the parameters in the text editor.
        """
        from ..backend.time_freq import _init_psd_parameters

        _init_psd_parameters(self)

    # Open PSD Visualizer
    # ========================================================================
    def open_psd_visualizer(self):
        """Redirect to PSD Visualize app.
        """
        try:
            from ..backend.time_freq import _read_psd_parameters
            _read_psd_parameters(self)

        except (AttributeError, FileNotFoundError, OSError):
            print('Cannot find/read Parameters.\n'
                  + 'Please verify the path and extension')
        else:
            try:
                if self.type == 'epochs':
                    from ..backend.time_freq import _open_epochs_psd_visualizer
                    _open_epochs_psd_visualizer(self)
                elif self.type == 'raw' or self.type == 'evoked':
                    from ..backend.time_freq import _open_raw_psd_visualizer
                    _open_raw_psd_visualizer(self)
                else:
                    print('Please initialize the EEG data '
                          + 'before proceeding.')
            except Exception as e:
                print(e)
