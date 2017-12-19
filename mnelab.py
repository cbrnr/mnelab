import sys
from collections import Counter
from os.path import exists, getsize, join, split, splitext
from os import listdir

import numpy as np
import matplotlib
import mne
from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt, QObject)
from PyQt5.QtGui import QKeySequence, QDropEvent
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar, QToolBar)
from mne.filter import filter_data
from mne.io.pick import channel_type

from dialogs.filterdialog import FilterDialog
from dialogs.pickchannelsdialog import PickChannelsDialog
from dialogs.referencedialog import ReferenceDialog
from dialogs.montagedialog import MontageDialog
from utils.datasets import DataSets, DataSet
from widgets.infowidget import InfoWidget


__version__ = "0.1.0"


data = DataSets()  # contains currently loaded data sets
history = []  # command history
MAX_RECENT = 6  # maximum number of recent files
SUPPORTED_FORMATS = "*.bdf *.edf *.vhdr"


class MainWindow(QMainWindow):
    """MNELAB main window.
    """
    def __init__(self):
        super().__init__()

        # restore settings
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

        # initialize menus
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.close_file_action = file_menu.addAction("&Close", self.close_file,
                                                     QKeySequence.Close)
        self.close_all_action = file_menu.addAction("Close all",
                                                    self.close_all)
        file_menu.addSeparator()
        self.import_bad_action = file_menu.addAction("Import bad channels...",
                                                     self.import_bads)
        self.import_anno_action = file_menu.addAction("Import annotations...",
                                                      self.import_annotations)
        file_menu.addSeparator()
        self.export_bad_action = file_menu.addAction("Export &bad channels...",
                                                     self.export_bads)
        self.export_anno_action = file_menu.addAction("Export &annotations...",
                                                      self.export_annotations)
        self.export_events_action = file_menu.addAction("Export &events...",
                                                        self.export_events)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, QKeySequence.Quit)

        edit_menu = menubar.addMenu("&Edit")
        self.pick_chans_action = edit_menu.addAction("Pick &channels...",
                                                     self.pick_channels)
        self.set_bads_action = edit_menu.addAction("Set &bad channels...",
                                                   self.set_bads)
        self.set_montage_action = edit_menu.addAction("Set &montage...",
                                                      self.set_montage)
        edit_menu.addSeparator()
        self.setref_action = edit_menu.addAction("&Set reference...",
                                                 self.set_reference)

        plot_menu = menubar.addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)
        self.plot_psd_action = plot_menu.addAction("&Power spectral "
                                                   "density...", self.plot_psd)
        self.plot_montage_action = plot_menu.addAction("Current &montage",
                                                       self.plot_montage)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...",
                                                  self.filter_data)
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

        # set up data model for sidebar (list of open files)
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

        self.setAcceptDrops(True)

        self._toggle_actions(False)
        self.show()

    def open_file(self):
        """Show open file dialog.
        """
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter=SUPPORTED_FORMATS)[0]
        if fname:
            self.load_file(fname)

    def load_file(self, fname):
        """Load file.

        Parameters
        ----------
        fname : str
            File name.
        """
        if not exists(fname):
            QMessageBox.critical(self, "File not found",
                                 "{} does not exist.".format(fname))
            self._remove_recent(fname)
            return
        name, ext = splitext(split(fname)[-1])
        ftype = ext[1:].upper()
        if ext not in SUPPORTED_FORMATS:
            raise ValueError("File format {} is not supported.".format(ftype))

        if ext in ['.edf', '.bdf']:
            raw = mne.io.read_raw_edf(fname, stim_channel=-1, preload=True)
            history.append("raw = mne.io.read_raw_edf('{}', "
                           "stim_channel=-1, preload=True)".format(fname))
        elif ext in ['.vhdr']:
            raw = mne.io.read_raw_brainvision(fname, preload=True)
            history.append("raw = mne.io.read_raw_brainvision('{}', "
                           "preload=True)".format(fname))

        data.insert_data(DataSet(name=name, fname=fname, ftype=ftype, raw=raw))
        self.find_events()
        self._update_sidebar(data.names, data.index)
        self._update_infowidget()
        self._update_statusbar()
        self._add_recent(fname)
        self._toggle_actions()

    def export_bads(self):
        """Export bad channels info to a CSV file.
        """
        fname = QFileDialog.getSaveFileName(self, "Export bad channels",
                                            filter="*.csv")[0]
        if fname:
            name, ext = splitext(split(fname)[-1])
            ext = ext if ext else ".csv"  # automatically add extension
            fname = join(split(fname)[0], name + ext)
            with open(fname, "w") as f:
                f.write(",".join(data.current.raw.info["bads"]))

    def import_bads(self):
        """Import bad channels info from a CSV file.
        """
        fname = QFileDialog.getOpenFileName(self, "Import bad channels",
                                            filter="*.csv")[0]
        if fname:
            with open(fname) as f:
                bads = f.read().replace(" ", "").split(",")
                if set(bads) - set(data.current.raw.info["ch_names"]):
                    QMessageBox.critical(self, "Channel labels not found",
                                         "Some channel labels from the file "
                                         "are not present in the data.")
                else:
                    data.current.raw.info["bads"] = bads
                    data.data[data.index].raw.info["bads"] = bads

    def export_events(self):
        """Export events to a CSV file.

        The resulting CSV file has two columns. The first column contains the
        position (in samples), whereas the second column contains the type of
        the events. The first line is a header containing the column names.
        """
        fname = QFileDialog.getSaveFileName(self, "Export events",
                                            filter="*.csv")[0]
        if fname:
            name, ext = splitext(split(fname)[-1])
            ext = ext if ext else ".csv"  # automatically add extension
            fname = join(split(fname)[0], name + ext)
            np.savetxt(fname, data.current.events[:, [0, 2]], fmt="%d",
                       delimiter=",", header="pos,type", comments="")

    def export_annotations(self):
        """Export annotations to a CSV file.

        The resulting CSV file has three columns. The first column contains the
        annotation type, the second column contains the onset (in s), and the
        third column contains the duration (in s). The first line is a header
        containing the column names.
        """
        fname = QFileDialog.getSaveFileName(self, "Export annotations",
                                            filter="*.csv")[0]
        if fname:
            name, ext = splitext(split(fname)[-1])
            ext = ext if ext else ".csv"  # automatically add extension
            fname = join(split(fname)[0], name + ext)
            anns = data.current.raw.annotations
            with open(fname, "w") as f:
                f.write("type,onset,duration\n")
                for a in zip(anns.description, anns.onset, anns.duration):
                    f.write(",".join([a[0], str(a[1]), str(a[2])]))
                    f.write("\n")

    def import_annotations(self):
        fname = QFileDialog.getOpenFileName(self, "Import annotations",
                                            filter="*.csv")[0]
        if fname:
            descs, onsets, durations = [], [], []
            fs = data.current.raw.info["sfreq"]
            with open(fname) as f:
                f.readline()  # skip header
                for line in f:
                    ann = line.split(",")
                    onset = float(ann[1].strip())
                    duration = float(ann[2].strip())
                    if onset > data.current.raw.n_times / fs:
                        QMessageBox.critical(self, "Invalid annotations",
                                             "One or more annotations are "
                                             "outside of the data range.")
                        return
                    descs.append(ann[0].strip())
                    onsets.append(onset)
                    durations.append(duration)
            annotations = mne.Annotations(onsets, durations, descs)
            data.raw.annotations = annotations
            data.data[data.index].raw.annotations = annotations
            self._update_infowidget()

    def close_file(self):
        """Close current file.
        """
        data.remove_data()
        self._update_sidebar(data.names, data.index)
        self._update_infowidget()
        self._update_statusbar()

        if not data:
            self._toggle_actions(False)

    def close_all(self):
        """Close all currently open data sets.
        """
        msg = QMessageBox.question(self, "Close all data sets",
                                   "Close all data sets?")
        if msg == QMessageBox.Yes:
            while data:
                self.close_file()

    def get_info(self):
        """Get basic information on current file.

        Returns
        -------
        info : dict
            Dictionary with information on current file.
        """
        raw = data.current.raw
        fname = data.current.fname
        ftype = data.current.ftype
        reference = data.current.reference
        events = data.current.events
        montage = data.current.montage

        nchan = raw.info["nchan"]
        chans = Counter([channel_type(raw.info, i) for i in range(nchan)])

        if events is not None:
            nevents = events.shape[0]
            unique = [str(e) for e in sorted(set(events[:, 2]))]
            events = "{} ({})".format(nevents, ", ".join(unique))
        else:
            events = "-"

        if isinstance(reference, list):
            reference = ",".join(reference)

        if raw.annotations is not None:
            annots = len(raw.annotations.description)
        else:
            annots = "-"

        return {"File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Number of channels": nchan,
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans.items()]),
                "Samples": raw.n_times,
                "Sampling frequency": str(raw.info["sfreq"]) + " Hz",
                "Length": str(raw.n_times / raw.info["sfreq"]) + " s",
                "Events": events,
                "Annotations": annots,
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
                "Size in memory": "{:.2f} MB".format(
                    raw._data.nbytes / 1024 ** 2),
                "Size on disk": "-" if not fname else "{:.2f} MB".format(
                    getsize(fname) / 1024 ** 2)}

    def pick_channels(self):
        """Pick channels in current data set.
        """
        channels = data.current.raw.info["ch_names"]
        dialog = PickChannelsDialog(self, channels)
        if dialog.exec_():
            picks = [item.data(0) for item in dialog.channels.selectedItems()]
            drops = set(channels) - set(picks)
            tmp = data.current.raw.drop_channels(drops)
            name = data.current.name + " (channels dropped)"
            new = DataSet(raw=tmp, name=name, events=data.current.events)
            history.append("raw.drop({})".format(drops))
            self._update_datasets(new)

    def set_bads(self):
        """Set bad channels.
        """
        channels = data.current.raw.info["ch_names"]
        selected = data.current.raw.info["bads"]
        dialog = PickChannelsDialog(self, channels, selected, "Bad channels")
        if dialog.exec_():
            bads = [item.data(0) for item in dialog.channels.selectedItems()]
            data.current.raw.info["bads"] = bads
            data.data[data.index].raw.info["bads"] = bads
            self._toggle_actions(True)

    def set_montage(self):
        """Set montage.
        """
        path = join(mne.__path__[0], "channels", "data", "montages")
        supported = (".elc", ".txt", ".csd", ".sfp", ".elp", ".hpts", ".loc",
                     ".locs", ".eloc", ".bvef")
        files = [splitext(f) for f in listdir(path)]
        montages = sorted([f for f, ext in files if ext in supported],
                          key=str.lower)
        # TODO: currently it is not possible to remove an existing montage
        dialog = MontageDialog(self, montages,
                               selected=data.current.montage)
        if dialog.exec_():
            name = dialog.montages.selectedItems()[0].data(0)
            montage = mne.channels.read_montage(name)

            ch_names = data.current.raw.info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                data.current.montage = name
                data.data[data.index].montage = name
                data.current.raw.set_montage(montage)
                data.data[data.index].raw.set_montage(montage)
                self._update_infowidget()
                self._toggle_actions()
            else:
                QMessageBox.critical(self, "No matching channel names",
                                     "Channel names defined in the montage do "
                                     "not match any channel name in the data.")

    def plot_raw(self):
        """Plot raw data.
        """
        events = data.current.events
        nchan = data.current.raw.info["nchan"]
        fig = data.current.raw.plot(events=events, n_channels=nchan,
                                        title=data.current.name,
                                        show=False)
        history.append("raw.plot(n_channels={})".format(nchan))
        win = fig.canvas.manager.window
        win.setWindowTitle("Raw data")
        win.findChild(QStatusBar).hide()
        win.installEventFilter(self)  # detect if the figure is closed

        # prevent closing the window with the escape key
        try:
            key_events = fig.canvas.callbacks.callbacks["key_press_event"][8]
        except KeyError:
            pass
        else:  # this requires MNE >=0.15
            key_events.func.keywords["params"]["close_key"] = None

        fig.show()

    def plot_psd(self):
        """Plot power spectral density (PSD).
        """
        fig = data.current.raw.plot_psd(average=False,
                                            spatial_colors=False, show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Power spectral density")
        fig.show()

    def plot_montage(self):
        """Plot montage.
        """
        montage = mne.channels.read_montage(data.current.montage)
        fig = montage.plot(show_names=True, show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def load_ica(self):
        """Load ICA solution from a file.
        """
        fname = QFileDialog.getOpenFileName(self, "Load ICA",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def find_events(self):
        events = mne.find_events(data.current.raw, consecutive=False)
        if events.shape[0] > 0:  # if events were found
            data.current.events = events
            data.data[data.index].events = events
            self._update_infowidget()

    def filter_data(self):
        """Filter data.
        """
        dialog = FilterDialog(self)

        if dialog.exec_():
            low, high = dialog.low, dialog.high
            tmp = filter_data(data.current.raw._data,
                              data.current.raw.info["sfreq"],
                              l_freq=low, h_freq=high, fir_design="firwin")
            name = data.current.name + " ({}-{} Hz)".format(low, high)
            new = DataSet(raw=mne.io.RawArray(tmp, data.current.raw.info),
                          name=name, events=data.current.events)
            history.append("raw.filter({}, {})".format(low, high))
            self._update_datasets(new)

    def set_reference(self):
        """Set reference.
        """
        dialog = ReferenceDialog(self)
        if dialog.exec_():
            if dialog.average.isChecked():
                tmp, _ = mne.set_eeg_reference(data.current.raw, None)
                tmp.apply_proj()
                name = data.current.name + " (average ref)"
                new = DataSet(raw=tmp, name=name, reference="average",
                              events=data.current.events)
            else:
                ref = [c.strip() for c in dialog.channellist.text().split(",")]
                refstr = ",".join(ref)
                if set(ref) - set(data.current.raw.info["ch_names"]):
                    # add new reference channel(s) to data
                    try:
                        tmp = mne.add_reference_channels(data.current.raw,
                                                         ref)
                    except RuntimeError:
                        QMessageBox.critical(self, "Cannot add new channels",
                                             "Cannot add new channels to "
                                             "average referenced data.")
                        return
                else:
                    # re-reference to existing channel(s)
                    tmp, _ = mne.set_eeg_reference(data.current.raw, ref)
                name = data.current.name + " (ref {})".format(refstr)
                new = DataSet(raw=tmp, name=name, reference=refstr,
                              events=data.current.events)
            self._update_datasets(new)

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

    def _update_datasets(self, dataset):
        # if current data is stored in a file create a new data set
        if data.current.fname:
            data.insert_data(dataset)
        # otherwise ask if the current data set should be overwritten or if a
        # new data set should be created
        else:
            msg = QMessageBox.question(self, "Overwrite existing data set",
                                       "Overwrite existing data set?")
            if msg == QMessageBox.No:  # create new data set
                data.insert_data(dataset)
            else:  # overwrite existing data set
                data.update_data(dataset)
        self._update_sidebar(data.names, data.index)
        self._update_infowidget()
        self._update_statusbar()

    def _update_sidebar(self, names, index):
        """Update (overwrite) sidebar with names and current index.
        """
        self.names.setStringList(names)
        self.sidebar.setCurrentIndex(self.names.index(index))

    def _update_infowidget(self):
        if data:
            self.infowidget.set_values(self.get_info())
        else:
            self.infowidget.clear()

    def _update_statusbar(self):
        if data:
            mb = data.nbytes / 1024 ** 2
            self.status_label.setText("Total Memory: {:.2f} MB".format(mb))
        else:
            self.status_label.clear()

    def _toggle_actions(self, enabled=True):
        """Toggle actions.

        Parameters
        ----------
        enabled : bool
            Specifies whether actions are enabled (True) or disabled (False).
        """
        self.close_file_action.setEnabled(enabled)
        self.close_all_action.setEnabled(enabled)
        if data.data:
            bads = bool(data.current.raw.info["bads"])
            self.export_bad_action.setEnabled(enabled and bads)
            events = data.current.events is not None
            self.export_events_action.setEnabled(enabled and events)
            annot = data.current.raw.annotations is not None
            self.export_anno_action.setEnabled(enabled and annot)
            montage = bool(data.current.montage)
            self.plot_montage_action.setEnabled(enabled and montage)
        else:
            self.export_bad_action.setEnabled(enabled)
            self.export_events_action.setEnabled(enabled)
            self.export_anno_action.setEnabled(enabled)
            self.plot_montage_action.setEnabled(enabled)
        self.import_bad_action.setEnabled(enabled)
        self.import_anno_action.setEnabled(enabled)
        self.pick_chans_action.setEnabled(enabled)
        self.set_bads_action.setEnabled(enabled)
        self.set_montage_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.plot_psd_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.setref_action.setEnabled(enabled)
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
        while len(self.recent) > MAX_RECENT:  # prune list
            self.recent.pop()
        self._write_settings()
        if not self.recent_menu.isEnabled():
            self.recent_menu.setEnabled(True)

    def _remove_recent(self, fname):
        """Remove file from recent file list.

        Parameters
        ----------
        fname : str
            File name.
        """
        if fname in self.recent:
            self.recent.remove(fname)
            self._write_settings()
            if not self.recent:
                self.recent_menu.setEnabled(False)

    def _write_settings(self):
        """Write application settings.
        """
        settings = QSettings()
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
        if statusbar is None:  # default is True
            statusbar = True

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
        if selected.row() != data.index:
            data.index = selected.row()
            data.update_current()
            self._update_infowidget()

    @pyqtSlot(QModelIndex, QModelIndex)
    def _update_names(self, start, stop):
        """Update names in DataSets after changes in sidebar.
        """
        for index in range(start.row(), stop.row() + 1):
            data.data[index].name = self.names.stringList()[index]
        if data.index in range(start.row(), stop.row() + 1):
            data.current.name = data.names[data.index]

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

    @pyqtSlot(QDropEvent)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    @pyqtSlot(QDropEvent)
    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            for url in urls:
                self.load_file(url.toLocalFile())

    @pyqtSlot(QEvent)
    def closeEvent(self, event):
        """Close application.

        Parameters
        ----------
        event : QEvent
            Close event.
        """
        self._write_settings()
        if history:
            print("\nCommand History")
            print("===============")
            print("\n".join(history))
        QApplication.quit()

    def eventFilter(self, source, event):
        # currently the only source is the raw plot window
        if event.type() == QEvent.Close:
            self._update_infowidget()
            self._toggle_actions()
        return QObject.eventFilter(self, source, event)


matplotlib.use("Qt5Agg")
app = QApplication(sys.argv)
app.setApplicationName("MNELAB")
app.setOrganizationName("cbrnr")
main = MainWindow()
if len(sys.argv) > 1:  # open files from command line arguments
    for f in sys.argv[1:]:
        main.load_file(f)
sys.exit(app.exec_())
