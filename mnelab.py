import sys
from collections import Counter
from os.path import getsize, split, splitext

import mne
from PyQt5.QtCore import pyqtSlot, QStringListModel, QModelIndex, QSettings
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel)
from mne.io.pick import channel_type

from datasets import DataSets, DataSet
from filterdialog import FilterDialog
from infowidget import InfoWidget


class MainWindow(QMainWindow):
    """MNELAB main window.
    """
    def __init__(self):
        super().__init__()

        self.MAX_RECENT = 6  # maximum number of recent files
        self.SUPPORTED_FORMATS = "*.bdf *.edf"

        self.datasets = DataSets()
        self.history = []  # command history

        settings = self._read_settings()
        self.recent = settings["recent"] if settings["recent"] else []

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("MNELAB")

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.close_file_action = file_menu.addAction("&Close", self.close_file,
                                                     QKeySequence.Close)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, QKeySequence.Quit)

        plot_menu = menubar.addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...",
                                                  self.filter_data)
        self.find_events_action = tools_menu.addAction("Find &events...",
                                                       self.find_events)
        self.run_ica_action = tools_menu.addAction("&Run ICA...")
        self.import_ica_action = tools_menu.addAction("&Load ICA...",
                                                      self.load_ica)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Show/hide statusbar", self._toggle_statusbar)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        help_menu.addAction("About &Qt", self.show_about_qt)

        self.names = QStringListModel()
        splitter = QSplitter()
        self.sidebar = QListView()
        self.sidebar.setFocusPolicy(0)
        self.sidebar.setFrameStyle(0)
        self.sidebar.setModel(self.names)
        self.sidebar.clicked.connect(self._update_data)
        splitter.addWidget(self.sidebar)
        self.infowidget = InfoWidget()
        splitter.addWidget(self.infowidget)
        width = splitter.size().width()
        splitter.setSizes((width * 0.25, width * 0.75))
        self.setCentralWidget(splitter)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        if settings["statusbar"]:
            self.statusBar().show()
        else:
            self.statusBar().hide()

        self._toggle_actions(False)
        self.show()

    def open_file(self):
        """Open file.
        """
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter=self.SUPPORTED_FORMATS)[0]
        if fname:
            self.load_file(fname)

    def load_file(self, fname):
        raw = mne.io.read_raw_edf(fname, stim_channel=None, preload=True)
        name, ext = splitext(split(fname)[-1])
        self.history.append("raw = mne.io.read_raw_edf('{}', "
                            "stim_channel=None, preload=True)".format(fname))
        self.datasets.insert_data(DataSet(name=name, fname=fname,
                                          ftype=ext[1:].upper(), raw=raw))
        self._update_sidebar()
        self._update_main()
        self._add_recent(fname)
        self._update_statusbar()
        self._toggle_actions()

    def close_file(self):
        """Close current file.
        """
        self.datasets.remove_data()
        self._update_sidebar()
        self._update_main()
        self._update_statusbar()

        if not self.datasets:
            self.infowidget.clear()
            self._toggle_actions(False)
            self.status_label.clear()

    def get_info(self):
        """Get basic information on current file.
        """
        raw = self.datasets.current.raw
        fname = self.datasets.current.fname

        nchan = raw.info["nchan"]
        chans = Counter([channel_type(raw.info, i) for i in range(nchan)])

        if self.datasets.current.events is not None:
            nevents = self.datasets.current.events.shape[0]
        else:
            nevents = None

        if self.datasets.current.ftype is not None:
            ftype = self.datasets.current.ftype
        else:
            ftype = "-"

        return {"File name": fname if fname else "-",
                "File type": ftype,
                "Number of channels": raw.info["nchan"],
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans.items()]),
                "Samples": raw.n_times,
                "Sampling frequency": str(raw.info["sfreq"]) + " Hz",
                "Length": str(raw.n_times / raw.info["sfreq"]) + " s",
                "Events": nevents if nevents is not None else "-",
                "Size in memory": "{:.2f} MB".format(
                    raw._data.nbytes / 1024 ** 2),
                "Size on disk": "-" if not fname else "{:.2f} MB".format(
                    getsize(fname) / 1024 ** 2)}

    def plot_raw(self):
        """Plot raw data.
        """
        events = self.datasets.current.events
        self.datasets.current.raw.plot(events=events)

    def load_ica(self):
        """Load ICA solution from a file.
        """
        fname = QFileDialog.getOpenFileName(self, "Load ICA",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def find_events(self):
        pass

    def filter_data(self):
        dialog = FilterDialog()

        if dialog.exec_():
            low, high = dialog.low, dialog.high
            self.datasets.current.raw.filter(low, high)
            self.history.append("raw.filter({}, {})".format(low, high))
            if QMessageBox.question(self, "Add new data set",
                                    "Store the current signals in a new data "
                                    "set?") == QMessageBox.Yes:
                new = DataSet(name="NEW", raw=self.datasets.current.raw)
                self.datasets.insert_data(new)
                self._update_sidebar()
                self._update_main()
                self._update_statusbar()

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

    def _update_sidebar(self):
        self.names.setStringList(self.datasets.names)
        self.sidebar.setCurrentIndex(self.names.index(self.datasets.index))

    def _update_main(self):
        if self.datasets:
            self.infowidget.set_values(self.get_info())
        else:
            self.infowidget.clear()

    def _update_statusbar(self):
        if self.datasets:
            mb = self.datasets.nbytes / 1024 ** 2
            self.status_label.setText("Total Memory: {:.2f} MB".format(mb))
        else:
            self.status_label.clear()

    def _toggle_actions(self, enabled=True):
        """Toggle actions.
        """
        self.close_file_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.find_events_action.setEnabled(enabled)
        self.run_ica_action.setEnabled(enabled)
        self.import_ica_action.setEnabled(enabled)

    def _add_recent(self, fname):
        if fname in self.recent:  # avoid duplicates
            self.recent.remove(fname)
        self.recent.insert(0, fname)
        while len(self.recent) > self.MAX_RECENT:  # prune list
            self.recent.pop()
        self._write_settings()
        if not self.recent_menu.isEnabled():
            self.recent_menu.setEnabled(True)

    def _write_settings(self):
        settings = QSettings()
        if self.recent:
            settings.setValue("recent", self.recent)
        settings.setValue("statusbar", not self.statusBar().isHidden())

    def _read_settings(self):
        settings = QSettings()
        recent = settings.value("recent")
        statusbar = settings.value("statusbar")
        if (statusbar is None) or (statusbar == "true"):
            statusbar = True
        else:
            statusbar = False
        return {"recent": recent, "statusbar": statusbar}

    @pyqtSlot(QModelIndex)
    def _update_data(self, selected):
        """Update index and information based on the state of the sidebar.
        """
        if selected.row() != self.datasets.index:
            self.datasets.index = selected.row()
            self.datasets.update_current()
            self._update_main()

    @pyqtSlot()
    def _update_recent_menu(self):
        self.recent_menu.clear()
        for recent in self.recent:
            self.recent_menu.addAction(recent)

    @pyqtSlot(QAction)
    def _load_recent(self, action):
        self.load_file(action.text())

    @pyqtSlot()
    def _toggle_statusbar(self):
        if self.statusBar().isHidden():
            self.statusBar().show()
        else:
            self.statusBar().hide()
        self._write_settings()

    def closeEvent(self, event):
        print("\nCommand History")
        print("===============")
        print("\n".join(self.history))
        event.accept()


app = QApplication(sys.argv)
app.setApplicationName("MNELAB")
app.setOrganizationName("cbrnr")
main = MainWindow()
if len(sys.argv) > 1:  # open files from command line arguments
    for f in sys.argv[1:]:
        main.load_file(f)
sys.exit(app.exec_())
