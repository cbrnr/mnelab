# © MNELAB developers
#
# License: BSD (3-clause)

import multiprocessing as mp
import sys
import traceback
from contextlib import contextmanager
from functools import partial
from operator import itemgetter
from pathlib import Path
from sys import version_info

import mne
import numpy as np
from mne import channel_type
from PySide6.QtCore import QEvent, QMetaObject, QModelIndex, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices, QDropEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
)
from pyxdf import resolve_streams

from mnelab.dialogs import *  # noqa: F403
from mnelab.io import writers
from mnelab.io.mat import parse_mat
from mnelab.io.readers import parse_npy
from mnelab.io.xdf import get_xml, list_chunks
from mnelab.model import InvalidAnnotationsError, LabelsNotFoundError, Model
from mnelab.settings import SettingsDialog, read_settings, write_settings
from mnelab.utils import count_locations, have, image_path, natural_sort
from mnelab.viz import (
    _calc_tfr,
    plot_erds,
    plot_erds_topomaps,
    plot_evoked,
    plot_evoked_comparison,
    plot_evoked_topomaps,
)
from mnelab.widgets import EmptyWidget, InfoWidget


class MainWindow(QMainWindow):
    """MNELAB main window."""

    def __init__(self, model: Model):
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
        sys.excepthook = self._excepthook

        # restore settings
        settings = read_settings()
        self.recent = settings["recent"]  # list of recent files
        self.resize(settings["size"])
        self.move(settings["pos"])

        # remove None entries from self.recent
        self.recent = [recent for recent in self.recent if recent is not None]

        # plot backend
        self.plot_backends = ["Matplotlib"]
        if have["mne-qt-browser"]:
            self.plot_backends.append("Qt")
        plot_backend = settings["plot_backend"]
        if plot_backend not in self.plot_backends:
            plot_backend = "Matplotlib"
        mne.viz.set_browser_backend(plot_backend)

        # trigger theme setting
        QIcon.setThemeSearchPaths(
            [f"{Path(__file__).parent}/icons"] + QIcon.themeSearchPaths()
        )
        QIcon.setFallbackThemeName("light")
        self.event(QEvent(QEvent.PaletteChange))

        self.actions = {}  # contains all actions

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        self.actions["open_file"] = file_menu.addAction(
            QIcon.fromTheme("open-file"), "&Open...", self.open_data, QKeySequence.Open
        )
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.actions["close_file"] = file_menu.addAction(
            "&Close", self.model.remove_data, QKeySequence.Close
        )
        self.actions["close_all"] = file_menu.addAction("Close all", self.close_all)
        file_menu.addSeparator()
        self.actions["import_bads"] = file_menu.addAction(
            "Import bad channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels", "*.csv"),
        )
        self.actions["import_events"] = file_menu.addAction(
            "Import events...",
            lambda: self.import_file(model.import_events, "Import events", "*.csv *.fif"),
        )
        self.actions["import_annotations"] = file_menu.addAction(
            "Import annotations...",
            lambda: self.import_file(
                model.import_annotations, "Import annotations", "*.csv"
            ),
        )
        self.actions["import_ica"] = file_menu.addAction(
            "Import &ICA...",
            lambda: self.open_file(model.import_ica, "Import ICA", "*.fif *.fif.gz"),
        )
        file_menu.addSeparator()
        self.export_menu = file_menu.addMenu("Export data")
        for ext, description in writers.items():
            action = "export_data" + ext.replace(".", "_")
            self.actions[action] = self.export_menu.addAction(
                f"{ext[1:].upper()} ({description[1]})...",
                partial(self.export_file, model.export_data, "Export data", "*" + ext),
            )
        self.actions["export_bads"] = file_menu.addAction(
            "Export &bad channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels", "*.csv"),
        )
        self.actions["export_events"] = file_menu.addAction(
            "Export &events...",
            lambda: self.export_file(model.export_events, "Export events", "*.csv"),
        )
        self.actions["export_annotations"] = file_menu.addAction(
            "Export &annotations...",
            lambda: self.export_file(
                model.export_annotations, "Export annotations", "*.csv"
            ),
        )
        self.actions["export_ica"] = file_menu.addAction(
            "Export ICA...",
            lambda: self.export_file(model.export_ica, "Export ICA", "*.fif *.fif.gz"),
        )
        file_menu.addSeparator()
        self.actions["xdf_metadata"] = file_menu.addAction(
            QIcon.fromTheme("xdf-metadata"),
            "Show XDF metadata",
            self.xdf_metadata,
        )
        self.actions["xdf_chunks"] = file_menu.addAction(
            "Inspect XDF chunks...", self.xdf_chunks
        )
        file_menu.addSeparator()
        self.actions["settings"] = file_menu.addAction(
            QIcon.fromTheme("settings"),
            "Settings...",
            QKeySequence(Qt.CTRL | Qt.Key_Comma),
            self.settings,
        )
        file_menu.addSeparator()
        self.actions["quit"] = file_menu.addAction("&Quit", self.close, QKeySequence.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.actions["pick_chans"] = edit_menu.addAction(
            "P&ick channels...", self.pick_channels
        )
        self.actions["rename_channels"] = edit_menu.addAction(
            "Rename channels...",
            self.rename_channels,
        )
        self.actions["chan_props"] = edit_menu.addAction(
            QIcon.fromTheme("chan-props"),
            "Edit channel &properties...",
            self.channel_properties,
        )
        edit_menu.addSeparator()
        self.actions["set_montage"] = edit_menu.addAction(
            "Set &montage...", self.set_montage
        )
        self.actions["clear_montage"] = edit_menu.addAction(
            "Clear montage",
            self.clear_montage,
        )
        edit_menu.addSeparator()
        self.actions["change_ref"] = edit_menu.addAction(
            "Change &reference...",
            self.change_reference,
        )
        edit_menu.addSeparator()
        self.actions["annotations"] = edit_menu.addAction(
            "Edit &Annotations...",
            self.edit_annotations,
        )
        self.actions["events"] = edit_menu.addAction(
            "Edit &Events...",
            self.edit_events,
        )

        edit_menu.addSeparator()
        self.actions["crop"] = edit_menu.addAction("&Crop data...", self.crop)
        self.actions["append_data"] = edit_menu.addAction(
            "Appen&d data...", self.append_data
        )

        plot_menu = self.menuBar().addMenu("&Plot")
        self.actions["plot_data"] = plot_menu.addAction(
            QIcon.fromTheme("plot-data"),
            "Plot &Data",
            self.plot_data,
        )
        self.actions["plot_psd"] = plot_menu.addAction(
            QIcon.fromTheme("plot-psd"),
            "Plot &PSD",
            self.plot_psd,
        )
        plot_menu.addSeparator()
        self.actions["plot_locations"] = plot_menu.addAction(
            QIcon.fromTheme("plot-locations"),
            "Plot &channel locations",
            self.plot_locations,
        )
        plot_menu.addSeparator()
        self.actions["plot_erds"] = plot_menu.addAction(
            "Plot &ERDS maps...",
            self.plot_erds,
        )
        self.actions["plot_erds_topomaps"] = plot_menu.addAction(
            "Plot ERDS topomaps...",
            self.plot_erds_topomaps,
        )
        plot_menu.addSeparator()
        self.actions["plot_evoked"] = plot_menu.addAction(
            "Plot evoked...",
            self.plot_evoked,
        )
        self.actions["plot_evoked_comparison"] = plot_menu.addAction(
            "Plot evoked comparison...",
            self.plot_evoked_comparison,
        )
        self.actions["plot_evoked_topomaps"] = plot_menu.addAction(
            "Plot evoked topomaps...",
            self.plot_evoked_topomaps,
        )
        plot_menu.addSeparator()
        self.actions["plot_ica_components"] = plot_menu.addAction(
            "Plot ICA &components",
            self.plot_ica_components,
        )
        self.actions["plot_ica_sources"] = plot_menu.addAction(
            "Plot ICA &sources",
            self.plot_ica_sources,
        )

        tools_menu = self.menuBar().addMenu("&Tools")
        self.actions["filter"] = tools_menu.addAction(
            QIcon.fromTheme("filter-data"), "&Filter data...", self.filter_data
        )
        self.actions["find_events"] = tools_menu.addAction(
            QIcon.fromTheme("find-events"), "Find &events...", self.find_events
        )
        self.actions["events_from_annotations"] = tools_menu.addAction(
            "Create events from annotations", self.events_from_annotations
        )
        self.actions["annotations_from_events"] = tools_menu.addAction(
            "Create annotations from events", self.annotations_from_events
        )
        tools_menu.addSeparator()
        self.actions["convert_od"] = tools_menu.addAction(
            "Convert to &optical density",
            self.convert_od,
        )
        self.actions["convert_bl"] = tools_menu.addAction(
            "Convert to &haemoglobin",
            self.convert_bl,
        )
        tools_menu.addSeparator()

        self.actions["run_ica"] = tools_menu.addAction(
            QIcon.fromTheme("run-ica"), "Run &ICA...", self.run_ica
        )
        self.actions["apply_ica"] = tools_menu.addAction("Apply &ICA", self.apply_ica)
        tools_menu.addSeparator()
        self.actions["interpolate_bads"] = tools_menu.addAction(
            "Interpolate bad channels...", self.interpolate_bads
        )
        tools_menu.addSeparator()
        self.actions["epoch_data"] = tools_menu.addAction(
            QIcon.fromTheme("epoch-data"), "Create epochs...", self.epoch_data
        )
        self.actions["drop_bad_epochs"] = tools_menu.addAction(
            "Drop bad epochs...",
            self.drop_bad_epochs,
        )

        view_menu = self.menuBar().addMenu("&View")
        self.actions["history"] = view_menu.addAction(
            "&History",
            self.show_history,
            QKeySequence(Qt.CTRL | Qt.Key_Y),
        )
        self.actions["toolbar"] = view_menu.addAction("&Toolbar", self._toggle_toolbar)
        self.actions["toolbar"].setCheckable(True)
        self.actions["statusbar"] = view_menu.addAction(
            "&Statusbar", self._toggle_statusbar
        )
        self.actions["statusbar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.actions["about"] = help_menu.addAction("&About", self.show_about)
        self.actions["about_qt"] = help_menu.addAction("About &Qt", self.show_about_qt)
        help_menu.addSeparator()
        self.actions["documentation"] = help_menu.addAction(
            "&Documentation",
            self.show_documentation,
        )
        # actions that are always enabled
        self.always_enabled = [
            "open_file",
            "about",
            "about_qt",
            "quit",
            "xdf_chunks",
            "toolbar",
            "statusbar",
            "settings",
            "documentation",
            "history",
        ]

        # set up toolbar
        self.toolbar = self.addToolBar("toolbar")
        self.toolbar.setObjectName("toolbar")
        self.toolbar.addAction(self.actions["open_file"])
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
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions["settings"])
        self.toolbar.setMovable(False)
        self.setUnifiedTitleAndToolBarOnMac(True)
        if settings["toolbar"]:
            self.toolbar.show()
            self.actions["toolbar"].setChecked(True)
        else:
            self.toolbar.hide()
            self.actions["toolbar"].setChecked(False)

        # set up data model for sidebar (list of open files)
        self.sidebar = QListWidget()
        self.sidebar.setFrameStyle(QFrame.NoFrame)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setAcceptDrops(True)
        self.sidebar.setDragEnabled(True)
        self.sidebar.setDragDropMode(QListWidget.InternalMove)
        self.sidebar.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.sidebar.setEditTriggers(QListWidget.DoubleClicked)
        self.sidebar.model().rowsMoved.connect(self._sidebar_move_event)
        self.sidebar.itemDelegate().commitData.connect(self._sidebar_edit_event)
        self.sidebar.clicked.connect(self._update_data)

        splitter = QSplitter()
        splitter.addWidget(self.sidebar)

        self.infowidget = QStackedWidget()
        self.infowidget.addWidget(InfoWidget())
        emptywidget = EmptyWidget(
            itemgetter("open_file", "history", "settings")(self.actions)
        )
        self.infowidget.addWidget(emptywidget)
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

    def _excepthook(self, type, value, traceback_):
        exception_text = str(value)
        traceback_text = "".join(traceback.format_exception(type, value, traceback_))
        print(traceback_text, file=sys.stderr)
        ErrorMessageBox(self, exception_text, "", traceback_text).show()

    def _sidebar_edit_event(self, edit):
        """
        Triggered when a data set in the sidebar is renamed.

        Parameters
        ----------
        edit : PySide6.QtWidgets.QLineEdit
            The text editor.
        """
        self.model.current["name"] = edit.text()

    def _sidebar_move_event(self, parent, start, end, destination, row):
        """
        Triggered when an item in the sidebar is moved.

        Parameters
        ----------
        parent : PySide6.QtCore.QModelIndex
            Unused.
        start : int
            The source index of the item.
        end : int
            Unused (equals start as the sidebar only allows single selection).
        destination : PySide6.QtCore.QModelIndex
            Unused.
        row : int
            The target index.
        """
        self.model.move_data(start, row)

    @contextmanager
    def _wait_cursor(self):
        # disabled on macOS because of outdated icon
        if sys.platform.startswith("darwin"):
            yield
        else:
            default_cursor = self.cursor()
            self.setCursor(Qt.WaitCursor)
            try:
                yield
            finally:
                self.setCursor(default_cursor)

    def data_changed(self):
        # update sidebar
        self.sidebar.clear()
        self.sidebar.insertItems(0, self.model.names)
        self.sidebar.setCurrentRow(self.model.index)
        for it in range(self.sidebar.count()):
            item = self.sidebar.item(it)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

        # update info widget
        if self.model.data:
            self.infowidget.setCurrentIndex(0)
            self.infowidget.widget(0).set_values(self.model.get_info())
        else:
            self.infowidget.setCurrentIndex(1)

        # update status bar
        if self.model.data:
            mb = self.model.nbytes / 1024**2
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
            events = len(self.model.current["events"]) > 0
            self.actions["export_events"].setEnabled(enabled and events)
            if self.model.current["dtype"] == "raw":
                annot = bool(self.model.current["data"].annotations)
            else:
                annot = False
            self.actions["export_annotations"].setEnabled(enabled and annot)
            self.actions["annotations"].setEnabled(enabled)
            locations = count_locations(self.model.current["data"].info)
            self.actions["plot_locations"].setEnabled(enabled and locations)
            ica = bool(self.model.current["ica"])
            self.actions["apply_ica"].setEnabled(enabled and ica)
            self.actions["export_ica"].setEnabled(enabled and ica)
            self.actions["plot_erds"].setEnabled(
                enabled and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_erds_topomaps"].setEnabled(
                enabled and locations and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_evoked"].setEnabled(
                enabled and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_evoked_comparison"].setEnabled(
                enabled and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_evoked_topomaps"].setEnabled(
                enabled and locations and self.model.current["dtype"] == "epochs"
            )
            self.actions["plot_ica_components"].setEnabled(enabled and ica and locations)
            self.actions["plot_ica_sources"].setEnabled(enabled and ica)
            self.actions["interpolate_bads"].setEnabled(enabled and locations and bads)
            self.actions["events"].setEnabled(enabled)
            self.actions["events_from_annotations"].setEnabled(enabled and annot)
            self.actions["annotations_from_events"].setEnabled(enabled and events)
            self.actions["find_events"].setEnabled(
                enabled and self.model.current["dtype"] == "raw"
            )
            self.actions["epoch_data"].setEnabled(
                enabled and events and self.model.current["dtype"] == "raw"
            )
            self.actions["drop_bad_epochs"].setEnabled(
                enabled and events and self.model.current["dtype"] == "epochs"
            )
            self.actions["clear_montage"].setEnabled(
                enabled and self.model.current["montage"] is not None
            )
            self.actions["crop"].setEnabled(
                enabled and self.model.current["dtype"] == "raw"
            )
            append = bool(self.model.get_compatibles())
            self.actions["append_data"].setEnabled(
                enabled and append and (self.model.current["dtype"] in ("raw", "epochs"))
            )
            self.actions["xdf_metadata"].setEnabled(
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
            # getOpenFileNames returns a tuple (filenames, selected_filter)
            fnames, _ = QFileDialog.getOpenFileNames(self, "Open raw")
        else:
            fnames = [fname]
        for fname in fnames:
            if not (Path(fname).is_file() or Path(fname).is_dir()):
                self._remove_recent(fname)
                QMessageBox.critical(
                    self, "File does not exist", f"File {fname} does not exist anymore."
                )
                return

            ext = "".join(Path(fname).suffixes)

            if any([ext.endswith(e) for e in (".xdf", ".xdfz", ".xdf.gz")]):  # XDF
                rows = []
                for s in resolve_streams(fname):
                    rows.append(
                        [
                            s["stream_id"],
                            s["name"],
                            s["type"],
                            s["channel_count"],
                            s["channel_format"],
                            s["nominal_srate"],
                        ]
                    )
                dialog = XDFStreamsDialog(
                    self,
                    rows,
                    fname=fname,
                    selected=None,
                )
                if dialog.exec():
                    fs_new = None
                    if dialog.resample.isChecked():
                        fs_new = float(dialog.fs_new.value())
                    self.model.load(
                        fname,
                        stream_ids=dialog.selected_streams,
                        marker_ids=dialog.selected_markers,
                        prefix_markers=dialog.prefix_markers,
                        fs_new=fs_new,
                    )
            elif ext.lower() == ".mat":
                dialog = MatDialog(self, Path(fname).name, parse_mat(fname))
                if dialog.exec():
                    self.model.load(
                        fname,
                        variable=dialog.name,
                        fs=dialog.fs,
                        transpose=dialog.transpose,
                    )
            elif ext == ".npy":
                dialog = NpyDialog(self, parse_npy(fname))
                if dialog.exec_():
                    self.model.load(fname, dialog.fs, dialog.transpose)
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

    def xdf_chunks(self):
        """Inspect XDF chunks."""
        fname = QFileDialog.getOpenFileName(
            self, "Select XDF file", filter="*.xdf *.xdfz *.xdf.gz"
        )[0]
        if fname:
            chunks = list_chunks(fname)
            dialog = XDFChunksDialog(self, chunks, fname)
            dialog.exec()

    def export_file(self, f, text, ffilter="*"):
        """Export to file."""
        fname = QFileDialog.getSaveFileName(self, text)[0]
        if fname:
            exts = [ext.replace("*", "") for ext in ffilter.split()]
            for ext in exts:
                if fname.endswith(ext):
                    return f(fname)
            return f(fname + exts[0])

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

    def xdf_metadata(self, fname=None):
        """Show XDF metadata."""
        if fname is None:
            fname = self.model.current["fname"]
        xml = get_xml(fname)
        dialog = XDFMetadataDialog(self, xml)
        dialog.exec()

    def pick_channels(self):
        """Pick channels in current data set."""
        channels = self.model.current["data"].info["ch_names"]
        types = sorted(set(self.model.current["data"].get_channel_types()))
        dialog = PickChannelsDialog(self, channels, types)
        if dialog.exec():
            if dialog.by_name.isChecked():
                picks = [item.text() for item in dialog.names.selectedItems()]
                if set(channels) == set(picks):
                    return
            else:  # by type
                picks = [item.text() for item in dialog.types.selectedItems()]
                if set(types) == set(picks):
                    return
            self.auto_duplicate()
            self.model.pick_channels(picks)

    def channel_properties(self):
        """Show channel properties dialog."""
        info = self.model.current["data"].info
        dialog = ChannelPropertiesDialog(self, info)
        if dialog.exec():
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

    def rename_channels(self):
        dialog = RenameChannelsDialog(self, self.model.current["data"].info["ch_names"])
        if dialog.exec():
            self.model.rename_channels(dialog.new_names)

    def set_montage(self):
        """Set montage."""
        montages = natural_sort(mne.channels.get_builtin_montages())
        dialog = MontageDialog(self, montages)
        if dialog.exec():
            name = dialog.montages.selectedItems()[0].data(0)
            montage = mne.channels.make_standard_montage(name)
            ch_names = self.model.current["data"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                self.model.set_montage(
                    name,
                    match_case=dialog.match_case.isChecked(),
                    match_alias=dialog.match_alias.isChecked(),
                    on_missing="ignore" if dialog.ignore_missing.isChecked() else "raise",
                )
            else:
                QMessageBox.critical(
                    self,
                    "No matching channel names",
                    "Channel names defined in the montage do not match any channel name in "
                    "the data.",
                )

    def clear_montage(self):
        self.model.set_montage(None)

    def edit_annotations(self):
        fs = self.model.current["data"].info["sfreq"]
        pos = self.model.current["data"].annotations.onset
        pos = (pos * fs).astype(int).tolist()
        dur = self.model.current["data"].annotations.duration
        dur = (dur * fs).astype(int).tolist()
        desc = self.model.current["data"].annotations.description.tolist()
        dialog = AnnotationsDialog(self, pos, dur, desc)
        if dialog.exec():
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
        dialog = EventsDialog(self, pos, desc, self.model.current["event_mapping"])
        if dialog.exec():
            rows = dialog.event_table.rowCount()
            events = np.zeros((rows, 3), dtype=int)
            for i in range(rows):
                pos = dialog.event_table.item(i, 0).value()
                desc = dialog.event_table.item(i, 1).value()
                events[i] = pos, 0, desc
            self.model.current["event_mapping"] = dict(dialog.event_mapping)
            if self.model.current["dtype"] == "epochs":
                event_id_old = self.model.current["data"].event_id
                event_id_new = {
                    f"{k} ({v})": k
                    for k, v in dialog.event_mapping.items()
                    if k in event_id_old.values()
                }
                self.model.current["data"].event_id = event_id_new
            self.model.set_events(events)

    def crop(self):
        """Crop data."""
        stop = self.model.current["data"].times[-1]
        dialog = CropDialog(self, 0, stop)
        if dialog.exec():
            self.auto_duplicate()
            self.model.crop(max(dialog.start, 0), min(dialog.stop, stop))

    def append_data(self):
        """Concatenate raw data objects to current one."""
        compatibles = self.model.get_compatibles()
        dialog = AppendDialog(self, compatibles)
        if dialog.exec():
            self.auto_duplicate()
            self.model.append_data(dialog.names)

    def plot_data(self):
        """Plot data."""
        # self.bad is needed to update history if bad channels are selected in the
        # interactive plot window (see also self.eventFilter)
        self.bads = self.model.current["data"].info["bads"]
        events = self.model.current["events"]
        nchan = self.model.current["data"].info["nchan"]
        fig = self.model.current["data"].plot(
            events=events,
            n_channels=nchan,
            title=self.model.current["name"],
            scalings="auto",
            show=False,
        )
        if events is not None:
            hist = f"data.plot(events=events, n_channels={nchan})"
        else:
            hist = f"data.plot(n_channels={nchan})"
        self.model.history.append(hist)
        if mne.viz.get_browser_backend() == "matplotlib":
            win = fig.canvas.manager.window
            win.setWindowTitle(self.model.current["name"])
            win.statusBar().hide()  # not necessary since matplotlib 3.3
            fig.canvas.mpl_connect("close_event", self._plot_closed)
            fig.mne.close_key = None
        else:
            fig.gotClosed.connect(self._plot_closed)
            fig.mne.keyboard_shortcuts.pop("escape")

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

        if dialog.exec():
            freqs = np.arange(dialog.f1, dialog.f2, dialog.step)
            baseline = (dialog.b1, dialog.b2)
            times = [dialog.t1, dialog.t2]
            alpha = None
            if dialog.significance_mask.isChecked():
                alpha = dialog.alpha.value()

            calc = CalcDialog(self, "Calculating ERDS maps", "Calculating ERDS maps...")

            def callback(x):
                QMetaObject.invokeMethod(calc, "accept", Qt.QueuedConnection)

            pool = mp.Pool(processes=1)
            res = pool.apply_async(
                func=_calc_tfr,
                args=(data, freqs, baseline, times, alpha),
                callback=callback,
            )
            pool.close()

            if not calc.exec():
                pool.terminate()
                print("ERDS map calculation aborted.")
            else:
                tfr_and_masks = res.get(timeout=1)
                figs = plot_erds(tfr_and_masks)
                for fig in figs:
                    fig.show()

    def plot_erds_topomaps(self):
        """Plot ERDS topomaps."""
        epochs = self.model.current["data"]
        t_range = [epochs.tmin, epochs.tmax]
        f_range = [1, epochs.info["sfreq"] / 2]

        dialog = ERDSTopomapsDialog(self, t_range, f_range, epochs.event_id)
        if dialog.exec():
            figs = plot_erds_topomaps(
                epochs,
                events=[item.text() for item in dialog.events.selectedItems()],
                freqs=np.arange(dialog.f1, dialog.f2, dialog.step),
                baseline=(dialog.b1, dialog.b2),
                times=[dialog.t1, dialog.t2],
            )
            for fig in figs:
                fig.show()

    def plot_evoked(self):
        """Plot evoked potentials for individual channels."""
        epochs = self.model.current["data"]
        dialog = PlotEvokedDialog(
            self,
            epochs.ch_names,
            epochs.event_id,
            epochs.get_montage(),
        )
        if dialog.exec():
            if dialog.topomaps.isChecked():
                if dialog.topomaps_peaks.isChecked():
                    topomap_times = "peaks"
                elif dialog.topomaps_auto.isChecked():
                    topomap_times = "auto"
                else:
                    topomap_times = [
                        float(t.strip()) for t in dialog.topomaps_timelist.text().split(",")
                    ]
            else:
                topomap_times = []
            figs = plot_evoked(
                epochs=epochs,
                picks=[item.text() for item in dialog.picks.selectedItems()],
                events=[item.text() for item in dialog.events.selectedItems()],
                gfp=dialog.gfp.isChecked(),
                spatial_colors=dialog.spatial_colors.isChecked(),
                topomap_times=topomap_times,
            )
            for fig in figs:
                fig.show()

    def plot_evoked_comparison(self):
        """Plot evoked potentials averaged over channels."""
        epochs = self.model.current["data"]
        dialog = PlotEvokedComparisonDialog(self, epochs.ch_names, epochs.event_id)
        if dialog.exec():
            figs = plot_evoked_comparison(
                epochs=epochs,
                picks=[item.text() for item in dialog.picks.selectedItems()],
                events=[item.text() for item in dialog.events.selectedItems()],
                average_method=dialog.average_epochs.currentText(),
                combine=dialog.combine_channels.currentText(),
                confidence_intervals=dialog.confidence_intervals.isChecked(),
            )
            for fig in figs:
                fig.show()

    def plot_evoked_topomaps(self):
        """Plot evoked topomaps."""
        epochs = self.model.current["data"]
        dialog = PlotEvokedTopomaps(self, epochs.event_id)
        if dialog.exec():
            if dialog.auto.isChecked():
                times = "auto"
            elif dialog.peaks.isChecked():
                times = "peaks"
            elif dialog.interactive.isChecked():
                times = "interactive"
            else:
                times = [float(t.strip()) for t in dialog.timelist.text().split(",")]

            figs = plot_evoked_topomaps(
                epochs=epochs,
                events=[item.text() for item in dialog.events.selectedItems()],
                average_method=dialog.average_epochs.currentText(),
                times=times,
            )
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

        if dialog.exec():
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
                callback=callback,
            )
            pool.close()

            if not calc.exec():
                pool.terminate()
                print("ICA calculation aborted...")
            else:
                self.model.current["ica"] = res.get(timeout=1)
                self.model.history.append(
                    f"ica.fit(inst=raw, reject_by_annotation=" f"{exclude_bad_segments})"
                )
                self.data_changed()

    def apply_ica(self):
        """Apply current fitted ICA."""
        self.auto_duplicate()
        self.model.apply_ica()

    def interpolate_bads(self):
        """Interpolate bad channels"""
        dialog = InterpolateBadsDialog(self)
        if dialog.exec():
            duplicated = self.auto_duplicate()
            try:
                self.model.interpolate_bads(dialog.reset_bads, dialog.mode, dialog.origin)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(
                    self,
                    "Could not interpolate bad channels",
                    str(e),
                    traceback.format_exc(),
                )
                msgbox.show()

    def filter_data(self):
        """Filter data."""
        dialog = FilterDialog(self)
        if dialog.exec():
            self.auto_duplicate()
            self.model.filter(dialog.low, dialog.high)

    def find_events(self):
        info = self.model.current["data"].info

        # use first stim channel as default in dialog
        default_stim = 0
        for i in range(info["nchan"]):
            if channel_type(info, i) == "stim":
                default_stim = i
                break
        dialog = FindEventsDialog(self, info["ch_names"], default_stim)
        if dialog.exec():
            stim_channel = dialog.stimchan.currentText()
            consecutive = dialog.consecutive.currentText().lower()
            if consecutive == "true":
                consecutive = True
            elif consecutive == "false":
                consecutive = False
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
                shortest_event=shortest_event,
            )

    def events_from_annotations(self):
        self.model.events_from_annotations()

    def annotations_from_events(self):
        self.model.annotations_from_events()

    def epoch_data(self):
        """Epoch raw data."""
        event_types = np.unique(self.model.current["events"][:, 2]).astype(str).tolist()
        dialog = EpochDialog(self, event_types)
        if dialog.exec():
            tmin = dialog.tmin.value()
            tmax = dialog.tmax.value()

            if dialog.baseline.isChecked():
                baseline = dialog.a.value(), dialog.b.value()
            else:
                baseline = None

            duplicated = self.auto_duplicate()

            try:
                self.model.epoch_data(dialog.selected_events, tmin, tmax, baseline)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(
                    self, "Could not create epochs", str(e), traceback.format_exc()
                )
                msgbox.show()

    def drop_bad_epochs(self):
        """Drop bad epochs."""

        def fields_to_dict(fields):
            res = {}
            for type, value in fields.items():
                if value.text():
                    res[type] = float(value.text())
            return res

        types = sorted(set(self.model.current["data"].get_channel_types()))
        dialog = DropBadEpochsDialog(self, types)
        if dialog.exec():
            reject = None
            flat = None
            if dialog.reject_box.isChecked():
                reject = fields_to_dict(dialog.reject_fields)
            if dialog.flat_box.isChecked():
                flat = fields_to_dict(dialog.flat_fields)
            if reject is None and flat is None:
                return
            self.auto_duplicate()
            self.model.drop_bad_epochs(reject, flat)

    def convert_od(self):
        """Convert to optical density."""
        self.auto_duplicate()
        self.model.convert_od()

    def convert_bl(self):
        """Convert to haemoglobin."""
        self.auto_duplicate()
        self.model.convert_beer_lambert()

    def change_reference(self):
        """Change reference."""
        dialog = ReferenceDialog(self, self.model.current["data"].info["ch_names"])
        if dialog.exec():
            if dialog.add_group.isChecked():
                add = [c.strip() for c in dialog.add_channellist.text().split(",")]
            else:
                add = []
            if dialog.reref_group.isChecked():
                if dialog.reref_average.isChecked():
                    ref = "average"
                else:
                    ref = [c.text() for c in dialog.reref_channellist.selectedItems()]
            else:
                ref = None
            duplicated = self.auto_duplicate()
            try:
                self.model.change_reference(add, ref)
            except ValueError as e:
                if duplicated:  # undo
                    self.model.remove_data()
                    # self.model.index -= 1
                    self.data_changed()
                msgbox = ErrorMessageBox(
                    self,
                    "Error while changing references:",
                    str(e),
                    traceback.format_exc(),
                )
                msgbox.show()

    def show_history(self):
        """Show history."""
        dialog = HistoryDialog(self, "\n".join(self.model.history))
        dialog.exec()

    def show_about(self):
        """Show About dialog."""
        from . import __version__

        msg_box = QMessageBox(self)
        text = f"<img src='{image_path('mnelab_logo.png')}'><p>MNELAB {__version__}</p>"
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
        text = (
            f"<nobr><p>This program uses Python {version} and the following packages:"
            f"</p></nobr><p>{', '.join(pkgs)}</p>"
            f"<nobr><p>MNELAB repository: <a href=https://{mnelab_url}>{mnelab_url}</a>"
            f"</p></nobr><nobr><p>MNE repository: "
            f"<a href=https://{mne_url}>{mne_url}</a></p></nobr>"
            f"<p>Licensed under the BSD 3-clause license.</p>"
            f"<p>© MNELAB developers.</p>"
        )
        msg_box.setInformativeText(text)
        msg_box.exec()

    def show_about_qt(self):
        """Show About Qt dialog."""
        QMessageBox.aboutQt(self, "About Qt")

    def show_documentation(self):
        url = QUrl("https://mnelab.readthedocs.io/")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Open Url", "Could not open url")

    def settings(self):
        SettingsDialog(self, self.plot_backends).exec()
        mne.viz.set_browser_backend(read_settings("plot_backend"))

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
        msg = QMessageBox(self)
        msg.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        msg.setWindowTitle("Modify data set")
        msg.setText(
            "You are about to modify the current data set. How do you want to proceed?"
        )
        create_button = msg.addButton("Create new data set", QMessageBox.AcceptRole)
        overwrite_button = msg.addButton(
            "Overwrite current data set", QMessageBox.RejectRole
        )
        msg.setDefaultButton(create_button)
        msg.setEscapeButton(create_button)
        msg.exec()
        if msg.clickedButton() == overwrite_button:
            return False
        else:
            self.model.duplicate_data()
            return True

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
        self.recent = self.recent[: read_settings("max_recent")]  # prune list
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
        event.accept()

    def _plot_closed(self, event=None):
        self.data_changed()
        bads = self.model.current["data"].info["bads"]
        if self.bads != bads:
            self.model.history.append(f'data.info["bads"] = {bads}')

    def event(self, ev):
        """Catch system events."""
        if ev.type() == QEvent.PaletteChange:  # detect theme switches
            if (style := QApplication.styleHints().colorScheme()) != Qt.ColorScheme.Unknown:
                QIcon.setThemeName(style.name.lower())
            else:
                QIcon.setThemeName("light")  # fallback
        return super().event(ev)
