import sys
from collections import Counter
from copy import deepcopy
from os.path import getsize, split, splitext

import mne
from PyQt5.QtCore import pyqtSlot, QStringListModel, QModelIndex
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView)
from mne.io.pick import channel_type

from filterdialog import FilterDialog
from infowidget import InfoWidget


class MainWindow(QMainWindow):
    """MNELAB main window.
    """
    def __init__(self):
        super().__init__()

        self.data = []  # list of loaded data sets
        self.index = -1  # currently active data set
        self.current = None  # copy of currently active data set

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("MNELAB")

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self.open_file_action = file_menu.addAction("&Open...", self.open_file,
                                                    "Ctrl+O")
        self.close_file_action = file_menu.addAction("&Close", self.close_file,
                                                     "Ctrl+W")
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")

        plot_menu = menubar.addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...",
                                                  self.filter_data)
        self.run_ica_action = tools_menu.addAction("&Run ICA...")
        self.import_ica_action = tools_menu.addAction("&Load ICA...",
                                                      self.load_ica)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        help_menu.addAction("About &Qt", self.show_about_qt)

        splitter = QSplitter()
        self.names = QStringListModel()
        self.listview = QListView()
        self.listview.setFocusPolicy(0)
        self.listview.setFrameStyle(0)
        self.listview.setModel(self.names)
        self.listview.clicked.connect(self.activate_data)
        splitter.addWidget(self.listview)
        self.infowidget = InfoWidget()
        splitter.addWidget(self.infowidget)
        width = splitter.size().width()
        splitter.setSizes((width * 0.25, width * 0.75))
        self.setCentralWidget(splitter)

        self._toggle_actions(False)
        self.show()

    def open_file(self):
        """Open file.
        """
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter="*.bdf *.edf")[0]
        if fname:
            self.load_file(fname)

    def load_file(self, fname):
        raw = mne.io.read_raw_edf(fname, stim_channel=None, preload=True)

        new = {"fname": fname, "raw": raw, "events": None}
        name, _ = splitext(split(fname)[-1])

        self._insert_data(new, name)
        self.current = deepcopy(self.data[self.index])

        self.infowidget.set_values(self.get_info())
        self.listview.setCurrentIndex(self.names.index(self.index))
        self._toggle_actions()

    def close_file(self):
        """Close current file.
        """
        self._pop_data(self.index)

        if self.index > -1:  # if there are still open data sets
            self._update_current()
        else:
            self.current = None
            self.infowidget.clear()
            self._toggle_actions(False)

    def get_info(self):
        """Get basic information on current file.
        """
        raw = self.current["raw"]
        fname = self.current["fname"]

        nchan = raw.info["nchan"]
        chans = Counter([channel_type(raw.info, i) for i in range(nchan)])

        return {"File name": fname if fname else "-",
                "Number of channels": raw.info["nchan"],
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans.items()]),
                "Samples": raw.n_times,
                "Sampling frequency": str(raw.info["sfreq"]) + " Hz",
                "Length": str(raw.n_times / raw.info["sfreq"]) + " s",
                "Size in memory": "{:.2f} MB".format(
                    raw._data.nbytes / 1024 ** 2),
                "Size on disk": "-" if not fname else "{:.2f} MB".format(
                    getsize(fname) / 1024 ** 2)}

    @pyqtSlot(QModelIndex)
    def activate_data(self, current):
        """Update index and information based on the file list.
        """
        self.index = current.row()
        self._update_current()

    def plot_raw(self):
        """Plot raw data.
        """
        events = self.current["events"]
        self.current["raw"].plot(events=events)

    def load_ica(self):
        """Load ICA solution from a file.
        """
        fname = QFileDialog.getOpenFileName(self, "Load ICA",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def filter_data(self):
        dialog = FilterDialog()

        if dialog.exec_():
            print(dialog.low, dialog.high)
            self.current["raw"].filter(dialog.low, dialog.high)
            if QMessageBox.question(self, "Add new data set",
                                    "Store the current signals in a new data "
                                    "set?") == QMessageBox.Yes:
                self._insert_data({"fname": "", "raw": self.current["raw"],
                                   "events": None}, "NEW")

    def show_about(self):
        """Show About dialog.
        """
        QMessageBox.about(self, "About MNELAB",
                          "Licensed under the BSD 3-clause license.\n"
                          "Copyright 2017 by Clemens Brunner.")

    def show_about_qt(self):
        """Show About Qt dialog.
        """
        QMessageBox.aboutQt(self, "About Qt")

    def _update_current(self):
        self.current = deepcopy(self.data[self.index])
        self.infowidget.set_values(self.get_info())

    def _insert_data(self, data, name=None):
        """Insert new data set at current index.
        """
        self.index += 1
        self.data.insert(self.index, data)
        self.names.insertRows(self.index, 1)
        if name is None:
            name, _ = splitext(split(data["fname"])[-1])
        self.names.setData(self.names.index(self.index), name)

    def _pop_data(self, index):
        """Remove data set at current index.
        """
        self.data.pop(self.index)
        self.names.removeRows(self.index, 1)
        if self.index >= len(self.data):  # removed last entry in list
            self.index = len(self.data) - 1

    def _toggle_actions(self, enabled=True):
        """Toggle actions.
        """
        self.close_file_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.run_ica_action.setEnabled(enabled)
        self.import_ica_action.setEnabled(enabled)


app = QApplication(sys.argv)
app.setApplicationName("MNELAB")
main = MainWindow()
if len(sys.argv) > 1:  # open files from command line arguments
    for f in sys.argv[1:]:
        main.load_file(f)
sys.exit(app.exec_())
