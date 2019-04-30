from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from .ui.time_freq_UI import Ui_TimeFreq


class TimeFreqDialog(QMainWindow):
    """Main Window for time-frequency
    """
    def __init__(self, parent=None, data=None):
        super(TimeFreqDialog, self).__init__(parent)
        self.ui = Ui_TimeFreq()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setup_ui()
        self.data = data
        self.set_informations()

    # Setup functions for UI
    # ========================================================================
    def setup_ui(self):
        self.filePaths = ['']
        self.type = 'raw'
        self.selected_ch = []
        self.selected_events = []
        self.events, self.event_id = None, None
        self.montage = None
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

        (self.ui.plotButton.clicked
         .connect(self.plot_data))

        (self.ui.psdMethod.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.tfrMethodBox.currentIndexChanged
         .connect(self.init_parameters))

        (self.ui.channelButton.clicked
         .connect(self.open_channel_picker))

        (self.ui.psdButton.clicked
         .connect(self.open_psd_visualizer))

        (self.ui.tfrButton.clicked
         .connect(self.open_tfr_visualizer))

        (self.ui.savePsdButton.clicked
         .connect(self.choose_save_path))

    # ---------------------------------------------------------------------
    def plot_data(self):
        """Plot the data
        """
        from matplotlib.pyplot import close, show
        try:
            close('all')
            self.data.plot(block=True, scalings='auto')
            show()
        except AttributeError:
            print('Please initialize the EEG data '
                  + 'before proceeding.')

    # ---------------------------------------------------------------------
    def set_informations(self):
        """Set informations in the information label
        """
        from ..backend.util import init_info_string
        self.ui.infoLabel.setText(init_info_string(self.data))

    # Parameters initialization
    # ========================================================================
    def init_parameters(self):
        """Init the parameters in the text editor
        """
        from ..backend.time_freq import \
            _init_psd_parameters, _init_tfr_parameters

        _init_psd_parameters(self)
        _init_tfr_parameters(self)

    # Channel and events picking functions
    # ========================================================================
    def open_channel_picker(self):
        """Open the channel picker
        """
        from .select_channels import PickChannels

        try:
            channels = self.data.info['ch_names']
            picker = PickChannels(self, channels, self.selected_ch)
            picker.exec_()
        except AttributeError:
            print('Please initialize the EEG data '
                  + 'before proceeding.')

    # ---------------------------------------------------------------------
    def open_events_picker(self):
        """Open the events picker
        """
        from .select_events import PickEvents

        try:
            picker = PickEvents(self, self.event_id.keys(),
                                self.selected_events)
            picker.exec_()
        except AttributeError:
            print('Please initialize the EEG data '
                  + 'before proceeding.')

    # ---------------------------------------------------------------------
    def set_selected_ch(self, selected):
        """Set selected channels
        """
        self.selected_ch = selected

    # ---------------------------------------------------------------------
    def set_selected_events(self, selected):
        """Set selected events
        """
        self.selected_events = selected
        self.ui.eventsLabel.setText(",".join(selected))
        self.init_epochs()
        self.set_informations()

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
            if self.type == 'epochs':
                from ..backend.time_freq import _open_epochs_psd_visualizer
                _open_epochs_psd_visualizer(self)
            elif self.type == 'raw':
                from ..backend.time_freq import _open_raw_psd_visualizer
                _open_raw_psd_visualizer(self)
            else:
                print('Please initialize the EEG data '
                      + 'before proceeding.')

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
            from ..backend.time_freq import _open_tfr_visualizer
            self.data.load_data()
            _open_tfr_visualizer(self)

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
