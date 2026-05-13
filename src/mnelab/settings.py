# © MNELAB developers
#
# License: BSD (3-clause)

import json
from pathlib import Path

from mne import get_config_path
from PySide6.QtCore import (
    QEvent,
    QPoint,
    QSettings,
    QSize,
    QStandardPaths,
    QUrl,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QIcon, QPalette, Qt
from PySide6.QtWidgets import (
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
    "toolbar": True,
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
}

_JSON_KEYS = {"annotation_colors"}


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
    def __init__(self, parent, backends):
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
        self._sidebar.addItems(["General", "Plotting"])
        self._sidebar.setIconSize(QSize(16, 16))
        self._sidebar.setCurrentRow(0)
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

        hbox.addWidget(self._stack)
        vbox.addLayout(hbox)

        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)

        self._mnelab_label = QLabel()
        self._mnelab_label.linkActivated.connect(self.open_path)
        vbox.addSpacing(8)
        vbox.addWidget(self._mnelab_label)

        self._mne_config_path = str(get_config_path())
        self._mne_label = QLabel()
        self._mne_label.linkActivated.connect(self.open_path)
        vbox.addWidget(self._mne_label)

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

        self.setMinimumSize(420, 260)

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
        link = p.color(QPalette.ColorRole.Link).name()
        self._mnelab_label.setText(
            f"<i>Settings are stored in"
            f' <a href="{SETTINGS_PATH}" style="color: {link};">'
            f"{SETTINGS_PATH}</a>.</i>"
        )
        self._mne_label.setText(
            f"<i>MNE-Python settings are stored in"
            f' <a href="{self._mne_config_path}" style="color: {link};">'
            f"{self._mne_config_path}</a>.</i>"
        )

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._update_theme()
        super().changeEvent(event)

    @Slot(str)
    def open_path(self, path):
        """Open a path in the default application."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @Slot()
    def on_ok_clicked(self):
        write_settings(
            max_recent=self.max_recent.value(),
            max_channels=self.max_channels.value(),
            duration=self.duration.value(),
            epochs=self.epochs.value(),
            recent=self.parent().recent,
            plot_backend=self.plot_backend.currentText(),
            dtype_badges=self.dtype_badges.isChecked(),
            menu_icons=self.menu_icons.isChecked(),
        )
        self.parent().recent = self.parent().recent[: read_settings("max_recent")]
        self.accept()

    @Slot()
    def reset_settings(self):
        self.max_recent.setValue(_DEFAULTS["max_recent"])
        self.max_channels.setValue(_DEFAULTS["max_channels"])
        self.duration.setValue(_DEFAULTS["duration"])
        self.epochs.setValue(_DEFAULTS["epochs"])
        self.dtype_badges.setChecked(_DEFAULTS["dtype_badges"])
        self.menu_icons.setChecked(_DEFAULTS["menu_icons"])
        self.plot_backend.setCurrentIndex(
            self.plot_backend.findText(_DEFAULTS["plot_backend"])
        )
        self.parent().resize(_DEFAULTS["size"])
        self.parent().move(_DEFAULTS["pos"])
        self.parent().recent = []
        self.parent()._set_splitter_ratio(_DEFAULTS["splitter"])
        clear_settings()
