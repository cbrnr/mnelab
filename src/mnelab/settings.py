# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

from mne import get_config_path
from PySide6.QtCore import (
    QPoint,
    QSettings,
    QSize,
    QStandardPaths,
    QUrl,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
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
    "recent": [],
    "toolbar": True,
    "statusbar": True,
    "size": QSize(700, 500),
    "pos": QPoint(100, 100),
    "plot_backend": "Matplotlib",
    "splitter": 0.4,
    "last_dir": str(Path.home()),
    "dtype_badges": True,
    "show_menubar": True,
    "theme": "Auto",
}


def _get_value(key):
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
        settings.setValue(key, value)


def clear_settings():
    """Clear all settings."""
    QSettings(SETTINGS_PATH, QSettings.Format.IniFormat).clear()


def apply_theme(theme):
    """Apply a color scheme to the application.

    Parameters
    ----------
    theme : str
        One of `"Auto"`, `"Light"`, or `"Dark"`.
    """
    mapping = {
        "Auto": Qt.ColorScheme.Unknown,
        "Light": Qt.ColorScheme.Light,
        "Dark": Qt.ColorScheme.Dark,
    }
    QGuiApplication.styleHints().setColorScheme(
        mapping.get(theme, Qt.ColorScheme.Unknown)
    )


class SettingsDialog(QDialog):
    def __init__(self, parent, backends):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        vbox = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        themes = ["Auto", "Light", "Dark"]
        theme = read_settings("theme")
        if theme not in themes:
            theme = _DEFAULTS["theme"]
        self.theme = QComboBox()
        self.theme.addItems(themes)
        self.theme.setCurrentIndex(themes.index(theme))
        form.addRow("Theme:", self.theme)

        backend = read_settings("plot_backend")
        if backend not in backends:
            backend = _DEFAULTS["plot_backend"]
        self.plot_backend = QComboBox()
        self.plot_backend.addItems(backends)
        self.plot_backend.setCurrentIndex(backends.index(backend))
        form.addRow("Plot backend:", self.plot_backend)

        self.max_recent = FlatSpinBox()
        self.max_recent.setRange(5, 25)
        self.max_recent.setValue(read_settings("max_recent"))
        self.max_recent.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_recent.setFixedWidth(100)
        form.addRow("Recent files:", self.max_recent)

        self.max_channels = FlatSpinBox()
        self.max_channels.setRange(1, 256)
        self.max_channels.setValue(read_settings("max_channels"))
        self.max_channels.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_channels.setFixedWidth(100)
        form.addRow("Displayed channels:", self.max_channels)

        self.duration = FlatSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(read_settings("duration"))
        self.duration.setSuffix(" s")
        self.duration.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.duration.setFixedWidth(100)
        form.addRow("Displayed duration:", self.duration)

        self.dtype_badges = QCheckBox()
        self.dtype_badges.setChecked(read_settings("dtype_badges"))
        form.addRow("Data type badges:", self.dtype_badges)

        vbox.addLayout(form)

        mnelab_label = QLabel(
            f'<i>Settings are stored in <a href="{SETTINGS_PATH}">'
            f"{SETTINGS_PATH}</a>.</i>"
        )
        mnelab_label.linkActivated.connect(self.open_path)
        vbox.addSpacing(8)
        vbox.addWidget(mnelab_label)

        mne_config_path = get_config_path()
        mne_label = QLabel(
            f'<i>MNE-Python settings are stored in <a href="{mne_config_path}">'
            f"{mne_config_path}</a>.</i>"
        )
        mne_label.linkActivated.connect(self.open_path)
        vbox.addWidget(mne_label)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.reset_button = self.buttonbox.addButton(
            "Reset to defaults", QDialogButtonBox.ButtonRole.ResetRole
        )
        vbox.addWidget(self.buttonbox)

        self.reset_button.clicked.connect(self.reset_settings)
        self.buttonbox.accepted.connect(self.on_ok_clicked)
        self.buttonbox.rejected.connect(self.reject)

        vbox.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        self.setFocus()

    @Slot(str)
    def open_path(self, path):
        """Open a path in the default application."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @Slot()
    def on_ok_clicked(self):
        write_settings(
            max_recent=int(self.max_recent.text()),
            max_channels=int(self.max_channels.text()),
            duration=self.duration.value(),
            recent=self.parent().recent,
            plot_backend=self.plot_backend.currentText(),
            dtype_badges=self.dtype_badges.isChecked(),
            theme=self.theme.currentText(),
        )
        self.parent().recent = self.parent().recent[: read_settings("max_recent")]
        self.accept()

    @Slot()
    def reset_settings(self):
        self.max_recent.setValue(_DEFAULTS["max_recent"])
        self.max_channels.setValue(_DEFAULTS["max_channels"])
        self.duration.setValue(_DEFAULTS["duration"])
        self.dtype_badges.setChecked(_DEFAULTS["dtype_badges"])
        self.plot_backend.setCurrentIndex(
            self.plot_backend.findText(_DEFAULTS["plot_backend"])
        )
        self.theme.setCurrentIndex(self.theme.findText(_DEFAULTS["theme"]))
        self.parent().resize(_DEFAULTS["size"])
        self.parent().move(_DEFAULTS["pos"])
        self.parent().recent = []
        self.parent()._set_splitter_ratio(_DEFAULTS["splitter"])
        clear_settings()
