import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import mne

from .batch_ui import Ui_BatchDialog
from .utils import _read, init_avg_tfr, init_epochs_psd, init_raw_psd
from .tfr import TimeFreqDialog
from .psd import PSDDialog


class BatchDialog(QDialog):
    """Main dialog window for batch processing."""

    def __init__(self, parent=None):
        super(BatchDialog, self).__init__(parent)
        self.ui = Ui_BatchDialog()
        self.ui.setupUi(self)
        self.set_bindings()
        self.ui.listWidget.setSelectionMode(QListWidget.NoSelection)
        self.fnames = []
        self.savePath = ''

    def set_bindings(self):
        self.ui.dirButton.clicked.connect(self.open_files)
        self.ui.startBatch.clicked.connect(self.batch_process)
        self.ui.pushButton.clicked.connect(self.choose_save_path)
        self.ui.tfrParams.clicked.connect(self.open_tfr)
        self.ui.psdParams.clicked.connect(self.open_psd)

    def open_files(self):
        fnames, _ = QFileDialog.getOpenFileNames(
            self, "Select files for batch processing...",
            "", "*.fif")
        self.ui.directory.setText(os.path.dirname(fnames[0]))
        if self.savePath == '':
            self.set_save_path(os.path.dirname(fnames[0]))
        names = [os.path.basename(fname) for fname in fnames]
        self.ui.listWidget.clear()
        self.ui.listWidget.insertItems(0, names)
        self.fnames = fnames

    def set_save_path(self, path):
        self.savePath = path
        self.ui.savePath.setText(path)

    def choose_save_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select save folder...", "")
        self.set_save_path(path)

    def open_tfr(self):
        dialog = TimeFreqDialog(self)
        if dialog.exec_():
            self.tfr_params = dialog.read_tfr_parameters()
            self.ui.tfrLabel.setText(str(self.tfr_params))

    def open_psd(self):
        dialog = PSDDialog(self)
        if dialog.exec_():
            self.psd_params = dialog.read_psd_parameters()
            self.ui.psdLabel.setText(str(self.psd_params))

    def batch_process(self):
        """Starts batch processing."""

        for fname in self.fnames:
            data, type = _read(fname)
            ending = ''

            # Filtering
            if self.ui.filterBox.isChecked():
                low = float(self.ui.low.text())
                high = float(self.ui.high.text())
                data.filter(low, high)
                ending = ending + '_filtered_{}-{}'.format(low, high)

            # Resampling
            if self.ui.samplingBox.isChecked():
                sfreq = float(self.ui.sfreq.text())
                data.resample(sfreq)
                ending = ending + '_resampled_{}'.format(sfreq)

            if (self.ui.filterBox.isChecked() or
                    self.ui.samplingBox.isChecked()):
                name, format = os.path.splitext(os.path.basename(fname))
                save_name = os.path.join(self.savePath,
                                         name + ending + format)
                data.save(save_name)

            # Computing tfr
            if self.ui.tfrBox.isChecked():
                try:
                    name, format = os.path.splitext(os.path.basename(fname))
                    save_name = os.path.join(self.savePath,
                                             name + '_tfr.h5')
                    avgTfr = init_avg_tfr(data, self.tfr_params)
                    avgTfr.tfr.save(save_name)
                except Exception as e:
                    print(name, (" time-frequency computing "
                                 + "encountered a problem..."))
                    print(e)

            # Computing PSD
            if self.ui.psdBox.isChecked():
                try:
                    name, format = os.path.splitext(os.path.basename(fname))
                    save_name = os.path.join(self.savePath,
                                             name + '_psd.h5')
                    if type == 'raw' or type == 'evoked':
                        psd = init_raw_psd(data, self.psd_params)
                        psd.save_hdf5(save_name)
                    elif type == 'epochs':
                        psd = init_epochs_psd(data, self.psd_params)
                        psd.save_hdf5(save_name)
                except Exception as e:
                    print(name, (" PSD computing "
                                 + "encountered a problem..."))
                    print(e)
