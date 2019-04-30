import multiprocessing as mp
from sys import version_info
from os.path import split, splitext

import mne
from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt, QObject)
from PyQt5.QtGui import QKeySequence, QDropEvent
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar, QToolBar)
from mne.io.pick import channel_type

from .dialogs.filterdialog import FilterDialog
from .dialogs.findeventsdialog import FindEventsDialog
from .dialogs.pickchannelsdialog import PickChannelsDialog
from .dialogs.referencedialog import ReferenceDialog
from .dialogs.montagedialog import MontageDialog
from .dialogs.channelpropertiesdialog import ChannelPropertiesDialog
from .dialogs.runicadialog import RunICADialog
from .dialogs.calcdialog import CalcDialog
from .dialogs.eventsdialog import EventsDialog
from .dialogs.xdfstreamsdialog import XDFStreamsDialog
from .widgets.infowidget import InfoWidget
from .model import (SUPPORTED_FORMATS, SUPPORTED_EXPORT_FORMATS,
                    LabelsNotFoundError, InvalidAnnotationsError)
from .utils.xdf import parse_xdf, parse_chunks


__version__ = "0.1.0"

MAX_RECENT = 6  # maximum number of recent files


def read_settings():
    """Read application settings.

    Returns
    -------
    settings : dict
        The restored settings values are returned in a dictionary for further
        processing.
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

        self.actions = {}  # contains all actions

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        self.actions["open_file"] = file_menu.addAction(
            "&Open...", self.open_raw, QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.actions["close_file"] = file_menu.addAction(
            "&Close",
            self.model.remove_data,
            QKeySequence.Close)
        self.actions["close_all"] = file_menu.addAction(
            "Close all",
            self.close_all)
        file_menu.addSeparator()
        self.actions["import_bads"] = file_menu.addAction(
            "Import bad channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels",
                                     "*.csv"))
        self.actions["import_events"] = file_menu.addAction(
            "Import events...",
            lambda: self.import_file(model.import_events, "Import events",
                                     "*.csv"))
        self.actions["import_annotations"] = file_menu.addAction(
            "Import annotations...",
            lambda: self.import_file(model.import_annotations,
                                     "Import annotations", "*.csv"))
        self.actions["import_ica"] = file_menu.addAction(
            "Import &ICA...",
            lambda: self.open_file(model.import_ica, "Import ICA",
                                   "*.fif *.fif.gz"))
        file_menu.addSeparator()
        self.actions["export_raw"] = file_menu.addAction(
            "Export &raw...",
            lambda: self.export_file(model.export_raw, "Export raw",
                                     SUPPORTED_EXPORT_FORMATS))
        self.actions["export_bads"] = file_menu.addAction(
            "Export &bad channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels",
                                     "*.csv"))
        self.actions["export_events"] = file_menu.addAction(
            "Export &events...",
            lambda: self.export_file(model.export_events, "Export events",
                                     "*.csv"))
        self.actions["export_annotations"] = file_menu.addAction(
            "Export &annotations...",
            lambda: self.export_file(model.export_annotations,
                                     "Export annotations", "*.csv"))
        self.actions["export_ica"] = file_menu.addAction(
            "Export ICA...",
            lambda: self.export_file(model.export_ica,
                                     "Export ICA", "*.fif *.fif.gz"))
        file_menu.addSeparator()
        self.actions["quit"] = file_menu.addAction("&Quit", self.close,
                                                   QKeySequence.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.actions["pick_chans"] = edit_menu.addAction(
            "Pick &channels...",
            self.pick_channels)
        self.actions["chan_props"] = edit_menu.addAction(
            "Channel &properties...",
            self.channel_properties)
        self.actions["set_montage"] = edit_menu.addAction("Set &montage...",
                                                          self.set_montage)
        edit_menu.addSeparator()
        self.actions["set_ref"] = edit_menu.addAction("&Set reference...",
                                                      self.set_reference)
        edit_menu.addSeparator()
        self.actions["events"] = edit_menu.addAction("Events...",
                                                     self.edit_events)

        plot_menu = self.menuBar().addMenu("&Plot")
        self.actions["plot_raw"] = plot_menu.addAction("&Raw data",
                                                       self.plot_raw)
        self.actions["plot_psd"] = plot_menu.addAction(
            "&Power spectral density...", self.plot_psd)
        self.actions["plot_montage"] = plot_menu.addAction("Current &montage",
                                                           self.plot_montage)
        plot_menu.addSeparator()
        self.actions["plot_ica_components"] = plot_menu.addAction(
            "ICA components...", self.plot_ica_components)

        tools_menu = self.menuBar().addMenu("&Tools")
        self.actions["filter"] = tools_menu.addAction("&Filter data...",
                                                      self.filter_data)
        self.actions["find_events"] = tools_menu.addAction("Find &events...",
                                                           self.find_events)
        self.actions["run_ica"] = tools_menu.addAction("Run &ICA...",
                                                       self.run_ica)

        view_menu = self.menuBar().addMenu("&View")
        self.actions["statusbar"] = view_menu.addAction("Statusbar",
                                                        self._toggle_statusbar)
        self.actions["statusbar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.actions["about"] = help_menu.addAction("&About", self.show_about)
        self.actions["about_qt"] = help_menu.addAction("About &Qt",
                                                       self.show_about_qt)

        # actions that are always enabled
        self.always_enabled = ["open_file", "about", "about_qt", "quit",
                               "statusbar"]

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
            self.actions["statusbar"].setChecked(True)
        else:
            self.statusBar().hide()
            self.actions["statusbar"].setChecked(False)

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

        for name, action in self.actions.items():  # toggle
            if name not in self.always_enabled:
                action.setEnabled(enabled)

        if self.model.data:  # toggle if specific conditions are met
            bads = bool(self.model.current["raw"].info["bads"])
            self.actions["export_bads"].setEnabled(enabled and bads)
            events = self.model.current["events"] is not None
            self.actions["export_events"].setEnabled(enabled and events)
            annot = self.model.current["raw"].annotations is not None
            self.actions["export_annotations"].setEnabled(enabled and annot)
            montage = bool(self.model.current["montage"])
            self.actions["plot_montage"].setEnabled(enabled and montage)
            ica = bool(self.model.current["ica"])
            self.actions["export_ica"].setEnabled(enabled and ica)
            self.actions["plot_ica_components"].setEnabled(enabled and ica and
                                                           montage)
            self.actions["events"].setEnabled(enabled and events)

        # add to recent files
        if len(self.model) > 0:
            self._add_recent(self.model.current["fname"])

    def open_raw(self):
        """Open raw file."""
        fname = QFileDialog.getOpenFileName(self, "Open raw",
                                            filter=SUPPORTED_FORMATS)[0]
        if fname:
            name, ext = splitext(split(fname)[-1])
            ftype = ext[1:].upper()
            if ext.lower() not in SUPPORTED_FORMATS:
                raise ValueError(f"File format {ftype} is not supported.")

            if ext.lower() == ".xdf":
                streams = parse_chunks(parse_xdf(fname))
                rows, disabled = [], []
                for idx, s in enumerate(streams):
                    rows.append([s["stream_id"], s["name"], s["type"],
                                 s["channel_count"], s["channel_format"],
                                 s["nominal_srate"]])
                    if s["nominal_srate"] == 0:  # disable marker streams
                        disabled.append(idx)

                dialog = XDFStreamsDialog(self, rows, disabled=disabled)
                if dialog.exec_():
                    # TODO: load selected stream of XDF file
                    row = dialog.view.selectionModel().selectedRows()[0].row()
                    print(dialog.model.data(dialog.model.index(row, 0)),
                          dialog.model.data(dialog.model.index(row, 1)),
                          dialog.model.data(dialog.model.index(row, 2)),
                          dialog.model.data(dialog.model.index(row, 3)),
                          dialog.model.data(dialog.model.index(row, 4)),
                          dialog.model.data(dialog.model.index(row, 5)))
            else:  # all other file formats
                self.model.load(fname)

    def open_file(self, f, text, ffilter):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, text, filter=ffilter)[0]
        if fname:
            f(fname)

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

    def edit_events(self):
        pos = self.model.current["events"][:, 0].tolist()
        desc = self.model.current["events"][:, 2].tolist()
        dialog = EventsDialog(self, pos, desc)
        if dialog.exec_():
            pass

    def plot_raw(self):
        """Plot raw data."""
        events = self.model.current["events"]
        nchan = self.model.current["raw"].info["nchan"]
        fig = self.model.current["raw"].plot(events=events, n_channels=nchan,
                                             title=self.model.current["name"],
                                             show=False)
        self.model.history.append("raw.plot(n_channels={})".format(nchan))
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
        """Plot current montage."""
        fig = self.model.current["raw"].plot_sensors(show_names=True,
                                                     show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def plot_ica_components(self):
        self.model.current["ica"].plot_components()

    def run_ica(self):
        """Run ICA calculation."""
        try:
            import picard
        except ImportError:
            have_picard = False
        else:
            have_picard = True

        try:
            import sklearn  # required for FastICA
        except ImportError:
            have_sklearn = False
        else:
            have_sklearn = True

        dialog = RunICADialog(self, self.model.current["raw"].info["nchan"],
                              have_picard, have_sklearn)

        if dialog.exec_():
            calc = CalcDialog(self, "Calculating ICA", "Calculating ICA.")
            method = dialog.method.currentText()
            exclude_bad_segments = dialog.exclude_bad_segments.isChecked()
            fit_params = {}
            if not dialog.extended.isHidden():
                fit_params["extended"] = dialog.extended.isChecked()
            if not dialog.ortho.isHidden():
                fit_params["ortho"] = dialog.ortho.isChecked()
            ica = mne.preprocessing.ICA(method=dialog.methods[method],
                                        fit_params=fit_params)
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
            self.auto_duplicate()
            self.model.filter(dialog.low, dialog.high)

    def find_events(self):
        info = self.model.current["raw"].info

        # use first stim channel as default in dialog
        default_stim = 0
        for i in range(info["nchan"]):
            if mne.io.pick.channel_type(info, i) == "stim":
                default_stim = i
                break
        dialog = FindEventsDialog(self, info["ch_names"], default_stim)
        if dialog.exec_():
            stim_channel = dialog.stimchan.currentText()
            consecutive = dialog.consecutive.isChecked()
            initial_event = dialog.initial_event.isChecked()
            uint_cast = dialog.uint_cast.isChecked()
            min_dur = dialog.minduredit.value()
            shortest_event = dialog.shortesteventedit.value()
            self.model.find_events(stim_channel=stim_channel,
                                   consecutive=consecutive,
                                   initial_event=initial_event,
                                   uint_cast=uint_cast,
                                   min_duration=min_dur,
                                   shortest_event=shortest_event)

    def set_reference(self):
        """Set reference."""
        dialog = ReferenceDialog(self)
        if dialog.exec_():
            self.auto_duplicate()
            if dialog.average.isChecked():
                self.model.set_reference("average")
            else:
                ref = [c.strip() for c in dialog.channellist.text().split(",")]
                self.model.set_reference(ref)

    def show_about(self):
        """Show About dialog."""
        msg_box = QMessageBox(self)
        text = ("<h3>MNELAB</h3>"
                "<nobr><p>MNELAB is a graphical user interface for MNE.</p>"
                "</nobr>")
        msg_box.setText(text)

        mnelab_url = "github.com/cbrnr/mnelab"
        mne_url = "github.com/mne-tools/mne-python"

        text = (f'<nobr><p>This program uses MNE version {mne.__version__} '
                f'(Python {".".join(str(k) for k in version_info[:3])}).</p>'
                f'</nobr>'
                f'<nobr><p>MNELAB repository: '
                f'<a href=https://{mnelab_url}>{mnelab_url}</a></p></nobr>'
                f'<nobr><p>MNE repository: '
                f'<a href=https://{mne_url}>{mne_url}</a></p></nobr>'
                f'<p>Licensed under the BSD 3-clause license.</p>'
                f'<p>Copyright 2017-2019 by Clemens Brunner.</p>')
        msg_box.setInformativeText(text)
        msg_box.exec_()

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
                self.model.load(url.toLocalFile())

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
