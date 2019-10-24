# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import multiprocessing as mp
from sys import version_info
import traceback
from os.path import isfile, isdir
from functools import partial
import numpy as np

import mne
from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt, QObject)
from PyQt5.QtGui import QKeySequence, QDropEvent, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar, QToolBar)
from mne.io.pick import channel_type

from .dialogs import (AnnotationsDialog, CalcDialog, ChannelPropertiesDialog,
                      CropDialog, EpochDialog, ErrorMessageBox, EventsDialog,
                      FilterDialog, FindEventsDialog, HistoryDialog,
                      InterpolateBadsDialog, MontageDialog, PickChannelsDialog,
                      ReferenceDialog, RunICADialog, XDFStreamsDialog,
                      MetaInfoDialog)
from .widgets.infowidget import InfoWidget
from .model import (LabelsNotFoundError, InvalidAnnotationsError,
                    UnknownFileTypeError)
from .utils import (IMPORT_FORMATS, EXPORT_FORMATS, have, split_fname,
                    parse_xdf, parse_chunks, get_xml)
# all icons are stored in mnelab/resources.py, which must be automatically
# generated with "pyrcc5 -o mnelab/resources.py mnelab.qrc"
import mnelab.resources  # noqa


__version__ = "0.5.1"

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

    toolbar = settings.value("toolbar")
    if toolbar is None:  # default is True
        toolbar = True

    statusbar = settings.value("statusbar")
    if statusbar is None:  # default is True
        statusbar = True

    geometry = settings.value("geometry")
    state = settings.value("state")

    return {"recent": recent, "statusbar": statusbar, "geometry": geometry,
            "state": state, "toolbar": toolbar}


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
        icon = QIcon(":/open_file.svg")
        self.actions["open_file"] = file_menu.addAction(
            icon, "&Open...", self.open_data, QKeySequence.Open)
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
        icon = QIcon(":/meta_info.svg")
        self.actions["meta_info"] = file_menu.addAction(icon,
                                                        "Show information...",
                                                        self.meta_info)
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
        self.export_menu = file_menu.addMenu("Export data")
        for name, ext in EXPORT_FORMATS.items():
            self.actions["export_data_" + ext] = self.export_menu.addAction(
                f"{name} ({ext[1:].upper()})...",
                partial(self.export_file, model.export_data, "Export data",
                        ext))
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
        icon = QIcon(":/chan_props.svg")
        self.actions["chan_props"] = edit_menu.addAction(
            icon, "Channel &properties...", self.channel_properties)
        self.actions["set_montage"] = edit_menu.addAction("Set &montage...",
                                                          self.set_montage)
        edit_menu.addSeparator()
        self.actions["set_ref"] = edit_menu.addAction("&Set reference...",
                                                      self.set_reference)
        edit_menu.addSeparator()
        self.actions["annotations"] = edit_menu.addAction(
            "Annotations...",
            self.edit_annotations)
        self.actions["events"] = edit_menu.addAction("Events...",
                                                     self.edit_events)

        edit_menu.addSeparator()
        self.actions["crop"] = edit_menu.addAction("&Crop data...", self.crop)

        plot_menu = self.menuBar().addMenu("&Plot")
        icon = QIcon(":/plot_data.svg")
        self.actions["plot_data"] = plot_menu.addAction(icon, "&Data...",
                                                        self.plot_data)
        icon = QIcon(":/plot_psd.svg")
        self.actions["plot_psd"] = plot_menu.addAction(
            icon, "&Power spectral density...", self.plot_psd)
        icon = QIcon(":/plot_montage.svg")
        self.actions["plot_montage"] = plot_menu.addAction(icon, "&Montage...",
                                                           self.plot_montage)
        plot_menu.addSeparator()
        self.actions["plot_ica_components"] = plot_menu.addAction(
            "ICA &components...", self.plot_ica_components)
        self.actions["plot_ica_sources"] = plot_menu.addAction(
            "ICA &sources...", self.plot_ica_sources)

        tools_menu = self.menuBar().addMenu("&Tools")
        icon = QIcon(":/filter.svg")
        self.actions["filter"] = tools_menu.addAction(icon, "&Filter data...",
                                                      self.filter_data)
        icon = QIcon(":/find_events.svg")
        self.actions["find_events"] = tools_menu.addAction(icon,
                                                           "Find &events...",
                                                           self.find_events)
        self.actions["events_from_annotations"] = tools_menu.addAction(
            "Create events from annotations", self.events_from_annotations
        )
        tools_menu.addSeparator()
        icon = QIcon(":/run_ica.svg")
        self.actions["run_ica"] = tools_menu.addAction(icon, "Run &ICA...",
                                                       self.run_ica)
        self.actions["apply_ica"] = tools_menu.addAction("Apply &ICA",
                                                         self.apply_ica)
        tools_menu.addSeparator()
        self.actions["interpolate_bads"] = tools_menu.addAction(
                                                "Interpolate bad channels...",
                                                self.interpolate_bads)
        tools_menu.addSeparator()
        icon = QIcon(":/epoch_data.svg")
        self.actions["epoch_data"] = tools_menu.addAction(
            icon, "Create Epochs...", self.epoch_data)

        view_menu = self.menuBar().addMenu("&View")
        self.actions["history"] = view_menu.addAction("&History...",
                                                      self.show_history)
        self.actions["toolbar"] = view_menu.addAction("&Toolbar",
                                                      self._toggle_toolbar)
        self.actions["toolbar"].setCheckable(True)
        self.actions["statusbar"] = view_menu.addAction("&Statusbar",
                                                        self._toggle_statusbar)
        self.actions["statusbar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.actions["about"] = help_menu.addAction("&About", self.show_about)
        self.actions["about_qt"] = help_menu.addAction("About &Qt",
                                                       self.show_about_qt)

        # actions that are always enabled
        self.always_enabled = ["open_file", "about", "about_qt", "quit",
                               "toolbar", "statusbar"]

        # set up toolbar
        self.toolbar = self.addToolBar("toolbar")
        self.toolbar.setObjectName("toolbar")
        self.toolbar.addAction(self.actions["open_file"])
        self.toolbar.addAction(self.actions["meta_info"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions["chan_props"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions["plot_data"])
        self.toolbar.addAction(self.actions["plot_psd"])
        self.toolbar.addAction(self.actions["plot_montage"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions["filter"])
        self.toolbar.addAction(self.actions["find_events"])
        self.toolbar.addAction(self.actions["epoch_data"])
        self.toolbar.addAction(self.actions["run_ica"])

        self.setUnifiedTitleAndToolBarOnMac(True)
        if settings["toolbar"]:
            self.toolbar.show()
            self.actions["toolbar"].setChecked(True)
        else:
            self.toolbar.hide()
            self.actions["toolbar"].setChecked(False)

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
            bads = bool(self.model.current["data"].info["bads"])
            self.actions["export_bads"].setEnabled(enabled and bads)
            events = self.model.current["events"] is not None
            self.actions["export_events"].setEnabled(enabled and events)
            if self.model.current["dtype"] == "raw":
                annot = bool(self.model.current["data"].annotations)
            else:
                annot = False
            self.actions["export_annotations"].setEnabled(enabled and annot)
            self.actions["annotations"].setEnabled(enabled and annot)
            montage = bool(self.model.current["montage"])
            self.actions["plot_montage"].setEnabled(enabled and montage)
            ica = bool(self.model.current["ica"])
            self.actions["apply_ica"].setEnabled(enabled and ica)
            self.actions["export_ica"].setEnabled(enabled and ica)
            self.actions["plot_ica_components"].setEnabled(enabled and ica and
                                                           montage)
            self.actions["plot_ica_sources"].setEnabled(enabled and ica)
            self.actions["interpolate_bads"].setEnabled(enabled and montage and
                                                        bads)
            self.actions["events"].setEnabled(enabled and events)
            self.actions["events_from_annotations"].setEnabled(enabled and
                                                               annot)
            self.actions["find_events"].setEnabled(
                enabled and self.model.current["dtype"] == "raw")
            self.actions["epoch_data"].setEnabled(
                enabled and events and self.model.current["dtype"] == "raw")
            self.actions["crop"].setEnabled(
                enabled and self.model.current["dtype"] == "raw")
            self.actions["meta_info"].setEnabled(
                enabled and
                self.model.current["ftype"] == "Extensible Data Format")
        # add to recent files
        if len(self.model) > 0:
            self._add_recent(self.model.current["fname"])

    def open_data(self, fname=None):
        """Open raw file."""
        if fname is None:
            fname = QFileDialog.getOpenFileName(self, "Open raw",
                                                filter="*")[0]
        if fname:
            if not (isfile(fname) or isdir(fname)):
                self._remove_recent(fname)
                QMessageBox.critical(self, "File does not exist",
                                     f"File {fname} does not exist anymore.")
                return

            name, ext, ftype = split_fname(fname, IMPORT_FORMATS)

            if ext in [".xdf", ".xdfz", ".xdf.gz"]:
                streams = parse_chunks(parse_xdf(fname))
                rows, disabled = [], []
                for idx, s in enumerate(streams):
                    rows.append([s["stream_id"], s["name"], s["type"],
                                 s["channel_count"], s["channel_format"],
                                 s["nominal_srate"]])
                    is_marker = (s["nominal_srate"] == 0 or
                                 s["channel_format"] == "string")
                    if is_marker:  # disable marker streams
                        disabled.append(idx)

                enabled = list(set(range(len(rows))) - set(disabled))
                if enabled:
                    selected = enabled[0]
                else:
                    selected = None
                dialog = XDFStreamsDialog(self, rows, selected=selected,
                                          disabled=disabled)
                if dialog.exec_():
                    row = dialog.view.selectionModel().selectedRows()[0].row()
                    stream_id = dialog.model.data(dialog.model.index(row, 0))
                    self.model.load(fname, stream_id=stream_id)
            else:  # all other file formats
                try:
                    self.model.load(fname)
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))
                except UnknownFileTypeError as e:
                    QMessageBox.critical(self, "Unknown file type", str(e))

    def open_file(self, f, text, ffilter):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, text, filter="*")[0]
        if fname:
            f(fname)

    def export_file(self, f, text, ffilter):
        """Export to file."""
        fname = QFileDialog.getSaveFileName(self, text, filter="*")[0]
        if fname:
            f(fname, ffilter)

    def import_file(self, f, text, ffilter):
        """Import file."""
        fname = QFileDialog.getOpenFileName(self, text, filter="*")[0]
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

    def meta_info(self):
        xml = get_xml(self.model.current["fname"])
        dialog = MetaInfoDialog(self, xml)
        dialog.exec_()

    def pick_channels(self):
        """Pick channels in current data set."""
        channels = self.model.current["data"].info["ch_names"]
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
        info = self.model.current["data"].info
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
            ch_names = self.model.current["data"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                self.model.set_montage(name)
            else:
                QMessageBox.critical(self, "No matching channel names",
                                     "Channel names defined in the montage do "
                                     "not match any channel name in the data.")

    def edit_annotations(self):
        fs = self.model.current["data"].info["sfreq"]
        pos = self.model.current["data"].annotations.onset
        pos = (pos * fs).astype(int).tolist()
        dur = self.model.current["data"].annotations.duration
        dur = (dur * fs).astype(int).tolist()
        desc = self.model.current["data"].annotations.description.tolist()
        dialog = AnnotationsDialog(self, pos, dur, desc)
        if dialog.exec_():
            rows = dialog.table.rowCount()
            onset, duration, description = [], [], []
            for i in range(rows):
                data = dialog.table.item(i, 0).data(Qt.DisplayRole)
                onset.append(float(data) / fs)
                data = dialog.table.item(i, 1).data(Qt.DisplayRole)
                duration.append(float(data) / fs)
                data = dialog.table.item(i, 2).data(Qt.DisplayRole)
                description.append(data)
            self.model.set_annotations(onset, duration, description)

    def edit_events(self):
        pos = self.model.current["events"][:, 0].tolist()
        desc = self.model.current["events"][:, 2].tolist()
        dialog = EventsDialog(self, pos, desc)
        if dialog.exec_():
            rows = dialog.table.rowCount()
            events = np.zeros((rows, 3), dtype=int)
            for i in range(rows):
                pos = int(dialog.table.item(i, 0).data(Qt.DisplayRole))
                desc = int(dialog.table.item(i, 1).data(Qt.DisplayRole))
                events[i] = pos, 0, desc
            self.model.set_events(events)

    def crop(self):
        """Filter data."""
        fs = self.model.current["data"].info["sfreq"]
        length = self.model.current["data"].n_times / fs
        dialog = CropDialog(self, 0, length)
        if dialog.exec_():
            self.auto_duplicate()
            if dialog.start is None:
                dialog.start = 0
            self.model.crop(dialog.start, dialog.stop)

    def plot_data(self):
        """Plot data."""
        # self.bad is needed to update history if bad channels are selected in
        # the interactive plot window (see also self.eventFilter)
        self.bads = self.model.current["data"].info["bads"]
        events = self.model.current["events"]
        nchan = self.model.current["data"].info["nchan"]
        fig = self.model.current["data"].plot(events=events, n_channels=nchan,
                                              title=self.model.current["name"],
                                              scalings="auto", show=False)
        self.model.history.append("data.plot(n_channels={})".format(nchan))
        win = fig.canvas.manager.window
        win.setWindowTitle(self.model.current["name"])
        win.findChild(QStatusBar).hide()
        win.installEventFilter(self)  # detect if the figure is closed

        # prevent closing the window with the escape key
        try:
            fig._mne_params["close_key"] = None
        except AttributeError:  # does not exist in older MNE versions
            pass

        fig.show()

    def plot_psd(self):
        """Plot power spectral density (PSD)."""
        kwds = {"show": False}
        if self.model.current["type"] == "raw":
            kwds.update({"average": False, "spatial_colors": False})
        fig = self.model.current["data"].plot_psd(**kwds)
        win = fig.canvas.manager.window
        win.setWindowTitle("Power spectral density")
        fig.show()

    def plot_montage(self):
        """Plot current montage."""
        fig = self.model.current["data"].plot_sensors(show_names=True,
                                                      show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def plot_ica_components(self):
        self.model.current["ica"].plot_components(
            inst=self.model.current["data"])

    def plot_ica_sources(self):
        self.model.current["ica"].plot_sources(inst=self.model.current["data"])

    def run_ica(self):
        """Run ICA calculation."""
        dialog = RunICADialog(self, self.model.current["data"].info["nchan"],
                              have["picard"], have["sklearn"])

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
            self.model.history.append(f"ica = mne.preprocessing.ICA("
                                      f"method={dialog.methods[method]}, "
                                      f"fit_params={fit_params})")
            pool = mp.Pool(1)
            kwds = {"reject_by_annotation": exclude_bad_segments}
            res = pool.apply_async(func=ica.fit,
                                   args=(self.model.current["data"],),
                                   kwds=kwds, callback=lambda x: calc.accept())
            if not calc.exec_():
                pool.terminate()
            else:
                self.model.current["ica"] = res.get(timeout=1)
                self.model.history.append(f"ica.fit(inst=raw, "
                                          f"reject_by_annotation="
                                          f"{exclude_bad_segments})")
                self.data_changed()

    def apply_ica(self):
        """Apply current fitted ICA."""
        self.auto_duplicate()
        self.model.apply_ica()

    def interpolate_bads(self):
        """Interpolate bad channels"""
        dialog = InterpolateBadsDialog(self)
        if dialog.exec_():
            duplicated = self.auto_duplicate()
            try:
                self.model.interpolate_bads(dialog.reset_bads, dialog.mode,
                                            dialog.origin)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(self,
                                         "Could not interpolate bad channels",
                                         str(e), traceback.format_exc())
                msgbox.show()

    def filter_data(self):
        """Filter data."""
        dialog = FilterDialog(self)
        if dialog.exec_():
            self.auto_duplicate()
            self.model.filter(dialog.low, dialog.high)

    def find_events(self):
        info = self.model.current["data"].info

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

    def events_from_annotations(self):
        self.model.events_from_annotations()

    def epoch_data(self):
        """Epoch raw data."""
        dialog = EpochDialog(self, self.model.current["events"])
        if dialog.exec_():
            events = [int(item.text()) for item
                      in dialog.events.selectedItems()]
            tmin = dialog.tmin.value()
            tmax = dialog.tmax.value()

            if dialog.baseline.isChecked():
                baseline = dialog.a.value(), dialog.b.value()
            else:
                baseline = None

            duplicated = self.auto_duplicate()
            try:
                self.model.epoch_data(events, tmin, tmax, baseline)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(self, "Could not create epochs",
                                         str(e), traceback.format_exc())
                msgbox.show()

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

    def show_history(self):
        """Show history."""
        dialog = HistoryDialog(self, "\n".join(self.model.history))
        dialog.exec_()

    def show_about(self):
        """Show About dialog."""
        msg_box = QMessageBox(self)
        text = (f"<img src=':/mnelab_logo.png'>"
                f"<p>MNELAB {__version__}</p>")
        msg_box.setText(text)

        mnelab_url = "github.com/cbrnr/mnelab"
        mne_url = "github.com/mne-tools/mne-python"

        pkgs = []
        for key, value in have.items():
            if value:
                pkgs.append(f"{key}&nbsp;({value})")
            else:
                pkgs.append(f"{key}&nbsp;(not installed)")

        text = (f'<nobr><p>This program uses Python '
                f'{".".join(str(k) for k in version_info[:3])} and the '
                f'following packages:</p></nobr>'
                f'<p>{", ".join(pkgs)}</p>'
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
        """Automatically duplicate current data set.

        If the current data set is stored in a file (i.e. was loaded directly
        from a file), a new data set is automatically created. If the current
        data set is not stored in a file (i.e. was created by operations in
        MNELAB), a dialog box asks the user if the current data set should be
        overwritten or duplicated.

        Returns
        -------
        duplicated : bool
            True if the current data set was automatically duplicated, False if
            the current data set was overwritten.
        """
        # if current data is stored in a file create a new data set
        if self.model.current["fname"]:
            self.model.duplicate_data()
            return True
        # otherwise ask the user
        else:
            msg = QMessageBox.question(self, "Overwrite existing data set",
                                       "Overwrite existing data set?")
            if msg == QMessageBox.No:  # create new data set
                self.model.duplicate_data()
                return True
        return False

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
        self.open_data(fname=action.text())

    @pyqtSlot()
    def _toggle_toolbar(self):
        if self.toolbar.isHidden():
            self.toolbar.show()
        else:
            self.toolbar.hide()
        write_settings(toolbar=not self.toolbar.isHidden())

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
                try:
                    self.open_data(url.toLocalFile())
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))

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
            bads = self.model.current["data"].info["bads"]
            if self.bads != bads:
                self.model.history.append(f"data.info['bads'] = {bads}")
        return QObject.eventFilter(self, source, event)
