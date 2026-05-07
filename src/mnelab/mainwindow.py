# © MNELAB developers
#
# License: BSD (3-clause)

import json
import logging
import multiprocessing as mp
import sys
import traceback
from contextlib import contextmanager
from functools import partial
from operator import itemgetter
from pathlib import Path
from sys import version_info
from urllib.request import Request, urlopen

import mne
import numpy as np
from mne import channel_type
from pybvrf import read_bvrf_header
from PySide6.QtCore import (
    QEvent,
    QMetaObject,
    Qt,
    QTimer,
    QUrl,
    Slot,
)
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProxyStyle,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStyle,
    QToolButton,
    QWidget,
)
from pyxdf import resolve_streams

from mnelab import IS_DEV_VERSION, __version__
from mnelab.dialogs import *  # noqa: F403
from mnelab.dialogs.channel_stats import ChannelStats
from mnelab.io import writers
from mnelab.io.mat import parse_mat
from mnelab.io.npy import parse_npy
from mnelab.io.readers import read_raw, split_name_ext
from mnelab.io.xdf import get_xml, list_chunks
from mnelab.model import (
    InvalidAnnotationsError,
    LabelsNotFoundError,
    Model,
    PipelineCancelledError,
)
from mnelab.settings import SettingsDialog, read_settings, write_settings
from mnelab.utils import (
    annotations_between_events,
    count_locations,
    format_code,
    get_annotation_types_from_file,
    have,
    image_path,
    natural_sort,
)
from mnelab.viz import (
    _calc_tfr,
    plot_erds,
    plot_erds_topomaps,
    plot_evoked,
    plot_evoked_comparison,
    plot_evoked_topomaps,
)
from mnelab.widgets import EmptyWidget, InfoWidget, PipelineTreeWidget


class MenuPaddingStyle(QProxyStyle):
    def sizeFromContents(self, contents_type, option, size, widget=None):
        base_size = super().sizeFromContents(contents_type, option, size, widget)

        if contents_type == QStyle.ContentsType.CT_MenuItem:
            base_size.setWidth(base_size.width() + 30)  # increase width

        return base_size


class _MNELogHandler(logging.Handler):
    """Logging handler that silently captures MNE messages into a list."""

    def __init__(self, log_list):
        super().__init__()
        self._log = log_list

    def emit(self, record):
        self._log.append(self.format(record))


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

        # capture MNE logging output
        _mne_logger = logging.getLogger("mne")
        for _h in list(_mne_logger.handlers):
            _mne_logger.removeHandler(_h)
        _mne_logger.propagate = False
        _mne_handler = _MNELogHandler(model.log)
        _mne_handler.setFormatter(logging.Formatter("%(message)s"))
        _mne_logger.addHandler(_mne_handler)

        # restore settings
        settings = read_settings()
        self.model.set_memory_limit_mb(settings["dataset_memory_limit_mb"])
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
        # some styles do not emit PaletteChange on startup
        QApplication.sendEvent(self, QEvent(QEvent.Type.PaletteChange))

        self.all_actions = {}  # contains all actions

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        self.all_actions["open_file"] = file_menu.addAction(
            QIcon.fromTheme("open-file"),
            "&Open...",
            self.open_data,
            QKeySequence.StandardKey.Open,
        )
        self.recent_menu = file_menu.addMenu(
            QIcon.fromTheme("open-recent"), "Open Recent"
        )
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.all_actions["close_file"] = file_menu.addAction(
            QIcon.fromTheme("close-file"),
            "&Close",
            self.model.remove_data,
            QKeySequence.StandardKey.Close,
        )
        self.all_actions["close_all"] = file_menu.addAction(
            QIcon.fromTheme("close-all"), "Close All", self.close_all
        )
        file_menu.addSeparator()
        self.export_menu = file_menu.addMenu(QIcon.fromTheme("export"), "Export")
        for ext, description in writers.items():
            action = "export_data" + ext.replace(".", "_")
            self.all_actions[action] = self.export_menu.addAction(
                f"{ext[1:].upper()} ({description[1]})...",
                partial(self.export_file, model.export_data, "Export data", "*" + ext),
            )
        file_menu.addSeparator()
        self.all_actions["xdf_metadata"] = file_menu.addAction(
            QIcon.fromTheme("xdf-metadata"),
            "Show XDF Metadata",
            self.xdf_metadata,
        )
        self.all_actions["xdf_chunks"] = file_menu.addAction(
            QIcon.fromTheme("xdf-chunks"), "Inspect XDF Chunks...", self.xdf_chunks
        )
        file_menu.addSeparator()
        self.all_actions["settings"] = file_menu.addAction(
            QIcon.fromTheme("settings"),
            "Settings...",
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Comma),
            self.settings,
        )
        file_menu.addSeparator()
        self.all_actions["quit"] = file_menu.addAction(
            QIcon.fromTheme("quit"),
            "&Quit",
            self.close,
            QKeySequence.StandardKey.Quit,
        )

        channels_menu = self.menuBar().addMenu("&Channels")
        self.all_actions["pick_chans"] = channels_menu.addAction(
            QIcon.fromTheme("pick-chans"), "P&ick Channels...", self.pick_channels
        )
        self.all_actions["rename_channels"] = channels_menu.addAction(
            QIcon.fromTheme("rename-channels"),
            "Rename Channels...",
            self.rename_channels,
        )
        self.all_actions["chan_props"] = channels_menu.addAction(
            QIcon.fromTheme("chan-props"),
            "Channel &Properties...",
            self.channel_properties,
        )
        channels_menu.addSeparator()
        self.all_actions["set_montage"] = channels_menu.addAction(
            QIcon.fromTheme("plot-locations"), "Set &Montage...", self.set_montage
        )
        self.all_actions["clear_montage"] = channels_menu.addAction(
            QIcon.fromTheme("clear-montage"),
            "Clear Montage",
            self.clear_montage,
        )
        channels_menu.addSeparator()
        self.all_actions["change_ref"] = channels_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Change &Reference...",
            self.change_reference,
        )
        channels_menu.addSeparator()
        self.all_actions["import_bads"] = channels_menu.addAction(
            QIcon.fromTheme("import"),
            "Import Bad Channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels", "*.csv"),
        )
        self.all_actions["export_bads"] = channels_menu.addAction(
            QIcon.fromTheme("export"),
            "Export &Bad Channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels", "*.csv"),
        )
        self.all_actions["interpolate_bads"] = channels_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Interpolate Bad Channels",
            self.interpolate_bads,
        )
        channels_menu.addSeparator()
        self.all_actions["channel_stats"] = channels_menu.addAction(
            QIcon.fromTheme("channel-stats"),
            "&Channel Statistics",
            self.show_channel_stats,
        )

        events_menu = self.menuBar().addMenu("&Markers")
        self.all_actions["annotations"] = events_menu.addAction(
            QIcon.fromTheme("edit"),
            "Edit &Annotations...",
            self.edit_annotations,
        )
        self.all_actions["annotation_colors"] = events_menu.addAction(
            QIcon.fromTheme("annotation-colors"),
            "Annotation &Colors...",
            self.set_annotation_colors,
        )
        self.all_actions["import_annotations"] = events_menu.addAction(
            QIcon.fromTheme("import"),
            "Import Annotations...",
            self.import_annotations,
        )
        self.all_actions["export_annotations"] = events_menu.addAction(
            QIcon.fromTheme("export"),
            "Export &Annotations...",
            self.export_annotations,
        )
        events_menu.addSeparator()
        self.all_actions["events"] = events_menu.addAction(
            QIcon.fromTheme("edit"),
            "Edit &Events...",
            self.edit_events,
        )
        self.all_actions["import_events"] = events_menu.addAction(
            QIcon.fromTheme("import"),
            "Import Events...",
            lambda: self.import_file(
                model.import_events, "Import events", "*.csv *.fif"
            ),
        )
        self.all_actions["export_events"] = events_menu.addAction(
            QIcon.fromTheme("export"),
            "Export &Events...",
            lambda: self.export_file(model.export_events, "Export events", "*.csv"),
        )
        events_menu.addSeparator()
        self.all_actions["find_events"] = events_menu.addAction(
            QIcon.fromTheme("find-events"), "Find &Events...", self.find_events
        )
        self.all_actions["events_from_annotations"] = events_menu.addAction(
            QIcon.fromTheme("events-from-annotations"),
            "Events from Annotations",
            self.events_from_annotations,
        )
        self.all_actions["annotations_from_events"] = events_menu.addAction(
            QIcon.fromTheme("annotations-from-events"),
            "Annotations from Events...",
            self.annotations_from_events,
        )

        plot_menu = self.menuBar().addMenu("&Plot")
        self.all_actions["plot_data"] = plot_menu.addAction(
            QIcon.fromTheme("plot-data"),
            "Plot &Data",
            self.plot_data,
        )
        self.all_actions["plot_psd"] = plot_menu.addAction(
            QIcon.fromTheme("plot-psd"),
            "Plot &PSD...",
            self.plot_psd,
        )
        plot_menu.addSeparator()
        self.all_actions["plot_locations"] = plot_menu.addAction(
            QIcon.fromTheme("plot-locations"),
            "Plot &Channel Locations",
            self.plot_locations,
        )
        plot_menu.addSeparator()
        self.all_actions["plot_erds"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot &ERDS Maps...",
            self.plot_erds,
        )
        self.all_actions["plot_erds_topomaps"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot ERDS Topomaps...",
            self.plot_erds_topomaps,
        )
        plot_menu.addSeparator()
        self.all_actions["plot_evoked"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot Evoked...",
            self.plot_evoked,
        )
        self.all_actions["plot_evoked_comparison"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot Evoked Comparison...",
            self.plot_evoked_comparison,
        )
        self.all_actions["plot_evoked_topomaps"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot Evoked Topomaps...",
            self.plot_evoked_topomaps,
        )
        plot_menu.addSeparator()
        self.all_actions["plot_ica_components"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot ICA &Components",
            self.plot_ica_components,
        )
        self.all_actions["plot_ica_sources"] = plot_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "Plot ICA &Sources",
            self.plot_ica_sources,
        )

        process_menu = self.menuBar().addMenu("&Process")
        self.all_actions["filter"] = process_menu.addAction(
            QIcon.fromTheme("filter-data"), "&Filter Data...", self.filter_data
        )
        process_menu.addSeparator()
        self.all_actions["crop"] = process_menu.addAction(
            QIcon.fromTheme("crop"), "&Crop Data...", self.crop
        )
        self.all_actions["append_data"] = process_menu.addAction(
            QIcon.fromTheme("append-data"), "Appen&d Data...", self.append_data
        )
        process_menu.addSeparator()
        self.all_actions["run_ica"] = process_menu.addAction(
            QIcon.fromTheme("run-ica"), "Run &ICA...", self.run_ica
        )
        self.all_actions["label_ica"] = process_menu.addAction(
            QIcon.fromTheme("label-ica"), "Label &ICs...", self.label_ica
        )
        self.all_actions["apply_ica"] = process_menu.addAction(
            QIcon.fromTheme("apply-ica"), "Apply &ICA", self.apply_ica
        )
        self.all_actions["import_ica"] = process_menu.addAction(
            QIcon.fromTheme("import"),
            "Import &ICA...",
            lambda: self.open_file(model.import_ica, "Import ICA", "*.fif *.fif.gz"),
        )
        self.all_actions["export_ica"] = process_menu.addAction(
            QIcon.fromTheme("export"),
            "Export ICA...",
            lambda: self.export_file(model.export_ica, "Export ICA", "*.fif *.fif.gz"),
        )
        process_menu.addSeparator()
        self.all_actions["pipeline_editor"] = process_menu.addAction(
            QIcon.fromTheme("pipeline-editor"),
            "Pipeline...",
            self.open_pipeline_editor,
        )

        epochs_menu = self.menuBar().addMenu("Ep&ochs")
        self.all_actions["epoch_data"] = epochs_menu.addAction(
            QIcon.fromTheme("epoch-data"), "Create Epochs...", self.epoch_data
        )
        self.all_actions["drop_bad_epochs"] = epochs_menu.addAction(
            QIcon.fromTheme("drop-bad-epochs"),
            "Drop Bad Epochs...",
            self.drop_bad_epochs,
        )
        self.all_actions["artifact_detection"] = epochs_menu.addAction(
            QIcon.fromTheme("artifact-detection"),
            "Detect &Artifacts...",
            self.artifact_detection,
        )

        view_menu = self.menuBar().addMenu("&View")
        self.all_actions["history"] = view_menu.addAction(
            QIcon.fromTheme("history"),
            "&Log...",
            self.show_log,
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Y),
        )
        self.all_actions["toolbar"] = view_menu.addAction(
            "&Toolbar", self._toggle_toolbar
        )
        self.all_actions["toolbar"].setCheckable(True)
        self.all_actions["statusbar"] = view_menu.addAction(
            "&Statusbar", self._toggle_statusbar
        )
        self.all_actions["statusbar"].setCheckable(True)
        if sys.platform != "darwin":
            self.all_actions["menubar"] = view_menu.addAction(
                QIcon.fromTheme("placeholder"),
                "&Menubar",
                self._toggle_menubar,
                QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_M),
            )
            self.all_actions["menubar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.all_actions["about"] = help_menu.addAction(
            QIcon.fromTheme("info"), "&About", self.show_about
        )
        self.all_actions["about_qt"] = help_menu.addAction(
            QIcon.fromTheme("info"), "About &Qt", self.show_about_qt
        )
        if sys.platform != "darwin":
            help_menu.addSeparator()
        self.all_actions["check_updates"] = help_menu.addAction(
            QIcon.fromTheme("check-updates"),
            "Check for &Updates",
            self.show_check_for_updates,
        )
        if sys.platform == "darwin":
            self.all_actions["check_updates"].setMenuRole(
                QAction.MenuRole.ApplicationSpecificRole
            )
        help_menu.addSeparator()
        self.all_actions["documentation"] = help_menu.addAction(
            QIcon.fromTheme("placeholder"),
            "&Documentation",
            self.show_documentation,
        )
        # actions that are always enabled
        self.always_enabled = [
            "open_file",
            "about",
            "about_qt",
            "check_updates",
            "quit",
            "xdf_chunks",
            "toolbar",
            "statusbar",
            "menubar",
            "settings",
            "documentation",
            "history",
            "annotation_colors",
        ]

        # set up toolbar
        self.toolbar = self.addToolBar("toolbar")
        self.toolbar.setObjectName("toolbar")
        self.toolbar.addAction(self.all_actions["open_file"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.all_actions["chan_props"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.all_actions["plot_data"])
        self.toolbar.addAction(self.all_actions["plot_psd"])
        self.toolbar.addAction(self.all_actions["plot_locations"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.all_actions["filter"])
        self.toolbar.addAction(self.all_actions["find_events"])
        self.toolbar.addAction(self.all_actions["epoch_data"])
        self.toolbar.addAction(self.all_actions["run_ica"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.all_actions["pipeline_editor"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.all_actions["settings"])
        self.toolbar.setMovable(False)
        # hamburger menu button (Windows/Linux only)
        if sys.platform != "darwin":
            hamburger_spacer = QWidget()
            hamburger_spacer.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self._hamburger_spacer_action = self.toolbar.addWidget(hamburger_spacer)
            self._hamburger_button = QToolButton()
            self._hamburger_button.setIcon(QIcon.fromTheme("hamburger-menu"))
            self._hamburger_button.setToolTip("Menu")
            hamburger_popup = QMenu(self)
            self._menu_style = MenuPaddingStyle()
            hamburger_popup.setStyle(self._menu_style)
            for menu_action in self.menuBar().actions():
                if (submenu := menu_action.menu()) is not None:
                    hamburger_popup.addMenu(submenu)
            self._hamburger_button.setMenu(hamburger_popup)
            self._hamburger_button.setPopupMode(
                QToolButton.ToolButtonPopupMode.InstantPopup
            )
            self._hamburger_action = self.toolbar.addWidget(self._hamburger_button)
            hamburger_enabled = not settings["show_menubar"]
            self._hamburger_spacer_action.setVisible(hamburger_enabled)
            self._hamburger_action.setVisible(hamburger_enabled)
            self.menuBar().setVisible(not hamburger_enabled)
            self.all_actions["menubar"].setChecked(not hamburger_enabled)
        self.setUnifiedTitleAndToolBarOnMac(True)
        if sys.platform == "darwin":
            self.toolbar.setStyleSheet("""
                QToolButton:hover {
                    background: rgba(128, 128, 128, 0.2);
                    border-radius: 4px;
                }
                QToolButton:pressed {
                    background: rgba(128, 128, 128, 0.35);
                    border-radius: 4px;
                }
            """)
        if settings["toolbar"]:
            self.toolbar.show()
            self.all_actions["toolbar"].setChecked(True)
        else:
            self.toolbar.hide()
            self.all_actions["toolbar"].setChecked(False)

        # set up data model for sidebar (pipeline tree)
        self.sidebar = PipelineTreeWidget(self)
        self.sidebar.hide()
        self.sidebar.datasetSelected.connect(self._update_data)
        self.sidebar.datasetRenamed.connect(self._sidebar_edit_event)
        self.sidebar.showHistoryRequested.connect(self.show_history_for_dataset)
        self.sidebar.savePipelineRequested.connect(self.save_pipeline_for_dataset)
        self.sidebar.exportHistoryRequested.connect(self.export_history_for_dataset)
        self.sidebar.showDetailsRequested.connect(self.show_dataset_details)
        self.sidebar.applyPipelineRequested.connect(self.apply_pipeline_for_dataset)

        self.splitter = QSplitter()
        self.splitter.setObjectName("main_splitter")
        self.splitter.addWidget(self.sidebar)

        self.infowidget = QStackedWidget()
        info_widget = InfoWidget()
        self.infowidget.addWidget(info_widget)
        emptywidget = EmptyWidget(
            itemgetter("open_file", "history", "settings")(self.all_actions)
        )
        self.infowidget.addWidget(emptywidget)
        self.splitter.addWidget(self.infowidget)
        QTimer.singleShot(0, lambda: self._set_splitter_ratio(settings["splitter"]))
        self.setCentralWidget(self.splitter)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        if settings["statusbar"]:
            self.statusBar().show()
            self.all_actions["statusbar"].setChecked(True)
        else:
            self.statusBar().hide()
            self.all_actions["statusbar"].setChecked(False)

        self.setAcceptDrops(True)
        self.data_changed()

    def _excepthook(self, type, value, traceback_):
        from mnelab import IS_DEV_VERSION

        if type is KeyboardInterrupt and IS_DEV_VERSION:
            self.close()
            return
        exception_text = str(value)
        traceback_text = "".join(traceback.format_exception(type, value, traceback_))
        print(traceback_text, file=sys.stderr)
        ErrorMessageBox(self, exception_text, "", traceback_text).show()

    def _sidebar_edit_event(self, dataset_index, new_name):
        """
        Triggered when a data set in the sidebar is renamed.

        Parameters
        ----------
        dataset_index : int
            Index of the renamed dataset in model.data.
        new_name : str
            The new name entered by the user.
        """
        if 0 <= dataset_index < len(self.model.data):
            self.model.data[dataset_index]["name"] = new_name

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
        # update sidebar (pipeline tree)
        if len(self.model.data) > 0:
            self.sidebar.show()
            self.sidebar.populate(self.model.get_pipeline_tree(), self.model.index)
            self.sidebar.set_badges_visible(read_settings("dtype_badges"))
        else:
            self.sidebar.hide()

        # update info widget
        if self.model.data:
            self.infowidget.setCurrentIndex(0)
            self.infowidget.widget(0).set_values(self.model.get_info())
        else:
            self.infowidget.setCurrentIndex(1)

        # update status bar
        if self.model.data:
            memory = self.model.memory_usage()
            loaded_mb = memory["loaded_mb"]
            limit_mb = memory["limit_mb"]
            unloaded = memory["unloaded_count"]
            if limit_mb > 0:
                status = (
                    f"Memory: {loaded_mb:.1f} / {limit_mb} MB "
                    f"({memory['available_mb']:.1f} MB free"
                )
                if memory["over_limit_mb"]:
                    status += f", {memory['over_limit_mb']:.1f} MB over limit"
                if unloaded:
                    status += f", {unloaded} unloaded"
                status += ")"
                self.status_label.setText(status)
            else:
                status = f"Memory: {loaded_mb:.1f} MB"
                if unloaded:
                    status += f" ({unloaded} unloaded)"
                self.status_label.setText(status)
        else:
            self.status_label.clear()

        # toggle actions
        has_data = len(self.model) > 0
        current_loaded = has_data and self.model.is_loaded(self.model.index)

        for name, action in self.all_actions.items():  # toggle
            if name not in self.always_enabled:
                action.setEnabled(current_loaded)

        if has_data:
            self.all_actions["close_file"].setEnabled(True)
            self.all_actions["close_all"].setEnabled(True)
            self.all_actions["pipeline_editor"].setEnabled(True)

        if current_loaded:  # toggle if specific conditions are met
            bads = bool(self.model.current["data"].info["bads"])
            self.all_actions["export_bads"].setEnabled(bads)
            events = len(self.model.current["events"]) > 0
            self.all_actions["export_events"].setEnabled(events)
            if self.model.current["dtype"] == "raw":
                annot = bool(self.model.current["data"].annotations)
            else:
                annot = False
            self.all_actions["export_annotations"].setEnabled(annot)
            self.all_actions["annotations"].setEnabled(True)
            locations = count_locations(self.model.current["data"].info)
            self.all_actions["plot_locations"].setEnabled(bool(locations))
            ica = bool(self.model.current["ica"])
            self.all_actions["label_ica"].setEnabled(
                ica and self.model.current["montage"] is not None
            )
            self.all_actions["apply_ica"].setEnabled(ica)
            self.all_actions["export_ica"].setEnabled(ica)
            self.all_actions["plot_erds"].setEnabled(
                self.model.current["dtype"] == "epochs"
            )
            self.all_actions["plot_erds_topomaps"].setEnabled(
                bool(locations) and self.model.current["dtype"] == "epochs"
            )
            self.all_actions["plot_evoked"].setEnabled(
                self.model.current["dtype"] == "epochs"
            )
            self.all_actions["plot_evoked_comparison"].setEnabled(
                self.model.current["dtype"] == "epochs"
            )
            self.all_actions["plot_evoked_topomaps"].setEnabled(
                bool(locations) and self.model.current["dtype"] == "epochs"
            )
            self.all_actions["plot_ica_components"].setEnabled(ica and bool(locations))
            self.all_actions["plot_ica_sources"].setEnabled(ica)
            self.all_actions["interpolate_bads"].setEnabled(bool(locations) and bads)
            self.all_actions["events"].setEnabled(True)
            self.all_actions["events_from_annotations"].setEnabled(annot)
            self.all_actions["annotations_from_events"].setEnabled(events)
            self.all_actions["find_events"].setEnabled(
                self.model.current["dtype"] == "raw"
            )
            self.all_actions["epoch_data"].setEnabled(
                events and self.model.current["dtype"] == "raw"
            )
            self.all_actions["channel_stats"].setEnabled(
                self.model.current["dtype"] == "raw"
            )
            self.all_actions["drop_bad_epochs"].setEnabled(
                events and self.model.current["dtype"] == "epochs"
            )
            self.all_actions["artifact_detection"].setEnabled(
                events and self.model.current["dtype"] == "epochs"
            )
            self.all_actions["clear_montage"].setEnabled(
                self.model.current["montage"] is not None
            )
            self.all_actions["crop"].setEnabled(self.model.current["dtype"] == "raw")
            append = bool(self.model.get_compatibles())
            self.all_actions["append_data"].setEnabled(
                append and (self.model.current["dtype"] in ("raw", "epochs"))
            )
            self.all_actions["xdf_metadata"].setEnabled(
                self.model.current["ftype"] in ["XDF", "XDFZ", "XDF.GZ"]
            )
            # disable unsupported exporters for epochs (all must support raw)
            if self.model.current["dtype"] == "epochs":
                for ext, description in writers.items():
                    action = "export_data" + ext.replace(".", "_")
                    if "epoch" in description[2]:
                        self.all_actions[action].setEnabled(True)
                    else:
                        self.all_actions[action].setEnabled(False)
        # add to recent files
        if has_data and self.model.current["fname"] is not None:
            self._add_recent(self.model.current["fname"])

    def open_data(self, fname=None):
        """Open raw file."""
        if fname is None:
            # getOpenFileNames returns a tuple (filenames, selected_filter)
            fnames, _ = QFileDialog.getOpenFileNames(
                self, "Open raw", self._get_last_dir()
            )
        else:
            fnames = [fname]
        for fname in fnames:
            if not (Path(fname).is_file() or Path(fname).is_dir()):
                self._remove_recent(fname)
                QMessageBox.critical(
                    self, "File does not exist", f"File {fname} does not exist anymore."
                )
                return

            self._set_last_dir(fname)
            ext = "".join(Path(fname).suffixes)

            if any(ext.endswith(e) for e in (".xdf", ".xdfz", ".xdf.gz")):  # XDF
                rows = [
                    [
                        s["stream_id"],
                        s["name"],
                        s["type"],
                        s["channel_count"],
                        s["channel_format"],
                        s["nominal_srate"],
                    ]
                    for s in resolve_streams(fname)
                ]
                dialog = XDFStreamsDialog(
                    self,
                    rows,
                    fname=fname,
                    selected=None,
                )
                if dialog.exec():
                    fs_new = None
                    gap_threshold = 0.0
                    if dialog.resample.isChecked():
                        fs_new = float(dialog.fs_new.value())
                        if dialog.gap_threshold_checkbox.isChecked():
                            gap_threshold = float(dialog.gap_threshold.value())
                    self.model.load(
                        fname,
                        stream_ids=dialog.selected_streams,
                        marker_ids=dialog.selected_markers,
                        prefix_markers=dialog.prefix_markers,
                        fs_new=fs_new,
                        gap_threshold=gap_threshold,
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
            elif ext == ".vhdr":
                dialog = BrainVisionDialog(self)
                if dialog.exec():
                    self.model.load(
                        fname, ignore_marker_types=dialog.ignore_marker_types
                    )
            elif ext in (".bvrh", ".bvrd", ".bvrm", ".bvri"):
                try:
                    header = read_bvrf_header(Path(fname).with_suffix(".bvrh"))
                    if header["n_participants"] > 1:
                        # get participant IDs
                        participants = [
                            p["Id"] for p in header["yaml_header"]["Participants"]
                        ]
                        dialog = BVRFDialog(self, participants)
                        if dialog.exec():
                            selected = dialog.selected_participants
                            if dialog.create_separate:
                                data_dict = read_raw(
                                    fname, participants=selected, split=True
                                )
                                for pid, raw in data_dict.items():
                                    name, _ = split_name_ext(fname)
                                    self.model.load_raw(
                                        raw, fname, name=f"{name} ({pid})"
                                    )
                            else:
                                self.model.load(
                                    fname, participants=selected, split=False
                                )
                    else:
                        # single participant, load directly
                        self.model.load(fname)
                except Exception as e:
                    QMessageBox.critical(self, "Error loading BVRF file", str(e))
            else:  # all other file formats
                try:
                    self.model.load(fname)
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))
                except ValueError as e:
                    QMessageBox.critical(self, "Unknown file type", str(e))

    def open_file(self, f, text, ffilter="*"):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, text, self._get_last_dir(), ffilter)[
            0
        ]
        if fname:
            self._set_last_dir(fname)
            f(fname)

    def xdf_chunks(self):
        """Inspect XDF chunks."""
        fname = QFileDialog.getOpenFileName(
            self, "Select XDF file", self._get_last_dir(), "*.xdf *.xdfz *.xdf.gz"
        )[0]
        if fname:
            self._set_last_dir(fname)
            chunks = list_chunks(fname)
            dialog = XDFChunksDialog(self, chunks, fname)
            dialog.exec()

    def export_file(self, f, text, ffilter="*"):
        """Export to file."""
        fname = QFileDialog.getSaveFileName(self, text, self._get_last_dir())[0]
        if fname:
            self._set_last_dir(fname)
            exts = [ext.replace("*", "") for ext in ffilter.split()]
            for ext in exts:
                if fname.endswith(ext):
                    return f(fname)
            return f(fname + exts[0])

    def import_file(self, f, text, ffilter="*"):
        """Import file."""
        fname = QFileDialog.getOpenFileName(self, text, self._get_last_dir(), ffilter)[
            0
        ]
        if fname:
            self._set_last_dir(fname)
            try:
                f(fname)
            except LabelsNotFoundError as e:
                QMessageBox.critical(self, "Channel labels not found", str(e))
            except InvalidAnnotationsError as e:
                QMessageBox.critical(self, "Invalid annotations", str(e))

    def export_annotations(self):
        """Export annotations, optionally filtered by type."""
        all_types = sorted(set(self.model.current["data"].annotations.description))
        fname = QFileDialog.getSaveFileName(
            self, "Export annotations", self._get_last_dir(), "*.csv"
        )[0]
        if not fname:
            return
        self._set_last_dir(fname)
        if len(all_types) > 1:
            dialog = AnnotationTypesDialog(
                self,
                all_types,
                title="Export annotations",
                label="Select annotation types to export:",
            )
            if not dialog.exec():
                return
            types = dialog.selected_types
        else:
            types = all_types
        if not fname.endswith(".csv"):
            fname += ".csv"
        self.model.export_annotations(fname, types=types)

    def import_annotations(self):
        """Import annotations, optionally filtered by type."""
        fname = QFileDialog.getOpenFileName(
            self, "Import annotations", self._get_last_dir(), "*.csv"
        )[0]
        if not fname:
            return
        self._set_last_dir(fname)
        try:
            all_types, integer = get_annotation_types_from_file(fname)
        except Exception as e:
            QMessageBox.critical(self, "Invalid annotations file", str(e))
            return
        # handle missing type column (ask the user for a description)
        if all_types is None:
            desc, ok = QInputDialog.getText(
                self,
                "Import annotations",
                "The file has no type column. Enter a description for all annotations:",
                text="annotation",
            )
            if not ok:
                return
            description = desc.strip() or "annotation"
            types = None
        else:
            description = None
            if len(all_types) > 1:
                dialog = AnnotationTypesDialog(
                    self,
                    all_types,
                    title="Import annotations",
                    label="Select annotation types to import:",
                )
                if not dialog.exec():
                    return
                types = dialog.selected_types
            else:
                types = all_types
        # check if all values look like integers (may be in samples)
        unit = "seconds"
        try:
            if integer:
                sfreq = self.model.current["data"].info["sfreq"]
                reply = QMessageBox.question(
                    self,
                    "Import annotations",
                    f"All onset and duration values are integers. They may be in "
                    f"samples (fs = {sfreq:.1f}\u202fHz) rather than "
                    f"seconds.\n\nImport as samples?",
                )
                if reply == QMessageBox.StandardButton.Yes:
                    unit = "samples"
        except Exception:
            pass
        try:
            self.model.import_annotations(
                fname,
                types=types if description is None else None,
                description=description,
                unit=unit,
            )
        except InvalidAnnotationsError as e:
            QMessageBox.critical(self, "Invalid annotations", str(e))

    def _set_splitter_ratio(self, ratio):
        total = sum(self.splitter.sizes())
        left = round(total * ratio)
        self.splitter.setSizes([left, total - left])

    def _get_last_dir(self):
        last_dir = read_settings("last_dir")
        return last_dir if Path(last_dir).is_dir() else str(Path.home())

    def _set_last_dir(self, fname):
        write_settings(last_dir=str(Path(fname).parent))

    def close_all(self):
        """Close all currently open data sets."""
        msg = QMessageBox.question(self, "Close all data sets", "Close all data sets?")
        if msg == QMessageBox.StandardButton.Yes:
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
                new_label = dialog.model.item(i, 1).data(Qt.ItemDataRole.DisplayRole)
                old_label = info["ch_names"][i]
                if new_label != old_label:
                    renamed[old_label] = new_label
                new_type = (
                    dialog.model.item(i, 2).data(Qt.ItemDataRole.DisplayRole).lower()
                )
                old_type = channel_type(info, i).lower()
                if new_type != old_type:
                    types[new_label] = new_type
                if dialog.model.item(i, 3).checkState() == Qt.CheckState.Checked:
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
            montage = dialog.montage
            ch_names = self.model.current["data"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.montage.ch_names):
                self.model.set_montage(
                    montage,
                    match_case=dialog.match_case.isChecked(),
                    match_alias=dialog.match_alias.isChecked(),
                    on_missing="ignore"
                    if dialog.ignore_missing.isChecked()
                    else "raise",
                )
            else:
                QMessageBox.critical(
                    self,
                    "No matching channel names",
                    "Channel names defined in the montage do not match any channel name"
                    " in the data.",
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
                data = dialog.table.item(i, 0).data(Qt.ItemDataRole.DisplayRole)
                onset.append(float(data) / fs)
                data = dialog.table.item(i, 1).data(Qt.ItemDataRole.DisplayRole)
                duration.append(float(data) / fs)
                data = dialog.table.item(i, 2).data(Qt.ItemDataRole.DisplayRole)
                description.append(data)
            self.model.set_annotations(onset, duration, description)

    def set_annotation_colors(self):
        """Open dialog to manage custom annotation colors."""
        colors = read_settings("annotation_colors")
        dialog = AnnotationColorsDialog(self, colors)
        if dialog.exec():
            write_settings(annotation_colors=dialog.annotation_colors)

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
            self.model.crop(max(dialog.start, 0), min(dialog.stop, stop))

    def append_data(self):
        """Concatenate raw data objects to current one."""
        compatibles = self.model.get_compatibles()
        dialog = AppendDialog(self, compatibles)
        if dialog.exec():
            self.model.append_data(dialog.selected_idx)

    def plot_data(self):
        """Plot data."""
        # self.bad is needed to update history if bad channels are selected in the
        # interactive plot window (see also self.eventFilter)
        self.bads = self.model.current["data"].info["bads"]
        events = self.model.current["events"]
        nchan = self.model.current["data"].info["nchan"]
        nchan = min(nchan, read_settings("max_channels"))
        duration = read_settings("duration")
        annotation_colors = read_settings("annotation_colors") or None

        fig = self.model.current["data"].plot(
            events=events,
            n_channels=nchan,
            duration=duration,
            title=self.model.current["name"],
            clipping=None,
            annotation_colors=annotation_colors,
            show=False,
        )
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
        fs = self.model.current["data"].info["sfreq"]
        dialog = PSDDialog(
            self, fmin=0, fmax=fs / 2, montage=self.model.current["montage"] is not None
        )

        if dialog.exec():
            psd_kwds = {"fmin": dialog.fmin, "fmax": dialog.fmax}
            plot_kwds = {
                "spatial_colors": dialog.spatial_colors,
                "exclude": dialog.exclude,
            }
            fig = (
                self.model.current["data"]
                .compute_psd(**psd_kwds)
                .plot(show=False, **plot_kwds)
            )
            psd_kwds = ", ".join(f"{key}={value}" for key, value in psd_kwds.items())
            plot_kwds = ", ".join(
                f"{key}={value!r}" for key, value in plot_kwds.items()
            )
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
        figs = self.model.current["ica"].plot_components(
            inst=self.model.current["data"]
        )
        # refresh UI after closing the plots to reflect changes in ICA exclusions
        for fig in figs:
            fig.canvas.mpl_connect("close_event", lambda _: self.data_changed())

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
                QMetaObject.invokeMethod(
                    calc, "accept", Qt.ConnectionType.QueuedConnection
                )

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
                        float(t.strip())
                        for t in dialog.topomaps_timelist.text().split(",")
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
        if have["python-picard"]:
            methods.insert(0, "Picard")
        if have["scikit-learn"]:
            methods.append("FastICA")

        data = self.model.current["data"]
        dialog = RunICADialog(self, data.info["nchan"], data.info["highpass"], methods)

        if dialog.exec():
            calc = CalcDialog(self, "Calculating ICA", "Calculating ICA...")

            method = dialog.method.currentText().lower()
            reject_by_annotation = dialog.exclude_bad_segments.isChecked()
            n_components = dialog.n_components.value() or None

            fit_params = {}
            if dialog.extended.isEnabled():
                fit_params["extended"] = dialog.extended.isChecked()
            if dialog.ortho.isEnabled():
                fit_params["ortho"] = dialog.ortho.isChecked()

            ica = mne.preprocessing.ICA(
                method=method,
                n_components=n_components,
                fit_params=fit_params,
                random_state=97,
            )

            pool = mp.Pool(processes=1)

            def callback(x):
                QMetaObject.invokeMethod(
                    calc, "accept", Qt.ConnectionType.QueuedConnection
                )

            res = pool.apply_async(
                func=ica.fit,
                args=(self.model.current["data"],),
                kwds={"reject_by_annotation": reject_by_annotation},
                callback=callback,
            )
            pool.close()

            if not calc.exec():
                pool.terminate()
                print("ICA calculation aborted...")
            else:
                self.model.run_ica(
                    method=method,
                    n_components=n_components,
                    reject_by_annotation=reject_by_annotation,
                    fit_params=fit_params,
                    random_state=97,
                    _fitted_ica=res.get(timeout=1),
                )

    def apply_ica(self):
        """Apply current fitted ICA."""
        self.model.apply_ica()

    def label_ica(self):
        """Label ICA components."""
        data = self.model.current["data"]
        ica = self.model.current["ica"]
        probs = self.model.get_iclabels()

        dialog = ICLabelDialog(self, data, ica, probs, exclude=ica.exclude)
        if dialog.exec():
            exclude_indices = dialog.get_excluded_indices()
            exclude_indices = sorted(int(x) for x in exclude_indices)
            if exclude_indices != sorted(int(x) for x in ica.exclude):
                self.model.set_ica_exclude(exclude_indices)

    def interpolate_bads(self):
        """Interpolate bad channels."""
        try:
            self.model.interpolate_bads()
        except ValueError as e:
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
            self.model.filter(dialog.lower, dialog.upper, dialog.notch)

    def find_events(self):
        info = self.model.current["data"].info

        # use first stim channel as default in dialog
        default_stim = 0
        for i in range(info["nchan"]):
            if channel_type(info, i) == "stim":
                default_stim = i
                break
        ftype = self.model.current["ftype"]
        dialog = FindEventsDialog(
            self, info["ch_names"], default_stim, mask_enabled=ftype == "BDF"
        )
        if dialog.exec():
            stim_channel = dialog.stimchan.currentText()
            consecutive = dialog.consecutive.currentText().lower()
            if consecutive == "true":
                consecutive = True
            elif consecutive == "false":
                consecutive = False
            initial_event = dialog.initial_event.isChecked()
            mask = (
                dialog.mask_value.value() if dialog.mask_enabled.isChecked() else None
            )
            min_dur = dialog.minduredit.value()
            shortest_event = dialog.shortesteventedit.value()
            self.model.find_events(
                stim_channel=stim_channel,
                consecutive=consecutive,
                initial_event=initial_event,
                mask=mask,
                min_duration=min_dur,
                shortest_event=shortest_event,
            )

    def events_from_annotations(self):
        self.model.events_from_annotations()

    def annotations_from_events(self):
        event_counts = mne.count_events(self.model.current["events"])
        annotations = sorted(set(self.model.current["data"].annotations.description))

        dialog = AnnotationsIntervalDialog(self, event_counts, annotations)
        if dialog.exec():
            if dialog.annotations_from_events():
                self.model.annotations_from_events()
            else:
                interval_data = dialog.event_to_event_data()
                try:
                    existing = self.model.current["data"].annotations
                    new = annotations_between_events(
                        events=self.model.current["events"],
                        sfreq=self.model.current["data"].info["sfreq"],
                        max_time=self.model.current["data"].times[-1],
                        orig_time=existing.orig_time,
                        **interval_data,
                    )
                    self.model.current["data"].set_annotations(existing + new)
                    self.data_changed()
                except Exception as e:
                    msgbox = ErrorMessageBox(
                        self,
                        "Could not create annotations from events",
                        str(e),
                        traceback.format_exc(),
                    )
                    msgbox.show()

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

            try:
                self.model.epoch_data(dialog.selected_events, tmin, tmax, baseline)
            except ValueError as e:
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
            self.model.drop_bad_epochs(reject, flat)

    def artifact_detection(self):
        """Apply artifact detection."""
        data = self.model.current["data"]

        dialog = ArtifactDetectionDialog(self, data)
        if dialog.exec():
            bad_epochs = dialog.get_bad_epochs()
            if not bad_epochs:
                return

            self.model.drop_detected_artifacts(bad_epochs)

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
            try:
                self.model.change_reference(add, ref)
            except ValueError as e:
                msgbox = ErrorMessageBox(
                    self,
                    "Error while changing references:",
                    str(e),
                    traceback.format_exc(),
                )
                msgbox.show()

    def show_log(self):
        """Show MNE log."""
        from mnelab.dialogs.history import LogDialog

        LogDialog(self, self.model.log).exec()

    def _open_pipeline_builder(self, pipeline, history=None, show_history=False):
        """Open the pipeline builder; apply the result if the user clicks Apply."""
        from mnelab.dialogs.pipeline_builder import PipelineBuilderDialog

        dialog = PipelineBuilderDialog(self, pipeline, history)
        if show_history:
            dialog.show_history_tab()
        if dialog.exec():
            self._confirm_and_apply_pipeline(dialog.get_pipeline())

    @Slot(int)
    def show_dataset_details(self, dataset_index):
        """Show details for a specific dataset in the lineage tree."""
        dialog = DatasetDetailsDialog(
            self,
            self.model.get_dataset_details(dataset_index),
        )
        dialog.datasetSelected.connect(self._update_data)
        dialog.exec()

    @Slot(int)
    def show_history_for_dataset(self, dataset_index):
        """Open the Pipeline dialog for a dataset with the History tab active."""
        pipeline = self.model.get_pipeline(dataset_index)
        history = self.model.get_history(dataset_index)
        self._open_pipeline_builder(pipeline, history, show_history=True)

    def show_channel_stats(self):
        """Show channel stats."""
        dialog = ChannelStats(self, self.model.current["data"])
        dialog.exec_()

    def show_about(self):
        """Show About dialog."""
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

    def show_check_for_updates(self):
        """Check GitHub for a newer MNELAB release."""
        try:
            req = Request(
                "https://api.github.com/repos/cbrnr/mnelab/releases/latest",
                headers={"User-Agent": "MNELAB"},
            )
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            latest = data["tag_name"].lstrip("v")
        except Exception:
            latest = None

        repo_url = "https://github.com/cbrnr/mnelab"
        repo_link = f'<a href="{repo_url}">{repo_url}</a>'
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Check for Updates")
        if latest is None:
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("Could not retrieve update information.")
            msg_box.setInformativeText(
                "Please check your internet connection and try again."
            )
        elif IS_DEV_VERSION:
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(f"You are running a development version ({__version__}).")
            msg_box.setInformativeText(
                f"The latest release is {latest}.<br><br>"
                f"Visit {repo_link} for more information."
            )
        else:

            def _version_tuple(v):
                parts = []
                for part in v.split("."):
                    try:
                        parts.append(int(part))
                    except ValueError:
                        break
                return tuple(parts)

            if _version_tuple(latest) > _version_tuple(__version__):
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText(
                    f"MNELAB {latest} is available (you have {__version__})."
                )
                msg_box.setInformativeText(
                    f"Visit {repo_link} to find download links for the latest release."
                )
            else:
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText(f"MNELAB {__version__} is the latest version.")
                msg_box.setInformativeText("No update is available.")
        msg_box.exec()

    def show_documentation(self):
        url = QUrl("https://mnelab.readthedocs.io/")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Open Url", "Could not open url")

    def settings(self):
        old_backend = read_settings("plot_backend")
        old_badges = read_settings("dtype_badges")
        old_menu_icons = read_settings("menu_icons")
        SettingsDialog(self, self.plot_backends).exec()
        new_backend = read_settings("plot_backend")
        new_badges = read_settings("dtype_badges")
        new_menu_icons = read_settings("menu_icons")
        new_memory_limit = read_settings("dataset_memory_limit_mb")
        if old_backend != new_backend:
            mne.viz.set_browser_backend(new_backend)
        if old_badges != new_badges:
            self.sidebar.set_badges_visible(new_badges)
        if old_menu_icons != new_menu_icons:
            QMessageBox.information(
                self,
                "Restart required",
                'The "Menu icons" setting will take effect after restarting MNELAB.',
            )
            self.model.set_memory_limit_mb(new_memory_limit)

    def save_pipeline_for_dataset(self, dataset_index):
        """Save the pipeline for a specific branch in the lineage tree."""
        if not self.model.has_replayable_pipeline(dataset_index):
            QMessageBox.information(
                self,
                "No replayable pipeline",
                "This branch has no replayable pipeline steps to save.",
            )
            return

        pipeline = self.model.get_pipeline(dataset_index)
        if pipeline is None or not pipeline.get("steps"):
            QMessageBox.information(
                self,
                "No pipeline steps",
                "This branch has no replayable pipeline steps to save.",
            )
            return

        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline", filter="MNELAB pipeline (*.mnepipe)"
        )
        if fname:
            if not fname.endswith(".mnepipe"):
                fname += ".mnepipe"
            try:
                self.model.save_pipeline(idx=dataset_index, path=fname)
            except ValueError as exc:
                QMessageBox.critical(self, "Pipeline error", str(exc))

    @Slot(int)
    def export_history_for_dataset(self, dataset_index):
        """Export Python history for a specific branch in the lineage tree."""
        dataset = self.model.data[dataset_index]
        default_name = f"{Path(dataset['name']).name or 'history'}-history.py"
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Export Branch History",
            default_name,
            "Python Files (*.py);;All Files (*)",
        )
        if fname:
            if not fname.endswith(".py"):
                fname += ".py"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(format_code("\n".join(self.model.get_history(dataset_index))))
                f.write("\n")

    def open_pipeline_editor(self):
        """Open the Pipeline dialog for the current dataset pipeline."""
        pipeline = (
            self.model.get_pipeline(self.model.index) if self.model.data else None
        )
        history = self.model.get_history(self.model.index) if self.model.data else None
        self._open_pipeline_builder(pipeline, history)

    @Slot(int)
    def apply_pipeline_for_dataset(self, dataset_index):
        """Open a .mnepipe file and apply it to a specific dataset."""
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open Pipeline", filter="MNELAB pipeline (*.mnepipe)"
        )
        if fname:
            self._apply_pipeline_from_path(fname, dataset_index)

    def _apply_pipeline_from_path(self, path, dataset_index=None):
        """Load a .mnepipe file and apply it to a dataset.

        Parameters
        ----------
        path :
            Path to the .mnepipe file.
        dataset_index :
            Model index of the target dataset. If None, uses the current dataset.
        """
        from mnelab.dialogs.pipeline import load_pipeline

        if not self.model.data:
            QMessageBox.information(
                self,
                "No dataset open",
                "Open a dataset first before applying a pipeline.",
            )
            return
        try:
            pipeline = load_pipeline(path)
        except (ValueError, KeyError) as e:
            QMessageBox.critical(self, "Invalid pipeline file", str(e))
            return
        if dataset_index is not None and dataset_index != self.model.index:
            old_index = self.model.index
            self.model.index = dataset_index
            self._confirm_and_apply_pipeline(pipeline)
            if self.model.index == dataset_index:
                self.model.index = old_index
            self.data_changed()
        else:
            self._confirm_and_apply_pipeline(pipeline)

    def _confirm_and_apply_pipeline(self, pipeline):
        """Show the pipeline compatibility dialog before applying a pipeline."""
        from mnelab.dialogs.pipeline import ApplyPipelineDialog
        from mnelab.widgets.pipeline_tree import _operation_label

        dialog = ApplyPipelineDialog(
            self,
            pipeline,
            self.model.current,
        )
        if dialog.exec():
            steps = pipeline.get("steps", [])
            progress_dialog = None
            if steps:
                progress_dialog = PipelineProgressDialog(self, len(steps))
                progress_dialog.show()
                QApplication.processEvents()

            def _review_step(step_index, step, execution_mode):
                label = _operation_label(step.get("operation"), step.get("params"))
                title = (
                    "Review checkpoint"
                    if execution_mode == "review"
                    else "Pipeline prompt"
                )
                reply = QMessageBox.question(
                    self,
                    title,
                    f"Pipeline step {step_index} requests a "
                    f"{execution_mode} checkpoint:\n\n{label}\n\nContinue?",
                )
                return reply == QMessageBox.StandardButton.Yes

            def _update_progress(step_index, step):
                if progress_dialog is None:
                    return
                progress_dialog.update_progress(step_index, step)
                QApplication.processEvents()

            try:
                self.model.apply_pipeline(
                    pipeline,
                    progress_callback=_update_progress,
                    is_cancelled=(
                        progress_dialog.wasCanceled
                        if progress_dialog is not None
                        else None
                    ),
                    review_callback=_review_step,
                )
            except PipelineCancelledError:
                return
            except (ValueError, AttributeError) as e:
                QMessageBox.critical(self, "Pipeline error", str(e))
            finally:
                if progress_dialog is not None:
                    progress_dialog.close()

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

    @Slot(int)
    def _update_data(self, dataset_index):
        """Update active dataset from pipeline tree selection.

        Parameters
        ----------
        dataset_index : int
            Index of the selected dataset in model.data.
        """
        if dataset_index != self.model.index:
            if (
                not self.model.is_overload_active()
                and not self.model.is_loaded(dataset_index)
                and self.model.can_reload(dataset_index)
            ):
                self.model.ensure_loaded(dataset_index)
            self.model.index = dataset_index
            self.data_changed()

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

    def _apply_hamburger_menu_setting(self, enabled):
        self.menuBar().setVisible(not enabled)
        self._hamburger_spacer_action.setVisible(enabled)
        self._hamburger_action.setVisible(enabled)
        write_settings(show_menubar=not enabled)

    @Slot()
    def _toggle_menubar(self):
        menubar_visible = self.menuBar().isVisible()
        self.menuBar().setVisible(not menubar_visible)
        hamburger_enabled = menubar_visible
        self._hamburger_spacer_action.setVisible(hamburger_enabled)
        self._hamburger_action.setVisible(hamburger_enabled)
        self.all_actions["menubar"].setChecked(not menubar_visible)
        write_settings(show_menubar=not hamburger_enabled)

    @Slot()
    def _toggle_statusbar(self):
        if self.statusBar().isHidden():
            self.statusBar().show()
        else:
            self.statusBar().hide()
        write_settings(statusbar=not self.statusBar().isHidden())

    def _plot_closed(self, event=None):
        self.data_changed()

    def event(self, event):
        if event.type() == QEvent.Type.Close:
            sizes = self.splitter.sizes()
            total = sum(sizes)
            kwargs = {"size": self.size(), "pos": self.pos()}
            if self.sidebar.isVisible() and total > 0:
                kwargs["splitter"] = sizes[0] / total
            write_settings(**kwargs)
            if len(self.model) > 0:
                print("\n# Pipeline History\n")
                print(format_code("\n".join(self.model.get_history())))
            event.accept()
        elif event.type() == QEvent.Type.PaletteChange:
            color_scheme = QApplication.styleHints().colorScheme()
            if color_scheme != Qt.ColorScheme.Unknown:
                QIcon.setThemeName(color_scheme.name.lower())
            else:
                QIcon.setThemeName("light")  # fallback
            if hasattr(self, "sidebar"):
                self.sidebar.refresh_theme()
        elif event.type() == QEvent.Type.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
        elif event.type() == QEvent.Type.Drop:
            mime = event.mimeData()
            if mime.hasUrls():
                urls = mime.urls()
                pipeline_files = [
                    u.toLocalFile()
                    for u in urls
                    if u.toLocalFile().endswith(".mnepipe")
                ]
                data_files = [
                    u.toLocalFile()
                    for u in urls
                    if not u.toLocalFile().endswith(".mnepipe")
                ]
                for path in pipeline_files:
                    self._apply_pipeline_from_path(path)
                try:
                    for path in data_files:
                        self.open_data(path)
                except FileNotFoundError as e:
                    QMessageBox.critical(self, "File not found", str(e))
            event.acceptProposedAction()
        return super().event(event)
