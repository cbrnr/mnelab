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
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mnelab.widgets import FlatSpinBox, set_tooltip

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
    "scalings": "auto",
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
        "pipeline",
        "---",
        "settings",
    ],
}

_JSON_KEYS = {"annotation_colors", "toolbar_actions"}

# preferences that can be saved in and loaded from a profile (window and session state
# such as size, position or recent files is deliberately excluded)
PROFILE_KEYS = (
    "max_recent",
    "dtype_badges",
    "menu_icons",
    "memory_saving",
    "plot_backend",
    "max_channels",
    "duration",
    "epochs",
    "scalings",
    "toolbar_actions",
)

# in-memory values that take precedence over the settings file (e.g. from a profile
# passed on the command line)
_overrides = {}


def _get_value(key):
    if key in _overrides:
        return _overrides[key]
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
    """Read application settings.

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
        _overrides.pop(key, None)  # explicit changes replace session overrides


def clear_settings():
    """Clear all settings."""
    QSettings(SETTINGS_PATH, QSettings.Format.IniFormat).clear()
    _overrides.clear()


def set_overrides(values):
    """Override settings for the current session without writing them to disk.

    Parameters
    ----------
    values : dict
        Setting keys and values. Writing a key with `write_settings` removes its
        override.
    """
    for key in values:
        if key not in _DEFAULTS:
            raise KeyError(f"Invalid setting key: {key}")
    _overrides.update(values)


def _validate_profile(values):
    if not isinstance(values, dict):
        raise ValueError("A profile must be a JSON object")  # noqa: TRY004
    for key, value in values.items():
        if key not in PROFILE_KEYS:
            raise ValueError(f"Unknown setting: {key}")
        default = _DEFAULTS[key]
        if key == "toolbar_actions":
            valid = isinstance(value, list) and all(isinstance(v, str) for v in value)
        else:
            valid = type(value) is type(default)  # exact check rejects bool for int
        if not valid:
            raise ValueError(
                f"Invalid value for {key}: expected {type(default).__name__}"
            )
    if "scalings" in values and values["scalings"] not in ("auto", "fixed"):
        raise ValueError('Invalid value for scalings: expected "auto" or "fixed"')


def read_profile(path):
    """Read a settings profile from a JSON file.

    Parameters
    ----------
    path : str | Path
        Path to the profile file.

    Returns
    -------
    dict
        Validated settings contained in the profile. The profile can be partial, so the
        dictionary only contains the keys present in the file.

    Raises
    ------
    ValueError
        If the file is not valid JSON or contains unknown keys or invalid values.
    """
    try:
        values = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error}") from error
    _validate_profile(values)
    return values


def write_profile(path, values):
    """Write a settings profile to a JSON file.

    Parameters
    ----------
    path : str | Path
        Path to the profile file.
    values : dict
        Settings to write. Keys that cannot be part of a profile are ignored.
    """
    profile = {key: values[key] for key in PROFILE_KEYS if key in values}
    Path(path).write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")


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

        def add_setting_row(form, label, field, tooltip):
            """Add a setting field with matching label and field tooltips."""
            form.addRow(label, field)
            set_tooltip(tooltip, form.labelForField(field), field)

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
        add_setting_row(
            general_form,
            "Recent Files:",
            self.max_recent,
            "Set how many recently opened files to keep in the File menu",
        )

        self.dtype_badges = QCheckBox()
        self.dtype_badges.setChecked(read_settings("dtype_badges"))
        add_setting_row(
            general_form,
            "Data Type Badges:",
            self.dtype_badges,
            "Show data type badges (Raw, Epochs) in the sidebar",
        )

        self.menu_icons = QCheckBox()
        self.menu_icons.setChecked(read_settings("menu_icons"))
        add_setting_row(
            general_form,
            "Menu Icons:",
            self.menu_icons,
            "Show icons beside actions in application menus",
        )

        self.memory_saving = QCheckBox()
        self.memory_saving.setChecked(read_settings("memory_saving"))
        add_setting_row(
            general_form,
            "Save Memory:",
            self.memory_saving,
            "Unload inactive datasets and reload them when selected to reduce "
            "memory use",
        )

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
        add_setting_row(
            plotting_form,
            "Plot Backend:",
            self.plot_backend,
            "Choose the backend used for plots",
        )

        self.max_channels = FlatSpinBox()
        self.max_channels.setRange(1, 256)
        self.max_channels.setValue(read_settings("max_channels"))
        self.max_channels.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_channels.setFixedWidth(100)
        add_setting_row(
            plotting_form,
            "Displayed Channels:",
            self.max_channels,
            "Set how many channels to show at once in data plots",
        )

        self.duration = FlatSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(read_settings("duration"))
        self.duration.setSuffix(" s")
        self.duration.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.duration.setFixedWidth(100)
        add_setting_row(
            plotting_form,
            "Displayed Duration:",
            self.duration,
            "Set the duration shown at once in continuous-data plots",
        )

        self.epochs = FlatSpinBox()
        self.epochs.setRange(1, 100)
        self.epochs.setValue(read_settings("epochs"))
        self.epochs.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.epochs.setFixedWidth(100)
        add_setting_row(
            plotting_form,
            "Displayed Epochs:",
            self.epochs,
            "Set how many epochs to show at once in epoch plots",
        )

        self.scalings = QComboBox()
        self.scalings.addItems(["Auto", "Fixed"])
        self.scalings.setCurrentText(read_settings("scalings").title())
        add_setting_row(
            plotting_form,
            "Channel Scaling:",
            self.scalings,
            "Automatically scale data or use fixed scales for each channel type",
        )

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
        toolbar_hbox.addLayout(left_vbox, 1)

        center_vbox = QVBoxLayout()
        center_vbox.addStretch()
        self._add_btn = QPushButton("→")
        self._remove_btn = QPushButton("←")
        self._up_btn = QPushButton("↑")
        self._down_btn = QPushButton("↓")
        for btn in [self._add_btn, self._remove_btn]:
            btn.setEnabled(False)
            btn.setFixedWidth(36)
            center_vbox.addWidget(btn)
        center_vbox.addSpacing(8)
        for btn in [self._up_btn, self._down_btn]:
            btn.setEnabled(False)
            btn.setFixedWidth(36)
            center_vbox.addWidget(btn)
        center_vbox.addStretch()
        toolbar_hbox.addLayout(center_vbox, 0)

        right_vbox = QVBoxLayout()
        _toolbar_header = QLabel("Toolbar")
        _toolbar_header.setFont(_header_font)
        right_vbox.addWidget(_toolbar_header)
        self._toolbar_list = QListWidget()
        self._toolbar_list.setIconSize(QSize(16, 16))
        self._toolbar_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        right_vbox.addWidget(self._toolbar_list)
        toolbar_hbox.addLayout(right_vbox, 1)

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
        self.import_button = self.buttonbox.addButton(
            "Import…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.export_button = self.buttonbox.addButton(
            "Export…", QDialogButtonBox.ButtonRole.ActionRole
        )
        set_tooltip(
            "Load settings from a JSON profile (applied after clicking OK)",
            self.import_button,
        )
        set_tooltip(
            "Save the settings shown here to a JSON profile", self.export_button
        )
        vbox.addWidget(self.buttonbox)

        self.reset_button.clicked.connect(self.reset_settings)
        self.import_button.clicked.connect(self.import_profile)
        self.export_button.clicked.connect(self.export_profile)
        self.buttonbox.accepted.connect(self.on_ok_clicked)
        self.buttonbox.rejected.connect(self.reject)

        self.setMinimumSize(600, 380)
        self.resize(670, 380)

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

    def _get_values(self):
        """Return the profile settings currently shown in the dialog."""
        return {
            "max_recent": self.max_recent.value(),
            "dtype_badges": self.dtype_badges.isChecked(),
            "menu_icons": self.menu_icons.isChecked(),
            "memory_saving": self.memory_saving.isChecked(),
            "plot_backend": self.plot_backend.currentText(),
            "max_channels": self.max_channels.value(),
            "duration": self.duration.value(),
            "epochs": self.epochs.value(),
            "scalings": self.scalings.currentText().lower(),
            "toolbar_actions": self._get_toolbar_action_keys(),
        }

    def _set_values(self, values):
        """Show the given profile settings (keys that are not given stay unchanged)."""
        if "max_recent" in values:
            self.max_recent.setValue(values["max_recent"])
        if "dtype_badges" in values:
            self.dtype_badges.setChecked(values["dtype_badges"])
        if "menu_icons" in values:
            self.menu_icons.setChecked(values["menu_icons"])
        if "memory_saving" in values:
            self.memory_saving.setChecked(values["memory_saving"])
        if "plot_backend" in values:
            index = self.plot_backend.findText(values["plot_backend"])
            if index < 0:  # backend not available, fall back to the default
                index = self.plot_backend.findText(_DEFAULTS["plot_backend"])
            self.plot_backend.setCurrentIndex(index)
        if "max_channels" in values:
            self.max_channels.setValue(values["max_channels"])
        if "duration" in values:
            self.duration.setValue(values["duration"])
        if "epochs" in values:
            self.epochs.setValue(values["epochs"])
        if "scalings" in values:
            self.scalings.setCurrentText(values["scalings"].title())
        if "toolbar_actions" in values:
            self._toolbar_list.clear()
            self._available_list.clear()
            self._populate_toolbar_page(values["toolbar_actions"])
            self._update_toolbar_buttons()

    @Slot()
    def on_ok_clicked(self):
        values = self._get_values()
        # only write settings that changed, so session overrides (e.g. from a profile
        # passed on the command line) are not persisted by accident
        changed = {k: v for k, v in values.items() if v != read_settings(k)}
        write_settings(recent=self.parent().recent, **changed)
        self.parent().recent = self.parent().recent[: read_settings("max_recent")]
        self.parent()._apply_toolbar(values["toolbar_actions"])
        self.accept()

    @Slot()
    def reset_settings(self):
        self._set_values(_DEFAULTS)
        self.parent().resize(_DEFAULTS["size"])
        self.parent().move(_DEFAULTS["pos"])
        self.parent().recent = []
        self.parent()._set_splitter_ratio(_DEFAULTS["splitter"])
        self.parent()._apply_toolbar(_DEFAULTS["toolbar_actions"])
        clear_settings()

    @Slot()
    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            read_settings("last_dir"),
            "Settings Files (*.json)",
        )
        if not path:
            return
        try:
            values = read_profile(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Could Not Import Settings", str(error))
            return
        self._set_values(values)
        write_settings(last_dir=str(Path(path).parent))

    @Slot()
    def export_profile(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            read_settings("last_dir"),
            "Settings Files (*.json)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".json"
        try:
            write_profile(path, self._get_values())
        except OSError as error:
            QMessageBox.warning(self, "Could Not Export Settings", str(error))
            return
        write_settings(last_dir=str(Path(path).parent))

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
