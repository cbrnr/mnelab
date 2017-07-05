import sys
from collections import Counter
from os.path import getsize, split, splitext

import matplotlib
import mne
from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar)
from mne.io.pick import channel_type
from mne.filter import filter_data

from datasets import DataSets, DataSet
from filterdialog import FilterDialog
from infowidget import InfoWidget


__version__ = "0.1.0"


class MainWindow(QMainWindow):
    """MNELAB main window.
    """
    def __init__(self):
        super().__init__()

        self.MAX_RECENT = 6  # maximum number of recent files
        self.SUPPORTED_FORMATS = "*.bdf *.edf"

        self.all = DataSets()  # contains currently loaded data sets
        self.history = []  # command history

        settings = self._read_settings()
        self.recent = settings["recent"]  # list of recent files

        if settings["geometry"]:
            self.restoreGeometry(settings["geometry"])
        else:
            self.setGeometry(300, 300, 1000, 750)  # default window size
            self.move(QApplication.desktop().screen().rect().center() -
                      self.rect().center())  # center window
        if settings["state"]:
            self.restoreState(settings["state"])

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
        self.plot_psd_action = plot_menu.addAction("&Power spectral "
                                                   "density...", self.plot_psd)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...",
                                                  self.filter_data)
        self.setref_action = tools_menu.addAction("&Set reference channels...",
                                                  self.set_reference)
        self.reref_action = tools_menu.addAction("&Re-reference data...",
                                                 self.re_reference)
        self.find_events_action = tools_menu.addAction("Find &events...",
                                                       self.find_events)
        self.run_ica_action = tools_menu.addAction("Run &ICA...")
        self.import_ica_action = tools_menu.addAction("&Load ICA...",
                                                      self.load_ica)

        view_menu = menubar.addMenu("&View")
        statusbar_action = view_menu.addAction("Statusbar",
                                               self._toggle_statusbar)
        statusbar_action.setCheckable(True)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        help_menu.addAction("About &Qt", self.show_about_qt)

        self.names = QStringListModel()
        self.names.dataChanged.connect(self._update_names)
        splitter = QSplitter()
        self.sidebar = QListView()
        self.sidebar.setFrameStyle(QFrame.NoFrame)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setModel(self.names)
        self.sidebar.clicked.connect(self._update_data)
        splitter.addWidget(self.sidebar)
        self.infowidget = InfoWidget()
        splitter.addWidget(self.infowidget)
        width = splitter.size().width()
        splitter.setSizes((width * 0.3, width * 0.7))
        self.setCentralWidget(splitter)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        if settings["statusbar"]:
            self.statusBar().show()
            statusbar_action.setChecked(True)
        else:
            self.statusBar().hide()
            statusbar_action.setChecked(False)

        self._toggle_actions(False)
        self.show()

    def open_file(self):
        """Show open file dialog.
        """
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter=self.SUPPORTED_FORMATS)[0]
        if fname:
            self.load_file(fname)

    def load_file(self, fname):
        """Load file.

        Parameters
        ----------
        fname : str
            File name.
        """
        # TODO: check if fname exists
        raw = mne.io.read_raw_edf(fname, stim_channel=None, preload=True)
        name, ext = splitext(split(fname)[-1])
        self.history.append("raw = mne.io.read_raw_edf('{}', "
                            "stim_channel=None, preload=True)".format(fname))
        self.all.insert_data(DataSet(name=name, fname=fname,
                                     ftype=ext[1:].upper(), raw=raw))
        self._update_sidebar(self.all.names, self.all.index)
        self._update_infowidget()
        self._update_statusbar()
        self._add_recent(fname)
        self._toggle_actions()

    def close_file(self):
        """Close current file.
        """
        self.all.remove_data()
        self._update_sidebar(self.all.names, self.all.index)
        self._update_infowidget()
        self._update_statusbar()

        if not self.all:
            self._toggle_actions(False)

    def get_info(self):
        """Get basic information on current file.

        Returns
        -------
        info : dict
            Dictionary with information on current file.
        """
        raw = self.all.current.raw
        fname = self.all.current.fname
        ftype = self.all.current.ftype

        nchan = raw.info["nchan"]
        chans = Counter([channel_type(raw.info, i) for i in range(nchan)])

        if self.all.current.events:
            nevents = self.all.current.events.shape[0]
        else:
            nevents = None

        return {"File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Number of channels": nchan,
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans.items()]),
                "Samples": raw.n_times,
                "Sampling frequency": str(raw.info["sfreq"]) + " Hz",
                "Length": str(raw.n_times / raw.info["sfreq"]) + " s",
                "Events": nevents if nevents else "-",
                "Reference": "-",
                "Size in memory": "{:.2f} MB".format(
                    raw._data.nbytes / 1024 ** 2),
                "Size on disk": "-" if not fname else "{:.2f} MB".format(
                    getsize(fname) / 1024 ** 2)}

    def plot_raw(self):
        """Plot raw data.
        """
        events = self.all.current.events
        nchan = 16  #self.datasets.current.raw.info["nchan"]
        fig = self.all.current.raw.plot(events=events, n_channels=nchan,
                                        show=False)
        self.history.append("raw.plot(n_channels={})".format(nchan))
        win = fig.canvas.manager.window
        win.setWindowTitle("Raw data")
        win.findChild(QStatusBar).hide()
        fig.show()

    def plot_psd(self):
        fig = self.all.current.raw.plot_psd(average=False,
                                            spatial_colors=False, show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Power spectral density")
        fig.show()

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
            filtered = filter_data(self.all.current.raw._data,
                                   self.all.current.raw.info["sfreq"],
                                   l_freq=low, h_freq=high)
            self.history.append("raw.filter({}, {})".format(low, high))

            # if current data is stored in a file we create a new data set with
            # the modified data
            if self.all.current.fname:
                self.all.current.raw._data = filtered
                new = DataSet(name=self.all.current.name + " (filtered)",
                              raw=self.all.current.raw)
                self.all.insert_data(new)
                self._update_sidebar(self.all.names, self.all.index)
                self._update_infowidget()
                self._update_statusbar()
            # otherwise ask if the current data set should be overwritten (in
            # memory) or if a new data set should be created
            else:
                msg = QMessageBox.question(self, "Overwrite existing data set",
                                           "Overwrite existing data set?")
                if msg == QMessageBox.No:  # create new data set
                    copy = self.all.current.raw.copy()
                    copy._data = filtered
                    new = DataSet(name=self.all.current.name +
                                  " (filtered)", raw=copy)
                    self.all.insert_data(new)
                    self._update_sidebar(self.all.names, self.all.index)
                    self._update_infowidget()
                    self._update_statusbar()
                else:  # overwrite existing data set
                    self.all.current.raw._data = filtered
                    idx = self.all.index
                    self.all.data[idx] = self.all.current

    def set_reference(self):
        pass

    def re_reference(self):
        pass

    def show_about(self):
        """Show About dialog.
        """
        msg = """<b>MNELAB {}</b><br/><br/>
        <a href="https://github.com/cbrnr/mnelab">MNELAB</a> - a graphical user
        interface for
        <a href="https://github.com/mne-tools/mne-python">MNE</a>.<br/><br/>
        This program uses MNE version {}.<br/><br/>
        Licensed under the BSD 3-clause license.<br/>
        Copyright 2017 by Clemens Brunner.""".format(__version__,
                                                     mne.__version__)
        QMessageBox.about(self, "About MNELAB", msg)

    def show_about_qt(self):
        """Show About Qt dialog.
        """
        QMessageBox.aboutQt(self, "About Qt")

    def _update_sidebar(self, names, index):
        """Update (overwrite) sidebar with names and current index.
        """
        self.names.setStringList(names)
        self.sidebar.setCurrentIndex(self.names.index(index))

    def _update_infowidget(self):
        if self.all:
            self.infowidget.set_values(self.get_info())
        else:
            self.infowidget.clear()

    def _update_statusbar(self):
        if self.all:
            mb = self.all.nbytes / 1024 ** 2
            self.status_label.setText("Total Memory: {:.2f} MB".format(mb))
        else:
            self.status_label.clear()

    def _toggle_actions(self, enabled=True):
        """Toggle actions.

        Parameters
        ----------
        enabled : bool
            Specifies whether actions should be enabled (True) or disabled
            (False).
        """
        self.close_file_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.plot_psd_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.setref_action.setEnabled(enabled)
        self.reref_action.setEnabled(enabled)
        self.find_events_action.setEnabled(enabled)
        self.run_ica_action.setEnabled(enabled)
        self.import_ica_action.setEnabled(enabled)

    def _add_recent(self, fname):
        """Add a file to recent file list.

        Parameters
        ----------
        fname : str
            File name.
        """
        if fname in self.recent:  # avoid duplicates
            self.recent.remove(fname)
        self.recent.insert(0, fname)
        while len(self.recent) > self.MAX_RECENT:  # prune list
            self.recent.pop()
        self._write_settings()
        if not self.recent_menu.isEnabled():
            self.recent_menu.setEnabled(True)

    def _write_settings(self):
        """Write application settings.
        """
        settings = QSettings()
        if self.recent:
            settings.setValue("recent", self.recent)
        settings.setValue("statusbar", not self.statusBar().isHidden())
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def _read_settings(self):
        """Read application settings.

        Returns
        -------
        settings : dict
            The restored settings values are returned in a dictionary for
            further processing.
        """
        settings = QSettings()

        recent = settings.value("recent")
        if not recent:
            recent = []  # default is empty list

        statusbar = settings.value("statusbar")
        if (not statusbar) or (statusbar == "true"):  # default is True
            statusbar = True
        else:
            statusbar = False

        geometry = settings.value("geometry")

        state = settings.value("state")

        return {"recent": recent, "statusbar": statusbar, "geometry": geometry,
                "state": state}

    @pyqtSlot(QModelIndex)
    def _update_data(self, selected):
        """Update index and information based on the state of the sidebar.

        Parameters
        ----------
        selected : QModelIndex
            Index of the selected row.
        """
        if selected.row() != self.all.index:
            self.all.index = selected.row()
            self.all.update_current()
            self._update_infowidget()

    @pyqtSlot(QModelIndex, QModelIndex)
    def _update_names(self, start, stop):
        """Update names in DataSets after changes in sidebar.
        """
        for index in range(start.row(), stop.row() + 1):
            self.all.data[index].name = self.names.stringList()[index]
        if self.all.index in range(start.row(), stop.row() + 1):
            self.all.current.name = self.all.names[self.all.index]

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

    @pyqtSlot(QEvent)
    def closeEvent(self, event):
        """Close application.

        Parameters
        ----------
        event : QEvent
            Close event.
        """
        self._write_settings()
        if self.history:
            print("\nCommand History")
            print("===============")
            print("\n".join(self.history))
        QApplication.quit()


matplotlib.use("Qt5Agg")
app = QApplication(sys.argv)
app.setApplicationName("MNELAB")
app.setOrganizationName("cbrnr")
main = MainWindow()
if len(sys.argv) > 1:  # open files from command line arguments
    for f in sys.argv[1:]:
        main.load_file(f)
sys.exit(app.exec_())
