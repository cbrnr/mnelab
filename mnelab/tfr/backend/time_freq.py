from PyQt5.QtWidgets import (QLineEdit, QLabel)

from ..app.error import show_error

# Miscellaneous functions for reading, saving and initializing parameters
# =====================================================================


def _init_psd_parameters(self):
    """Set the parameters in the parameters text slot
    """
    text = 'fmin=0\nfmax=100\ntmin=Default\ntmax=Default\n'
    if self.ui.psdMethod.currentText() == 'welch':
        text = text + 'n_fft=Default\nn_per_seg=Default\nn_overlap=0'
    if self.ui.psdMethod.currentText() == 'multitaper':
        text = text + 'bandwidth=4'
    self.ui.psdParametersText.setText(text)


# ---------------------------------------------------------------------
def clear_layout(layout):
    """Clear layout."""
    for i in reversed(range(layout.count())):
        layout.itemAt(i).widget().setParent(None)


# ---------------------------------------------------------------------
def _init_tfr_parameters(self):
    """Set the parameters in the parameters text slot
    """
    clear_layout(self.ui.labels)
    clear_layout(self.ui.lines)
    self.ui.labels.addWidget(QLabel('Fmax (Hz)'))
    self.ui.labels.addWidget(QLabel('Fmin (Hz)'))
    self.fmin = QLineEdit()
    self.fmax = QLineEdit()
    self.ui.lines.addWidget(self.fmin)
    self.ui.lines.addWidget(self.fmax)

    if self.data.info['highpass'] is not None:
        self.fmax.setText(str(self.data.info['highpass']))
    else:
        self.fmax.setText(str(self.data.info['sfreq'] / 2))

    if self.data.info['lowpass'] is not None:
        self.fmin.setText(str(self.data.info['lowpass']))
    else:
        self.fmin.setText('0')

    if self.ui.tfrMethodBox.currentText() == 'multitaper':
        self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
        self.ui.labels.addWidget(QLabel('Time Window (s)'))
        self.ui.labels.addWidget(QLabel('Time Bandwidth (s.Hz)'))
        self.fstep = QLineEdit()
        self.time_window, self.time_bandwidth = QLineEdit(), QLineEdit()
        self.ui.lines.addWidget(self.fstep)
        self.ui.lines.addWidget(self.time_window)
        self.ui.lines.addWidget(self.time_bandwidth)
        self.fstep.setText('1')
        self.time_window.setText('0.5')
        self.time_bandwidth.setText('4')
    if self.ui.tfrMethodBox.currentText() == 'morlet':
        self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
        self.ui.labels.addWidget(QLabel('Time Window (s)'))
        self.fstep = QLineEdit()
        self.time_window = QLineEdit()
        self.ui.lines.addWidget(self.fstep)
        self.ui.lines.addWidget(self.time_window)
        self.fstep.setText('1')
        self.time_window.setText('0.5')
    if self.ui.tfrMethodBox.currentText() == 'stockwell':
        self.ui.labels.addWidget(QLabel('Width'))
        self.ui.labels.addWidget(QLabel('FFT points'))
        self.width = QLineEdit()
        self.n_fft = QLineEdit()
        self.ui.lines.addWidget(self.width)
        self.ui.lines.addWidget(self.n_fft)
        self.width.setText('1')
        self.n_fft.setText(str(min(len(self.data.times), 2048)))


# ---------------------------------------------------------------------
def _save_matrix(self):
    """Save the matrix containing the PSD
    """
    n_files = len(self.filePaths)
    if n_files == 1:
        print('Saving one file ...', end='')
        if self.type == 'epochs':
            self.init_epochs_psd()
        if self.type == 'raw':
            self.init_raw_psd()
        self.psd.save_avg_matrix_sef(self.savepath)
        print('done !')

    else:
        from os.path import basename, splitext, join

        print('Batch Processing of {} files'
              .format(len(self.filePaths)))
        n = 0
        for path in self.filePaths:
            print('Saving file {} out of {} ...'
                  .format(n+1, n_files), end='')
            file_name = splitext(basename(path))[0]
            self.ui.dataFilesBox.setCurrentIndex(0)
            if self.type == 'epochs':
                self.init_epochs_psd()
            if self.type == 'raw':
                self.init_raw_psd()

            savepath = join(self.savepath, file_name + '-PSD.sef')
            self.psd.save_avg_matrix_sef(savepath)
            print('done !')
            n += 1


# ---------------------------------------------------------------------
def _read_parameters_tfr(self):
    """Read parameters from txt file and sets it up in params"""

    try:
        self.params = {}
        self.params['fmin'] = float(self.fmin.text())
        self.params['fmax'] = float(self.fmax.text())
        if self.ui.tfrMethodBox.currentText() == 'multitaper':
            self.params['fstep'] = float(self.fstep.text())
            self.params['time_window'] = float(self.time_window().text())
            self.params['time_bandwidth'] = float(self.time_bandwidth.text())
        if self.ui.tfrMethodBox.currentText() == 'morlet':
            self.params['fstep'] = float(self.fstep.text())
            self.params['time_window'] = float(self.time_window().text())
        if self.ui.tfrMethodBox.currentText() == 'stockwell':
            self.params['width'] = float(self.width.text())
            self.params['n_fft'] = float(self.n_fft.text())
        print(self.params)

    except Exception as e:  # Print exception for parameters
        print(e)


# PSD - Init the parameters and open the app functions
# ---------------------------------------------------------------------
def _init_nfft(self):
    """Init the n_fft parameter
    """
    from .util import int_

    n_fft = int_(self.params.get('n_fft', None))
    if n_fft is None:
        if self.type == 'raw':
            n_fft = min(self.data.n_times, 2048)
        if self.type == 'epochs':
            n_fft = min(len(self.data.times), 2048)
        if self.type == 'evoked':
            n_fft = min(len(self.data.times), 2048)
    return n_fft


# ---------------------------------------------------------------------
def _init_epochs_psd(self):
    """Initialize the instance of EpochsPSD
    """
    from .epochs_psd import EpochsPSD
    from .util import float_, int_

    if self.ui.psdMethod.currentText() == 'welch':
        n_fft = _init_nfft(self)
        self.psd = EpochsPSD(
            self.data,
            fmin=float_(self.params['fmin']),
            fmax=float_(self.params['fmax']),
            tmin=float_(self.params['tmin']),
            tmax=float_(self.params['tmax']),
            method='welch',
            n_fft=n_fft,
            n_per_seg=int_(self.params.get('n_per_seg', n_fft)),
            n_overlap=int_(self.params.get('n_overlap', 0)))

    if self.ui.psdMethod.currentText() == 'multitaper':
        self.psd = EpochsPSD(
            self.data,
            fmin=float_(self.params['fmin']),
            fmax=float_(self.params['fmax']),
            tmin=float_(self.params['tmin']),
            tmax=float_(self.params['tmax']),
            method='multitaper',
            bandwidth=float_(self.params.get('bandwidth', 4)))


# ---------------------------------------------------------------------
def _init_raw_psd(self):
    """Initialize the instance of RawPSD
    """
    from .raw_psd import RawPSD
    from .util import float_, int_

    if self.ui.psdMethod.currentText() == 'welch':
        n_fft = _init_nfft(self)
        self.psd = RawPSD(
            self.data,
            fmin=float_(self.params['fmin']),
            fmax=float_(self.params['fmax']),
            tmin=float_(self.params['tmin']),
            tmax=float_(self.params['tmax']),
            method='welch',
            n_fft=n_fft,
            n_per_seg=int_(self.params.get('n_per_seg', n_fft)),
            n_overlap=int_(self.params.get('n_overlap', 0)))

    if self.ui.psdMethod.currentText() == 'multitaper':
        self.psd = RawPSD(
            self.data,
            fmin=float_(self.params['fmin']),
            fmax=float_(self.params['fmax']),
            tmin=float_(self.params['tmin']),
            tmax=float_(self.params['tmax']),
            method='multitaper',
            bandwidth=float_(self.params.get('bandwidth', 4)))


# ---------------------------------------------------------------------
def _open_epochs_psd_visualizer(self):
    """Open PSD visualizer for epochs data
    """
    from ..app.epochs_psd import EpochsPSDWindow

    _init_epochs_psd(self)
    psdVisualizer = EpochsPSDWindow(self.psd, parent=self)
    psdVisualizer.show()


# ---------------------------------------------------------------------
def _open_raw_psd_visualizer(self):
    """Open PSD Visualizer for raw type data
    """
    from ..app.raw_psd import RawPSDWindow

    _init_raw_psd(self)
    psdVisualizer = RawPSDWindow(self.psd, parent=self)
    psdVisualizer.show()


# TFR - Init the parameters and open the app functions
# ---------------------------------------------------------------------
def _init_avg_tfr(self):
    """Init tfr from parameters
    """
    from .avg_epochs_tfr import AvgEpochsTFR
    from .util import float_, int_
    from numpy import arange

    fmin = float_(self.params['fmin'])
    fmax = float_(self.params['fmax'])
    step = float_(self.params.get('freq_step', 1))
    freqs = arange(fmin, fmax, step)
    n_cycles = _init_ncycles(self, freqs)
    n_fft = int_(self.params.get('n_fft', None))

    self.avgTFR = AvgEpochsTFR(
        self.data, freqs, n_cycles,
        method=self.ui.tfrMethodBox.currentText(),
        time_bandwidth=float_(self.params.get('time_bandwidth', 4)),
        width=float_(self.params.get('width', 1)),
        n_fft=n_fft)


# ---------------------------------------------------------------------
def _init_ncycles(self, freqs):
    """Init the n_cycles parameter
    """
    from .util import float_

    # Handling of the time window parameter for multitaper and morlet method
    n_cycles = 0
    if self.ui.tfrMethodBox.currentText() != 'stockwell':
        n_cycles = float_(self.params.get('n_cycles', None))
        if n_cycles is None:
            time_window = float_(self.params.get('time_window', None))
            if time_window is None:
                show_error('Please specify a number of cycles,'
                           + ' or a time_window parameter')
                raise ValueError('Not enough parameters found')
            else:
                n_cycles = freqs * time_window
    return n_cycles


# ---------------------------------------------------------------------
def _open_tfr_visualizer(self):
    """Open TFR Visualizer
    """
    from ..app.avg_epochs_tfr import AvgTFRWindow
    try:
        _init_avg_tfr(self)
        psdVisualizer = AvgTFRWindow(self.avgTFR, parent=self)
        psdVisualizer.show()

    except AttributeError:
        print('Please initialize the EEG data before'
              + ' proceeding.')

    except ValueError:
        print('Time-Window or n_cycles is too high for'
              + 'the length of the signal.\n'
              + 'Please use a smaller Time-Window'
              + ' or less cycles.')
