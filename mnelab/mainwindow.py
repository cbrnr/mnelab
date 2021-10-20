# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import multiprocessing as mp
from sys import version_info
import traceback
from functools import partial
from pathlib import Path

import numpy as np
import mne
from mne.io.pick import channel_type
from qtpy.QtCore import (Qt, Slot, QStringListModel, QModelIndex, QSettings, QEvent, QSize,
                         QPoint, QObject, QMetaObject)
from qtpy.QtGui import QKeySequence, QDropEvent, QIcon
from qtpy.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter, QMessageBox,
                            QListView, QAction, QLabel, QFrame)

from .dialogs import (AnnotationsDialog, AppendDialog, CalcDialog, ChannelPropertiesDialog,
                      CropDialog, ERDSDialog, EpochDialog, ErrorMessageBox, EventsDialog,
                      FilterDialog, FindEventsDialog, HistoryDialog, InterpolateBadsDialog,
                      MetaInfoDialog, MontageDialog, PickChannelsDialog, ReferenceDialog,
                      RunICADialog, XDFStreamsDialog)
from .widgets import InfoWidget
from .model import LabelsNotFoundError, InvalidAnnotationsError
from .utils import have, has_locations, image_path, interface_style
from .io import writers
from .io.xdf import get_xml, get_streams
from .viz import plot_erds


MAX_RECENT = 6  # maximum number of recent files


def read_settings():
    """Read application settings.

    Returns
    -------
    settings : dict
        Settings values.
    """
    settings = {}
    settings["recent"] = QSettings().value("recent", [])
    settings["toolbar"] = QSettings().value("toolbar", True)
    settings["statusbar"] = QSettings().value("statusbar", True)
    settings["size"] = QSettings().value("size", QSize(700, 500))
    settings["pos"] = QSettings().value("pos", QPoint(100, 100))
    return settings


def write_settings(**kwargs):
    """Write application settings."""
    for key, value in kwargs.items():
        QSettings().setValue(key, value)


class MainWindow(QMainWindow):
    """MNELAB main window."""
    def __init__(self, model):
        """Initialize MNELAB main window.

        Parameters
        ----------
        model : mnelab.model.Model instance
            The main window needs to connect to a model containing all data sets. This
            decouples the GUI from the data (model/view).
        """
        super().__init__()
        self.model = model  # data model
        self.setWindowTitle("MNELAB")

        # restore settings
        settings = read_settings()
        self.recent = settings["recent"]  # list of recent files
        self.resize(settings["size"])
        self.move(settings["pos"])

        # remove None entries from self.recent
        self.recent = [recent for recent in self.recent if recent is not None]

        # trigger theme setting
        QIcon.setThemeSearchPaths([str(Path(__file__).parent / "icons")])
        self.event(QEvent(QEvent.PaletteChange))

        self.actions = {}  # contains all actions

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        icon = QIcon.fromTheme("open-file")
        self.actions["open_file"] = file_menu.addAction(icon, "&Open...", self.open_data,
                                                        QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.actions["close_file"] = file_menu.addAction("&Close", self.model.remove_data,
                                                         QKeySequence.Close)
        self.actions["close_all"] = file_menu.addAction("Close all", self.close_all)
        file_menu.addSeparator()
        icon = QIcon.fromTheme("meta-info")
        self.actions["meta_info"] = file_menu.addAction(icon, "Show information...",
                                                        self.meta_info)
        file_menu.addSeparator()
        self.actions["import_bads"] = file_menu.addAction(
            "Import bad channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels", "*.csv")
        )
        self.actions["import_events"] = file_menu.addAction(
            "Import events...",
            lambda: self.import_file(model.import_events, "Import events", "*.csv")
        )
        self.actions["import_annotations"] = file_menu.addAction(
            "Import annotations...",
            lambda: self.import_file(model.import_annotations, "Import annotations",
                                     "*.csv")
        )
        self.actions["import_ica"] = file_menu.addAction(
            "Import &ICA...",
            lambda: self.open_file(model.import_ica, "Import ICA", "*.fif *.fif.gz")
        )
        file_menu.addSeparator()
        self.export_menu = file_menu.addMenu("Export data")
        for ext, description in writers.items():
            action = "export_data" + ext.replace(".", "_")
            self.actions[action] = self.export_menu.addAction(
                f"{ext[1:].upper()} ({description[1]})...",
                partial(self.export_file, model.export_data, "Export data", "*" + ext)
            )
        self.actions["export_bads"] = file_menu.addAction(
            "Export &bad channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels", "*.csv")
        )
        self.actions["export_events"] = file_menu.addAction(
            "Export &events...",
            lambda: self.export_file(model.export_events, "Export events", "*.csv")
        )
        self.actions["export_annotations"] = file_menu.addAction(
            "Export &annotations...",
            lambda: self.export_file(model.export_annotations, "Export annotations",
                                     "*.csv")
        )
        self.actions["export_ica"] = file_menu.addAction(
            "Export ICA...",
            lambda: self.export_file(model.export_ica, "Export ICA", "*.fif *.fif.gz")
        )
        file_menu.addSeparator()
        self.actions["quit"] = file_menu.addAction("&Quit", self.close, QKeySequence.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.actions["pick_chans"] = edit_menu.addAction("P&ick channels...",
                                                         self.pick_channels)
        icon = QIcon.fromTheme("chan-props")
        self.actions["chan_props"] = edit_menu.addAction(icon, "Channel &properties...",
                                                         self.channel_properties)
        self.actions["set_montage"] = edit_menu.addAction("Set &montage...",
                                                          self.set_montage)
        edit_menu.addSeparator()
        self.actions["set_ref"] = edit_menu.addAction("Set &reference...",
                                                      self.set_reference)
        edit_menu.addSeparator()
        self.actions["annotations"] = edit_menu.addAction("&Annotations...",
                                                          self.edit_annotations)
        self.actions["events"] = edit_menu.addAction("&Events...", self.edit_events)

        edit_menu.addSeparator()
        self.actions["crop"] = edit_menu.addAction("&Crop data...", self.crop)
        self.actions["append_data"] = edit_menu.addAction("Appen&d data...",
                                                          self.append_data)

        plot_menu = self.menuBar().addMenu("&Plot")
        icon = QIcon.fromTheme("plot-data")
        self.actions["plot_data"] = plot_menu.addAction(icon, "&Data", self.plot_data)
        icon = QIcon.fromTheme("plot-psd")
        self.actions["plot_psd"] = plot_menu.addAction(icon, "&Power spectral density",
                                                       self.plot_psd)
        icon = QIcon.fromTheme("plot-locations")
        self.actions["plot_locations"] = plot_menu.addAction(icon, "&Channel locations",
                                                             self.plot_locations)
        self.actions["plot_erds"] = plot_menu.addAction("&ERDS maps...", self.plot_erds)
        plot_menu.addSeparator()
        self.actions["plot_ica_components"] = plot_menu.addAction("ICA &components...",
                                                                  self.plot_ica_components)
        self.actions["plot_ica_sources"] = plot_menu.addAction("ICA &sources...",
                                                               self.plot_ica_sources)

        tools_menu = self.menuBar().addMenu("&Tools")
        icon = QIcon.fromTheme("filter-data")
        self.actions["filter"] = tools_menu.addAction(icon, "&Filter data...",
                                                      self.filter_data)
        icon = QIcon.fromTheme("find-events")
        self.actions["find_events"] = tools_menu.addAction(icon, "Find &events...",
                                                           self.find_events)
        self.actions["events_from_annotations"] = tools_menu.addAction(
            "Create events from annotations", self.events_from_annotations
        )
        self.actions["annotations_from_events"] = tools_menu.addAction(
            "Create annotations from events", self.annotations_from_events
        )
        tools_menu.addSeparator()
        nirs_menu = tools_menu.addMenu("NIRS")
        self.actions["convert_od"] = nirs_menu.addAction("Convert to &optical density",
                                                         self.convert_od)
        self.actions["convert_bl"] = nirs_menu.addAction("Convert to &haemoglobin",
                                                         self.convert_bl)

        tools_menu.addSeparator()
        icon = QIcon.fromTheme("run-ica")
        self.actions["run_ica"] = tools_menu.addAction(icon, "Run &ICA...", self.run_ica)
        self.actions["apply_ica"] = tools_menu.addAction("Apply &ICA", self.apply_ica)
        tools_menu.addSeparator()
        self.actions["interpolate_bads"] = tools_menu.addAction(
            "Interpolate bad channels...", self.interpolate_bads
        )
        tools_menu.addSeparator()
        icon = QIcon.fromTheme("epoch-data")
        self.actions["epoch_data"] = tools_menu.addAction(icon, "Create epochs...",
                                                          self.epoch_data)

        view_menu = self.menuBar().addMenu("&View")
        self.actions["history"] = view_menu.addAction("&History...", self.show_history)
        self.actions["toolbar"] = view_menu.addAction("&Toolbar", self._toggle_toolbar)
        self.actions["toolbar"].setCheckable(True)
        self.actions["statusbar"] = view_menu.addAction("&Statusbar",
                                                        self._toggle_statusbar)
        self.actions["statusbar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.actions["about"] = help_menu.addAction("&About", self.show_about)
        self.actions["about_qt"] = help_menu.addAction("About &Qt", self.show_about_qt)

        # actions that are always enabled
        self.always_enabled = ["open_file", "about", "about_qt", "quit", "toolbar",
                               "statusbar"]

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
        self.toolbar.addAction(self.actions["plot_locations"])
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
        splitter.setSizes((int(width * 0.3), int(width * 0.7)))
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
            self.status_label.setText(f"Total Memory: {mb:.2f} MB")
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
            locations = has_locations(self.model.current["data"].info)
            self.actions["plot_locations"].setEnabled(enabled and locations)
            ica = bool(self.model.current["ica"])
            self.actions["apply_ica"].setEnabled(enabled and ica)
            self.actions["export_ica"].setEnabled(enabled and ica)
            self.actions["plot_erds"].setEnabled(
                enabled and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_ica_components"].setEnabled(enabled and ica and locations)
            self.actions["plot_ica_sources"].setEnabled(enabled and ica)
            self.actions["interpolate_bads"].setEnabled(enabled and locations and bads)
            self.actions["events"].setEnabled(enabled and events)
            self.actions["events_from_annotations"].setEnabled(enabled and annot)
            self.actions["annotations_from_events"].setEnabled(enabled and events)
            self.actions["find_events"].setEnabled(
                enabled and self.model.current["dtype"] == "raw"
            )
            self.actions["epoch_data"].setEnabled(
                enabled and events and self.model.current["dtype"] == "raw"
            )
            self.actions["crop"].setEnabled(
                enabled and self.model.current["dtype"] == "raw"
            )
            append = bool(self.model.get_compatibles())
            self.actions["append_data"].setEnabled(
                enabled and append and (self.model.current["dtype"] in ("raw", "epochs"))
            )
            self.actions["meta_info"].setEnabled(
                enabled and self.model.current["ftype"] in ["XDF", "XDFZ", "XDF.GZ"]
            )
            self.actions["convert_od"].setEnabled(
                len(
                    mne.pick_types(
                        self.model.current["data"].info, fnirs="fnirs_cw_amplitude"
                    )
                )
            )
            self.actions["convert_bl"].setEnabled(
                len(mne.pick_types(self.model.current["data"].info, fnirs="fnirs_od"))
            )
            # disable unsupported exporters for epochs (all must support raw)
            if self.model.current["dtype"] == "epochs":
                for ext, description in writers.items():
                    action = "export_data" + ext.replace(".", "_")
                    if "epoch" in description[2]:
                        self.actions[action].setEnabled(True)
                    else:
                        self.actions[action].setEnabled(False)
        # add to recent files
        if len(self.model) > 0:
            self._add_recent(self.model.current["fname"])

    def open_data(self, fname=None):
        """Open raw file."""
        if fname is None:
            fname = QFileDialog.getOpenFileName(self, "Open raw")[0]
        if fname:
            if not (Path(fname).is_file() or Path(fname).is_dir()):
                self._remove_recent(fname)
                QMessageBox.critical(self, "File does not exist",
                                     f"File {fname} does not exist anymore.")
                return

            ext = "".join(Path(fname).suffixes)

            if ext in [".xdf", ".xdfz", ".xdf.gz"]:
                rows, disabled = [], []
                for idx, s in enumerate(get_streams(fname)):
                    rows.append([s["stream_id"], s["name"], s["type"], s["channel_count"],
                                 s["channel_format"], s["nominal_srate"]])
                    is_marker = (s["nominal_srate"] == 0 or s["channel_format"] == "string")
                    if is_marker:  # disable marker streams
                        disabled.append(idx)

                enabled = list(set(range(len(rows))) - set(disabled))
                if enabled:
                    selected = enabled[0]
                else:
                    selected = None
                dialog = XDFStreamsDialog(self, rows, selected=selected, disabled=disabled)
                if dialog.exec_():
                    row = dialog.view.selectionModel().selectedRows()[0].row()
                    stream_id = dialog.model.data(dialog.model.index(row, 0))
                    self.model.load(fname, stream_id=stream_id)
            else:  # all other file formats
                try:
                    self.model.load(fname)
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))
                except ValueError as e:
                    QMessageBox.critical(self, "Unknown file type", str(e))

    def open_file(self, f, text, ffilter="*"):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, text, filter=ffilter)[0]
        if fname:
            f(fname)

    def export_file(self, f, text, ffilter="*"):
        """Export to file."""
        fname = QFileDialog.getSaveFileName(self, text, filter=ffilter)[0]
        if fname:
            if ffilter != "*":
                exts = [ext.replace("*", "") for ext in ffilter.split()]

                maxsuffixes = max([ext.count(".") for ext in exts])
                suffixes = Path(fname).suffixes
                for i in range(-maxsuffixes, 0):
                    ext = "".join(suffixes[i:])
                    if ext in exts:
                        return f(fname)
                fname = fname + exts[0]
                return f(fname)

    def import_file(self, f, text, ffilter="*"):
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
        msg = QMessageBox.question(self, "Close all data sets", "Close all data sets?")
        if msg == QMessageBox.Yes:
            while len(self.model) > 0:
                self.model.remove_data()

    def meta_info(self):
        """Show XDF meta info."""
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
        dialog = MontageDialog(self, montages)
        if dialog.exec_():
            name = dialog.montages.selectedItems()[0].data(0)
            montage = mne.channels.make_standard_montage(name)
            ch_names = self.model.current["data"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                self.model.set_montage(name)
            else:
                QMessageBox.critical(
                    self, "No matching channel names", "Channel names defined in the "
                    "montage do not match any channel name in the data."
                )

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
        """Crop data."""
        fs = self.model.current["data"].info["sfreq"]
        length = self.model.current["data"].n_times / fs
        dialog = CropDialog(self, 0, length)
        if dialog.exec_():
            self.auto_duplicate()
            self.model.crop(dialog.start or 0, dialog.stop)

    def append_data(self):
        """Concatenate raw data objects to current one."""
        compatibles = self.model.get_compatibles()
        dialog = AppendDialog(self, compatibles)
        if dialog.exec_():
            self.auto_duplicate()
            self.model.append_data(dialog.names)

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
        if events is not None:
            hist = f"data.plot(events=events, n_channels={nchan})"
        else:
            hist = f"data.plot(n_channels={nchan})"
        self.model.history.append(hist)
        win = fig.canvas.manager.window
        win.setWindowTitle(self.model.current["name"])
        win.statusBar().hide()  # not necessary since matplotlib 3.3
        win.installEventFilter(self)  # detect if the figure is closed

        # prevent closing the window with the escape key
        try:
            fig._mne_params["close_key"] = None
        except AttributeError:  # does not exist in older MNE versions
            pass

        fig.show()

    def plot_psd(self):
        """Plot power spectral density (PSD)."""
        kwds = {}
        if self.model.current["dtype"] == "raw":
            kwds.update({"average": False, "spatial_colors": False})
        fig = self.model.current["data"].plot_psd(show=False, **kwds)
        if kwds:
            tmp = ", ".join(f"{key}={value}" for key, value in kwds.items())
            hist = f"data.plot_psd({tmp})"
        else:
            hist = "data.plot_psd()"
        self.model.history.append(hist)
        win = fig.canvas.manager.window
        win.setWindowTitle("Power spectral density")
        fig.show()

    def plot_locations(self):
        """Plot current montage."""
        fig = self.model.current["data"].plot_sensors(show_names=True, show=False)
        win = fig.canvas.manager.window
        win.setWindowTitle("Montage")
        win.statusBar().hide()  # not necessary since matplotlib 3.3
        fig.show()

    def plot_ica_components(self):
        self.model.current["ica"].plot_components(inst=self.model.current["data"])

    def plot_ica_sources(self):
        self.model.current["ica"].plot_sources(inst=self.model.current["data"])

    def plot_erds(self):
        """Plot ERDS maps."""
        data = self.model.current["data"]
        t_range = [data.tmin, data.tmax]
        f_range = [1, data.info["sfreq"] / 2]

        dialog = ERDSDialog(self, t_range, f_range)

        if dialog.exec_():
            freqs = np.arange(dialog.f1, dialog.f2, dialog.step)
            baseline = [dialog.b1, dialog.b2]
            times = [dialog.t1, dialog.t2]
            figs = plot_erds(data, freqs, freqs, baseline, times)
            for fig in figs:
                fig.show()

    def run_ica(self):
        """Run ICA calculation."""

        methods = ["Infomax"]
        if have["picard"]:
            methods.insert(0, "Picard")
        if have["sklearn"]:
            methods.append("FastICA")

        dialog = RunICADialog(self, self.model.current["data"].info["nchan"], methods)

        if dialog.exec_():
            calc = CalcDialog(self, "Calculating ICA", "Calculating ICA.")

            method = dialog.method.currentText().lower()
            exclude_bad_segments = dialog.exclude_bad_segments.isChecked()

            fit_params = {}
            if dialog.extended.isEnabled():
                fit_params["extended"] = dialog.extended.isChecked()
            if dialog.ortho.isEnabled():
                fit_params["ortho"] = dialog.ortho.isChecked()

            ica = mne.preprocessing.ICA(method=method, fit_params=fit_params)
            history = f"ica = mne.preprocessing.ICA(method='{method}'"
            if fit_params:
                history += f", fit_params={fit_params})"
            else:
                history += ")"
            self.model.history.append(history)

            pool = mp.Pool(processes=1)

            def callback(x):
                QMetaObject.invokeMethod(calc, "accept", Qt.QueuedConnection)

            res = pool.apply_async(
                func=ica.fit,
                args=(self.model.current["data"],),
                kwds={"reject_by_annotation": exclude_bad_segments},
                callback=callback
            )
            pool.close()

            if not calc.exec_():
                pool.terminate()
                print("ICA calculation aborted...")
            else:
                self.model.current["ica"] = res.get(timeout=1)
                self.model.history.append(f"ica.fit(inst=raw, reject_by_annotation="
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
                self.model.interpolate_bads(dialog.reset_bads, dialog.mode, dialog.origin)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(self, "Could not interpolate bad channels", str(e),
                                         traceback.format_exc())
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
            self.model.find_events(
                stim_channel=stim_channel,
                consecutive=consecutive,
                initial_event=initial_event,
                uint_cast=uint_cast,
                min_duration=min_dur,
                shortest_event=shortest_event
            )

    def events_from_annotations(self):
        self.model.events_from_annotations()

    def annotations_from_events(self):
        self.model.annotations_from_events()

    def epoch_data(self):
        """Epoch raw data."""
        dialog = EpochDialog(self, self.model.current["events"])
        if dialog.exec_():
            events = [int(item.text()) for item in dialog.events.selectedItems()]
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
                msgbox = ErrorMessageBox(self, "Could not create epochs", str(e),
                                         traceback.format_exc())
                msgbox.show()

    def convert_od(self):
        """Convert to optical density."""
        self.auto_duplicate()
        self.model.convert_od()

    def convert_bl(self):
        """Convert to haemoglobin."""
        self.auto_duplicate()
        self.model.convert_beer_lambert()

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
        from . import __version__

        msg_box = QMessageBox(self)
        text = (f"<img src='{image_path('mnelab_logo.png')}'><p>MNELAB {__version__}</p>")
        msg_box.setText(text)

        mnelab_url = "github.com/cbrnr/mnelab"
        mne_url = "github.com/mne-tools/mne-python"

        pkgs = []
        for key, value in have.items():
            if value:
                pkgs.append(f"{key}&nbsp;({value})")
            else:
                pkgs.append(f"{key}&nbsp;(not installed)")
        version = ".".join(str(k) for k in version_info[:3])
        text = (f"<nobr><p>This program uses Python {version} and the following packages:"
                f"</p></nobr><p>{', '.join(pkgs)}</p>"
                f"<nobr><p>MNELAB repository: <a href=https://{mnelab_url}>{mnelab_url}</a>"
                f"</p></nobr><nobr><p>MNE repository: "
                f"<a href=https://{mne_url}>{mne_url}</a></p></nobr>"
                f"<p>Licensed under the BSD 3-clause license.</p>"
                f"<p>Copyright 2017&ndash;2021 by Clemens Brunner.</p>")
        msg_box.setInformativeText(text)
        msg_box.exec_()

    def show_about_qt(self):
        """Show About Qt dialog."""
        QMessageBox.aboutQt(self, "About Qt")

    def auto_duplicate(self):
        """Automatically duplicate current data set.

        If the current data set is stored in a file (i.e. was loaded directly from a file),
        a new data set is automatically created. If the current data set is not stored in a
        file (i.e. was created by operations in MNELAB), a dialog box asks the user if the
        current data set should be overwritten or duplicated.

        Returns
        -------
        duplicated : bool
            True if the current data set was automatically duplicated, False if the current
            data set was overwritten.
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

    @Slot(QModelIndex)
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
            self.model.history.append(f"data = datasets[{self.model.index}]")

    @Slot(QModelIndex, QModelIndex)
    def _update_names(self, start, stop):
        """Update names in DataSets after changes in sidebar."""
        for index in range(start.row(), stop.row() + 1):
            self.model.data[index]["name"] = self.names.stringList()[index]

    @Slot()
    def _update_recent_menu(self):
        self.recent_menu.clear()
        for recent in self.recent:
            self.recent_menu.addAction(recent)

    @Slot(QAction)
    def _load_recent(self, action):
        self.open_data(fname=action.text())

    @Slot()
    def _toggle_toolbar(self):
        if self.toolbar.isHidden():
            self.toolbar.show()
        else:
            self.toolbar.hide()
        write_settings(toolbar=not self.toolbar.isHidden())

    @Slot()
    def _toggle_statusbar(self):
        if self.statusBar().isHidden():
            self.statusBar().show()
        else:
            self.statusBar().hide()
        write_settings(statusbar=not self.statusBar().isHidden())

    @Slot(QDropEvent)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    @Slot(QDropEvent)
    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            for url in urls:
                try:
                    self.open_data(url.toLocalFile())
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))

    @Slot(QEvent)
    def closeEvent(self, event):
        """Close application.

        Parameters
        ----------
        event : QEvent
            Close event.
        """
        write_settings(size=self.size(), pos=self.pos())
        if self.model.history:
            print("\n# Command History\n")
            print("\n".join(self.model.history))
        QApplication.quit()

    def eventFilter(self, source, event):
        # currently the only source is the raw plot window
        if event.type() == QEvent.Close:
            self.data_changed()
            bads = self.model.current["data"].info["bads"]
            if self.bads != bads:
                self.model.history.append(f'data.info["bads"] = {bads}')
        return QObject.eventFilter(self, source, event)

    def event(self, ev):
        """Catch system events."""
        if ev.type() == QEvent.PaletteChange:  # detect theme switches
            style = interface_style()  # light or dark
            if style is not None:
                QIcon.setThemeName(style)
            else:
                QIcon.setThemeName("light")  # fallback
        return super().event(ev)
