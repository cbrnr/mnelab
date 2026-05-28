# © MNELAB developers
#
# License: BSD (3-clause)

import bisect
import json
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QSettings,
    QSize,
    QStandardPaths,
    Slot,
)
from PySide6.QtGui import QFont, QIcon, QPalette, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mnelab.widgets import FlatSpinBox

SETTINGS_PATH = str(
    Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
    )
    / "mnelab.ini"
)


_DEFAULTS = {
    "max_recent": 6,
    "max_channels": 20,
    "duration": 20,
    "epochs": 10,
    "recent": [],
    "statusbar": True,
    "size": QSize(700, 500),
    "pos": QPoint(100, 100),
    "plot_backend": "Matplotlib",
    "splitter": 0.4,
    "last_dir": str(Path.home()),
    "dtype_badges": True,
    "menu_icons": True,
    "show_menubar": True,
    "annotation_colors": {},
    "memory_saving": False,
    "toolbar_actions": [
        "open_file",
        "---",
        "chan_props",
        "---",
        "plot_data",
        "plot_psd",
        "plot_locations",
        "---",
        "filter",
        "find_events",
        "epoch_data",
        "run_ica",
        "---",
        "settings",
    ],
}

_JSON_KEYS = {"annotation_colors", "toolbar_actions"}


def _get_value(key):
    if key in _JSON_KEYS:
        raw = QSettings(SETTINGS_PATH, QSettings.Format.IniFormat).value(
            key, defaultValue=None
        )
        if raw is None:
            return _DEFAULTS[key]
        return json.loads(raw)
    return QSettings(SETTINGS_PATH, QSettings.Format.IniFormat).value(
        key, defaultValue=_DEFAULTS[key], type=type(_DEFAULTS[key])
    )


def read_settings(key=None):
    """
    Read application settings.

    Parameters
    ----------
    key : str, optional
        Setting key to read, by default `None`.

    Returns
    -------
    str | dict
        If `key` is given, return the corresponding value. If key is `None`, return all
        settings in a dictionary.
    """
    if key is not None:
        if key not in _DEFAULTS:
            raise KeyError(f"Invalid setting key: {key}")
        return _get_value(key)
    return {key: _get_value(key) for key in _DEFAULTS}


def write_settings(**kwargs):
    """Write application settings."""
    settings = QSettings(SETTINGS_PATH, QSettings.Format.IniFormat)
    for key, value in kwargs.items():
        if key not in _DEFAULTS:
            raise KeyError(f"Invalid setting key: {key}")
        if key in _JSON_KEYS:
            value = json.dumps(value)
        settings.setValue(key, value)


def clear_settings():
    """Clear all settings."""
    QSettings(SETTINGS_PATH, QSettings.Format.IniFormat).clear()


class SettingsDialog(QDialog):
    def __init__(self, parent, backends, initial_page=0):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        vbox = QVBoxLayout(self)

        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)

        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(130)
        self._sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar.addItems(["General", "Plotting", "Toolbar"])
        self._sidebar.setIconSize(QSize(16, 16))
        self._sidebar.setCurrentRow(initial_page)
        hbox.addWidget(self._sidebar)

        self._stack = QStackedWidget()

        # shared form layout configuration
        _form_margins = (12, 8, 12, 8)
        _form_vspacing = 8
        _form_hspacing = 12

        # General page
        general_page = QWidget()
        general_form = QFormLayout(general_page)
        general_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        general_form.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        general_form.setContentsMargins(*_form_margins)
        general_form.setVerticalSpacing(_form_vspacing)
        general_form.setHorizontalSpacing(_form_hspacing)

        self.max_recent = FlatSpinBox()
        self.max_recent.setRange(5, 25)
        self.max_recent.setValue(read_settings("max_recent"))
        self.max_recent.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_recent.setFixedWidth(100)
        general_form.addRow("Recent Files:", self.max_recent)

        self.dtype_badges = QCheckBox()
        self.dtype_badges.setChecked(read_settings("dtype_badges"))
        general_form.addRow("Data Type Badges:", self.dtype_badges)

        self.menu_icons = QCheckBox()
        self.menu_icons.setChecked(read_settings("menu_icons"))
        general_form.addRow("Menu Icons:", self.menu_icons)

        self.memory_saving = QCheckBox()
        self.memory_saving.setChecked(read_settings("memory_saving"))
        general_form.addRow("Save Memory:", self.memory_saving)

        self._stack.addWidget(general_page)

        # Plotting page
        plotting_page = QWidget()
        plotting_form = QFormLayout(plotting_page)
        plotting_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        plotting_form.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        plotting_form.setContentsMargins(*_form_margins)
        plotting_form.setVerticalSpacing(_form_vspacing)
        plotting_form.setHorizontalSpacing(_form_hspacing)

        backend = read_settings("plot_backend")
        if backend not in backends:
            backend = _DEFAULTS["plot_backend"]
        self.plot_backend = QComboBox()
        self.plot_backend.addItems(backends)
        self.plot_backend.setCurrentIndex(backends.index(backend))
        plotting_form.addRow("Plot Backend:", self.plot_backend)

        self.max_channels = FlatSpinBox()
        self.max_channels.setRange(1, 256)
        self.max_channels.setValue(read_settings("max_channels"))
        self.max_channels.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_channels.setFixedWidth(100)
        plotting_form.addRow("Displayed Channels:", self.max_channels)

        self.duration = FlatSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(read_settings("duration"))
        self.duration.setSuffix(" s")
        self.duration.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.duration.setFixedWidth(100)
        plotting_form.addRow("Displayed Duration:", self.duration)

        self.epochs = FlatSpinBox()
        self.epochs.setRange(1, 100)
        self.epochs.setValue(read_settings("epochs"))
        self.epochs.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.epochs.setFixedWidth(100)
        plotting_form.addRow("Displayed Epochs:", self.epochs)

        self._stack.addWidget(plotting_page)

        # Toolbar page
        toolbar_page = QWidget()
        toolbar_vbox = QVBoxLayout(toolbar_page)
        toolbar_vbox.setContentsMargins(*_form_margins)
        toolbar_vbox.setSpacing(_form_vspacing)

        toolbar_hbox = QHBoxLayout()
        toolbar_hbox.setSpacing(8)

        _header_font = QFont(QApplication.font())
        _header_font.setPointSizeF(_header_font.pointSizeF() * 0.85)
        _header_font.setBold(True)

        left_vbox = QVBoxLayout()
        _avail_header = QLabel("Available Actions")
        _avail_header.setFont(_header_font)
        left_vbox.addWidget(_avail_header)
        self._available_list = QListWidget()
        self._available_list.setIconSize(QSize(16, 16))
        left_vbox.addWidget(self._available_list)
        toolbar_hbox.addLayout(left_vbox)

        center_vbox = QVBoxLayout()
        center_vbox.addStretch()
        self._add_btn = QPushButton("→")
        self._remove_btn = QPushButton("←")
        self._up_btn = QPushButton("↑")
        self._down_btn = QPushButton("↓")
        for btn in [self._add_btn, self._remove_btn]:
            btn.setEnabled(False)
            center_vbox.addWidget(btn)
        center_vbox.addSpacing(8)
        for btn in [self._up_btn, self._down_btn]:
            btn.setEnabled(False)
            center_vbox.addWidget(btn)
        center_vbox.addStretch()
        toolbar_hbox.addLayout(center_vbox)

        right_vbox = QVBoxLayout()
        _toolbar_header = QLabel("Toolbar")
        _toolbar_header.setFont(_header_font)
        right_vbox.addWidget(_toolbar_header)
        self._toolbar_list = QListWidget()
        self._toolbar_list.setIconSize(QSize(16, 16))
        self._toolbar_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        right_vbox.addWidget(self._toolbar_list)
        toolbar_hbox.addLayout(right_vbox)

        toolbar_vbox.addLayout(toolbar_hbox)
        reset_toolbar_btn = QPushButton("Reset Toolbar")
        reset_toolbar_btn.clicked.connect(self._reset_toolbar_page)
        toolbar_vbox.addWidget(reset_toolbar_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self._stack.addWidget(toolbar_page)

        self._add_btn.clicked.connect(self._add_to_toolbar)
        self._remove_btn.clicked.connect(self._remove_from_toolbar)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)
        self._available_list.currentRowChanged.connect(self._update_toolbar_buttons)
        self._toolbar_list.currentRowChanged.connect(self._update_toolbar_buttons)
        self._toolbar_list.model().rowsMoved.connect(
            lambda *_: self._update_toolbar_buttons()
        )
        self._toolbar_list.model().rowsInserted.connect(
            lambda *_: self._update_toolbar_buttons()
        )
        self._populate_toolbar_page(read_settings("toolbar_actions"))
        self._update_toolbar_buttons()

        hbox.addWidget(self._stack)
        vbox.addLayout(hbox)

        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._stack.setCurrentIndex(initial_page)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.reset_button = self.buttonbox.addButton(
            "Reset to Defaults", QDialogButtonBox.ButtonRole.ResetRole
        )
        vbox.addWidget(self.buttonbox)

        self.reset_button.clicked.connect(self.reset_settings)
        self.buttonbox.accepted.connect(self.on_ok_clicked)
        self.buttonbox.rejected.connect(self.reject)

        self.setMinimumSize(600, 380)
        self.resize(650, 380)

        self._update_theme()
        self.setFocus()

    def _update_theme(self):
        p = QApplication.instance().palette()
        base = p.color(QPalette.ColorRole.Base).name()
        highlight = p.color(QPalette.ColorRole.Highlight).name()
        highlighted_text = p.color(QPalette.ColorRole.HighlightedText).name()
        midlight = p.color(QPalette.ColorRole.Midlight).name()
        self._sidebar.setStyleSheet(f"""
            QListWidget {{
                background: {base};
                border-radius: 6px;
                outline: none;
                padding: 4px 0px;
            }}
            QListWidget::item {{
                padding: 5px 12px;
                border-radius: 5px;
                margin: 1px 4px;
            }}
            QListWidget::item:selected {{
                background: {highlight};
                color: {highlighted_text};
            }}
            QListWidget::item:hover:!selected {{
                background: {midlight};
            }}
        """)
        self._sidebar.item(0).setIcon(QIcon.fromTheme("settings-general"))
        self._sidebar.item(1).setIcon(QIcon.fromTheme("settings-plotting"))
        self._sidebar.item(2).setIcon(QIcon.fromTheme("settings-toolbar"))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._update_theme()
        super().changeEvent(event)

    @Slot()
    def on_ok_clicked(self):
        toolbar_keys = self._get_toolbar_action_keys()
        write_settings(
            max_recent=self.max_recent.value(),
            max_channels=self.max_channels.value(),
            duration=self.duration.value(),
            epochs=self.epochs.value(),
            recent=self.parent().recent,
            plot_backend=self.plot_backend.currentText(),
            dtype_badges=self.dtype_badges.isChecked(),
            menu_icons=self.menu_icons.isChecked(),
            memory_saving=self.memory_saving.isChecked(),
            toolbar_actions=toolbar_keys,
        )
        self.parent().recent = self.parent().recent[: read_settings("max_recent")]
        self.parent()._apply_toolbar(toolbar_keys)
        self.accept()

    @Slot()
    def reset_settings(self):
        self.max_recent.setValue(_DEFAULTS["max_recent"])
        self.max_channels.setValue(_DEFAULTS["max_channels"])
        self.duration.setValue(_DEFAULTS["duration"])
        self.epochs.setValue(_DEFAULTS["epochs"])
        self.dtype_badges.setChecked(_DEFAULTS["dtype_badges"])
        self.menu_icons.setChecked(_DEFAULTS["menu_icons"])
        self.memory_saving.setChecked(_DEFAULTS["memory_saving"])
        self.plot_backend.setCurrentIndex(
            self.plot_backend.findText(_DEFAULTS["plot_backend"])
        )
        self.parent().resize(_DEFAULTS["size"])
        self.parent().move(_DEFAULTS["pos"])
        self.parent().recent = []
        self.parent()._set_splitter_ratio(_DEFAULTS["splitter"])
        self._reset_toolbar_page()
        self.parent()._apply_toolbar(_DEFAULTS["toolbar_actions"])
        clear_settings()

    def _populate_toolbar_page(self, current_keys):
        excluded = {"statusbar", "menubar"}
        all_actions = self.parent().all_actions
        in_toolbar = {k for k in current_keys if k != "---"}
        for key in current_keys:
            if key == "---":
                item = QListWidgetItem("─── Separator ───")
                item.setData(Qt.ItemDataRole.UserRole, "---")
            elif key in all_actions:
                action = all_actions[key]
                text = action.text().replace("&", "")
                item = QListWidgetItem(action.icon(), text)
                item.setData(Qt.ItemDataRole.UserRole, key)
            else:
                continue
            self._toolbar_list.addItem(item)
        sep_item = QListWidgetItem("─── Separator ───")
        sep_item.setData(Qt.ItemDataRole.UserRole, "---")
        self._available_list.addItem(sep_item)
        available = []
        for key, action in all_actions.items():
            if key in excluded or key in in_toolbar:
                continue
            if key.startswith("export_data"):
                continue
            text = action.text().replace("&", "")
            available.append((text, key, action.icon()))
        available.sort(key=lambda x: x[0])
        for text, key, icon in available:
            item = QListWidgetItem(icon, text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._available_list.addItem(item)

    def _get_toolbar_action_keys(self):
        return [
            self._toolbar_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._toolbar_list.count())
        ]

    def _reset_toolbar_page(self):
        self._toolbar_list.clear()
        self._available_list.clear()
        self._populate_toolbar_page(_DEFAULTS["toolbar_actions"])
        self._update_toolbar_buttons()

    @Slot()
    def _add_to_toolbar(self):
        row = self._available_list.currentRow()
        if row < 0:
            return
        key = self._available_list.item(row).data(Qt.ItemDataRole.UserRole)
        toolbar_row = self._toolbar_list.currentRow()
        ins = toolbar_row + 1 if toolbar_row >= 0 else self._toolbar_list.count()
        if key == "---":
            # separator stays in the available list; clone a new one into toolbar
            item = QListWidgetItem("─── Separator ───")
            item.setData(Qt.ItemDataRole.UserRole, "---")
            self._toolbar_list.insertItem(ins, item)
            self._toolbar_list.setCurrentRow(ins)
        else:
            item = self._available_list.takeItem(row)
            self._toolbar_list.insertItem(ins, item)
            self._toolbar_list.setCurrentRow(ins)
            new_row = min(row, self._available_list.count() - 1)
            if new_row >= 0:
                self._available_list.setCurrentRow(new_row)
        self._update_toolbar_buttons()

    @Slot()
    def _remove_from_toolbar(self):
        row = self._toolbar_list.currentRow()
        if row < 0:
            return
        item = self._toolbar_list.takeItem(row)
        key = item.data(Qt.ItemDataRole.UserRole)
        if key != "---":
            # skip the separator permanently at position 0
            texts = [
                self._available_list.item(i).text()
                for i in range(1, self._available_list.count())
            ]
            pos = bisect.bisect_left(texts, item.text()) + 1
            self._available_list.insertItem(pos, item)
            self._available_list.setCurrentRow(pos)
        self._update_toolbar_buttons()

    @Slot()
    def _move_up(self):
        row = self._toolbar_list.currentRow()
        if row <= 0:
            return
        item = self._toolbar_list.takeItem(row)
        self._toolbar_list.insertItem(row - 1, item)
        self._toolbar_list.setCurrentRow(row - 1)

    @Slot()
    def _move_down(self):
        row = self._toolbar_list.currentRow()
        if row < 0 or row >= self._toolbar_list.count() - 1:
            return
        item = self._toolbar_list.takeItem(row)
        self._toolbar_list.insertItem(row + 1, item)
        self._toolbar_list.setCurrentRow(row + 1)

    @Slot()
    def _update_toolbar_buttons(self):
        avail_row = self._available_list.currentRow()
        toolbar_row = self._toolbar_list.currentRow()
        toolbar_count = self._toolbar_list.count()
        self._add_btn.setEnabled(avail_row >= 0)
        self._remove_btn.setEnabled(toolbar_row >= 0)
        self._up_btn.setEnabled(toolbar_row > 0)
        self._down_btn.setEnabled(0 <= toolbar_row < toolbar_count - 1)
