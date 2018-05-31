from os.path import join, splitext
from os import listdir
import multiprocessing as mp

import mne
from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt, QObject)
from PyQt5.QtGui import QKeySequence, QDropEvent
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar, QToolBar)
from mne.filter import filter_data
from mne.io.pick import channel_type

from .dialogs.filterdialog import FilterDialog
from .dialogs.pickchannelsdialog import PickChannelsDialog
from .dialogs.referencedialog import ReferenceDialog
from .dialogs.montagedialog import MontageDialog
from .dialogs.channelpropertiesdialog import ChannelPropertiesDialog
from .dialogs.runicadialog import RunICADialog
from .dialogs.calcdialog import CalcDialog
from .widgets.infowidget import InfoWidget
from .model import (SUPPORTED_FORMATS, LabelsNotFoundError,
                    InvalidAnnotationsError)


__version__ = "0.1.0"

MAX_RECENT = 6  # maximum number of recent files


def read_settings():
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


def write_settings(**kwargs):
    """Write application settings."""
    settings = QSettings()
    for key, value in kwargs.items():
        settings.setValue(key, value)


class MainWindow(QMainWindow):
    """MNELAB main window."""
    def __init__(self, model):
        """Initialize MNELAB main window.

        Parameters
        ----------
        model : mnelab.model.Model instance
            The main window needs to connect to a model containing all data
            sets. This decouples the GUI from the data (model/view).
        """
        super().__init__()

        self.model = model  # data model
        self.setWindowTitle("MNELAB")

        # restore settings
        settings = read_settings()
        self.recent = settings["recent"]  # list of recent files
        if settings["geometry"]:
            self.restoreGeometry(settings["geometry"])
        else:
            self.setGeometry(300, 300, 1000, 750)  # default window size
            self.move(QApplication.desktop().screen().rect().center() -
                      self.rect().center())  # center window
        if settings["state"]:
            self.restoreState(settings["state"])

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.close_file_action = file_menu.addAction(
            "&Close",
            self.model.remove_data,
            QKeySequence.Close)
        self.close_all_action = file_menu.addAction(
            "Close all",
            self.close_all)
        file_menu.addSeparator()
        self.import_bad_action = file_menu.addAction(
            "Import bad channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels",
                                     "*.csv"))
        self.import_anno_action = file_menu.addAction(
            "Import annotations...",
            lambda: self.import_file(model.import_annotations,
                                     "Import annotations", "*.csv"))
        file_menu.addSeparator()
        self.export_raw_action = file_menu.addAction(
            "Export &raw...",
            lambda: self.export_file(model.export_raw, "Export raw", "*.fif"))
        self.export_bad_action = file_menu.addAction(
            "Export &bad channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels",
                                     "*.csv"))
        self.export_events_action = file_menu.addAction(
            "Export &events...",
            lambda: self.export_file(model.export_events, "Export events",
                                     "*.csv"))
        self.export_anno_action = file_menu.addAction(
            "Export &annotations...",
            lambda: self.export_file(model.export_annotations,
                                     "Export annotations", "*.csv"))
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, QKeySequence.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.pick_chans_action = edit_menu.addAction(
            "Pick &channels...",
            self.pick_channels)
        self.chan_props_action = edit_menu.addAction(
            "Channel &properties...",
            self.channel_properties)
        self.set_montage_action = edit_menu.addAction("Set &montage...",
                                                      self.set_montage)
        edit_menu.addSeparator()
        self.setref_action = edit_menu.addAction("&Set reference...",
                                                 self.set_reference)

        plot_menu = self.menuBar().addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)
        self.plot_psd_action = plot_menu.addAction("&Power spectral "
                                                   "density...", self.plot_psd)
        self.plot_montage_action = plot_menu.addAction("Current &montage",
                                                       self.plot_montage)

        tools_menu = self.menuBar().addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...",
                                                  self.filter_data)
        self.find_events_action = tools_menu.addAction("Find &events...",
                                                       self.model.find_events)
        self.run_ica_action = tools_menu.addAction("Run &ICA...", self.run_ica)
        self.import_ica_action = tools_menu.addAction("&Load ICA...",
                                                      self.load_ica)

        view_menu = self.menuBar().addMenu("&View")
        statusbar_action = view_menu.addAction("Statusbar",
                                               self._toggle_statusbar)
        statusbar_action.setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
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
        self.data_changed()

    def data_changed(self):
        # update sidebar
        self.names.setStringList(self.model.names)
        self.sidebar.setCurrentIndex(self.names.index(self.model.index))

        # update info widget
        if self.model.data:
            self.infowidget.set_values(self.model.get_info())
        else:
            self.infowidget.clear()

        # update status bar
        if self.model.data:
            mb = self.model.nbytes / 1024 ** 2
            self.status_label.setText("Total Memory: {:.2f} MB".format(mb))
        else:
            self.status_label.clear()

        # toggle actions
        if len(self.model) == 0:  # disable if no data sets are currently open
            enabled = False
        else:
            enabled = True
        self.close_file_action.setEnabled(enabled)
        self.close_all_action.setEnabled(enabled)
        self.export_raw_action.setEnabled(enabled)
        if self.model.data:
            current = self.model.data[self.model.index]
            bads = bool(current["raw"].info["bads"])
            self.export_bad_action.setEnabled(enabled and bads)
            events = current["events"] is not None
            self.export_events_action.setEnabled(enabled and events)
            annot = current["raw"].annotations is not None
            self.export_anno_action.setEnabled(enabled and annot)
            montage = bool(current["montage"])
            self.plot_montage_action.setEnabled(enabled and montage)
        else:
            self.export_bad_action.setEnabled(enabled)
            self.export_events_action.setEnabled(enabled)
            self.export_anno_action.setEnabled(enabled)
            self.plot_montage_action.setEnabled(enabled)
        self.import_bad_action.setEnabled(enabled)
        self.import_anno_action.setEnabled(enabled)
        self.pick_chans_action.setEnabled(enabled)
        self.chan_props_action.setEnabled(enabled)
        self.set_montage_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.plot_psd_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.setref_action.setEnabled(enabled)
        self.find_events_action.setEnabled(enabled)
        self.run_ica_action.setEnabled(enabled)
        self.import_ica_action.setEnabled(enabled)

        # add to recent files
        if len(self.model) > 0:
            self._add_recent(self.model.current["fname"])

    def open_file(self):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter=SUPPORTED_FORMATS)[0]
        if fname:
            self.model.load(fname)

    def export_file(self, f, text, ffilter):
        """Export to file."""
        fname = QFileDialog.getSaveFileName(self, text, filter=ffilter)[0]
        if fname:
            f(fname)

    def import_file(self, f, text, ffilter):
        """Import file."""
        fname = QFileDialog.getOpenFileName(self, text, filter=ffilter)[0]
        if fname:
            try:
                f(fname)
            except LabelsNotFoundError as e:
                QMessageBox.critical(self, "Channel labels not found", str(e))
            except InvalidAnnotationsError as e:
                QMessageBox.critical(self, "Invalid annotations", str(e))

    def close_all(self):
        """Close all currently open data sets."""
        msg = QMessageBox.question(self, "Close all data sets",
                                   "Close all data sets?")
        if msg == QMessageBox.Yes:
            while len(self.model) > 0:
                self.model.remove_data()

    def pick_channels(self):
        """Pick channels in current data set."""
        channels = self.model.current["raw"].info["ch_names"]
        dialog = PickChannelsDialog(self, channels, selected=channels)
        if dialog.exec_():
            picks = [item.data(0) for item in dialog.channels.selectedItems()]
            drops = set(channels) - set(picks)
            if drops:
                self.auto_duplicate()
                self.model.drop_channels(drops)
                self.model.history.append(f"raw.drop({drops})")

    def channel_properties(self):
        """Show channel properties dialog."""
        info = self.model.current["raw"].info
        dialog = ChannelPropertiesDialog(self, info)
        if dialog.exec_():
            dialog.model.sort(0)
            bads = []
            renamed = {}
            types = {}
            for i in range(dialog.model.rowCount()):
                new_label = dialog.model.item(i, 1).data(Qt.DisplayRole)
                old_label = info["ch_names"][i]
                if new_label != old_label:
                    renamed[old_label] = new_label
                new_type = dialog.model.item(i, 2).data(Qt.DisplayRole).lower()
                old_type = channel_type(info, i).lower()
                if new_type != old_type:
                    types[new_label] = new_type
                if dialog.model.item(i, 3).checkState() == Qt.Checked:
                    bads.append(info["ch_names"][i])
            self.model.set_channel_properties(bads, renamed, types)

    def set_montage(self):
        """Set montage."""
        montages = mne.channels.get_builtin_montages()
        # TODO: currently it is not possible to remove an existing montage
        dialog = MontageDialog(self, montages,
                               selected=self.model.current["montage"])
        if dialog.exec_():
            name = dialog.montages.selectedItems()[0].data(0)
            montage = mne.channels.read_montage(name)
            ch_names = self.model.current["raw"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                self.model.set_montage(name)
            else:
                QMessageBox.critical(self, "No matching channel names",
                                     "Channel names defined in the montage do "
                                     "not match any channel name in the data.")

    def plot_raw(self):
        fig = self.model.plot_raw()
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
        """Plot power spectral density (PSD)."""
        fig = self.model.current["raw"].plot_psd(average=False,
                                                 spatial_colors=False,
                                                 show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Power spectral density")
        fig.show()

    def plot_montage(self):
        """Plot montage."""
        montage = mne.channels.read_montage(self.model.current["montage"])
        fig = montage.plot(show_names=True, show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def load_ica(self):
        """Load ICA solution from a file."""
        fname = QFileDialog.getOpenFileName(self, "Load ICA",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def run_ica(self):
        """Run ICA calculation."""
        try:
            import picard
        except ImportError:
            have_picard = False
        else:
            have_picard = True

        dialog = RunICADialog(self, self.model.current["raw"].info["nchan"],
                              have_picard)

        if dialog.exec_():
            calc = CalcDialog(self, "Calculating ICA", "Calculating ICA.")
            method = dialog.method.currentText()
            exclude_bad_segments = dialog.exclude_bad_segments.isChecked()
            ica = mne.preprocessing.ICA(method=dialog.methods[method])
            pool = mp.Pool(1)
            kwds = {"reject_by_annotation": exclude_bad_segments}
            res = pool.apply_async(func=ica.fit,
                                   args=(self.model.current["raw"],),
                                   kwds=kwds, callback=lambda x: calc.accept())
            if not calc.exec_():
                pool.terminate()
            else:
                self.model.current["ica"] = res.get(timeout=1)
                self.data_changed()

    def filter_data(self):
        """Filter data."""
        dialog = FilterDialog(self)

        if dialog.exec_():
            low, high = dialog.low, dialog.high
            tmp = filter_data(self.model.current["raw"]._data,
                              self.model.current["raw"].info["sfreq"],
                              l_freq=low, h_freq=high, fir_design="firwin")
            name = self.model.current["name"] + " ({}-{} Hz)".format(low, high)
            new = DataSet(raw=mne.io.RawArray(tmp, data.current.raw.info),
                          name=name, events=data.current.events)
            self.model.history.append("raw.filter({}, {})".format(low, high))
            self._update_datasets(new)

    def set_reference(self):
        """Set reference."""
        dialog = ReferenceDialog(self)
        if dialog.exec_():
            if dialog.average.isChecked():
                tmp, _ = mne.set_eeg_reference(data.current.raw, None)
                tmp.apply_proj()
                name = data.current.name + " (average ref)"
                new = DataSet(raw=tmp, name=name, reference="Average",
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
        """Show About dialog."""
        msg = f"""<p style="font-weight: bold">MNELAB {__version__}</p>
        <p style="font-weight: normal">
        <a href="https://github.com/cbrnr/mnelab">MNELAB</a> - a graphical user
        interface for
        <a href="https://github.com/mne-tools/mne-python">MNE</a>.</p>
        <p style="font-weight: normal">
        This program uses MNE version {mne.__version__}.</p>
        <p style="font-weight: normal">
        Licensed under the BSD 3-clause license.</p>
        <p style="font-weight: normal">
        Copyright 2017-2018 by Clemens Brunner.</p>"""
        QMessageBox.about(self, "About MNELAB", msg)

    def show_about_qt(self):
        """Show About Qt dialog."""
        QMessageBox.aboutQt(self, "About Qt")

    def auto_duplicate(self):
        # if current data is stored in a file create a new data set
        if self.model.current["fname"]:
            self.model.duplicate_data()
        # otherwise ask the user
        else:
            msg = QMessageBox.question(self, "Overwrite existing data set",
                                       "Overwrite existing data set?")
            if msg == QMessageBox.No:  # create new data set
                self.model.duplicate_data()

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
        write_settings(recent=self.recent)
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
            write_settings(recent=self.recent)
            if not self.recent:
                self.recent_menu.setEnabled(False)

    @pyqtSlot(QModelIndex)
    def _update_data(self, selected):
        """Update index and information based on the state of the sidebar.

        Parameters
        ----------
        selected : QModelIndex
            Index of the selected row.
        """
        if selected.row() != self.model.index:
            self.model.index = selected.row()
            self.data_changed()

    @pyqtSlot(QModelIndex, QModelIndex)
    def _update_names(self, start, stop):
        """Update names in DataSets after changes in sidebar."""
        for index in range(start.row(), stop.row() + 1):
            self.model.data[index]["name"] = self.names.stringList()[index]

    @pyqtSlot()
    def _update_recent_menu(self):
        self.recent_menu.clear()
        for recent in self.recent:
            self.recent_menu.addAction(recent)

    @pyqtSlot(QAction)
    def _load_recent(self, action):
        self.model.load(action.text())

    @pyqtSlot()
    def _toggle_statusbar(self):
        if self.statusBar().isHidden():
            self.statusBar().show()
        else:
            self.statusBar().hide()
        write_settings(statusbar=not self.statusBar().isHidden())

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
        write_settings(geometry=self.saveGeometry(), state=self.saveState())
        if self.model.history:
            print("\nCommand History")
            print("===============")
            print("\n".join(self.model.history))
        QApplication.quit()

    def eventFilter(self, source, event):
        # currently the only source is the raw plot window
        if event.type() == QEvent.Close:
            self.data_changed()
        return QObject.eventFilter(self, source, event)
