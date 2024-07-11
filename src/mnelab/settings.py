# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QPoint, QSettings, QSize, Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)

_DEFAULTS = {
    "max_recent": 6,
    "max_channels": 32,
    "recent": [],
    "toolbar": True,
    "statusbar": True,
    "size": QSize(700, 500),
    "pos": QPoint(100, 100),
    "plot_backend": "Matplotlib",
}


def _get_value(key):
    # The third argument to QSettings().value is a typecast which is applied to the
    # retrieved value. Since booleans are stored as "true" and "false" (at least on Win10),
    # we need that typecast. However, lists would get replaced with an empty list for some
    # reason, so here's a special case:
    if isinstance(_DEFAULTS[key], list):
        return QSettings().value(key, defaultValue=_DEFAULTS[key])
    return QSettings().value(key, defaultValue=_DEFAULTS[key], type=type(_DEFAULTS[key]))


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
        If `key` is given, the corresponding value. If key is `None`, return all settings in
        a dictionary.
    """
    if key is not None:
        return _get_value(key)
    return {key: _get_value(key) for key in _DEFAULTS}


def write_settings(**kwargs):
    """Write application settings."""
    for key, value in kwargs.items():
        QSettings().setValue(key, value)


class SettingsDialog(QDialog):
    def __init__(self, parent, backends):
        super().__init__(parent)
        self.setWindowTitle("MNELAB settings")

        grid = QGridLayout(self)

        backend = read_settings("plot_backend")
        if backend not in backends:
            backend = _DEFAULTS["plot_backend"]
        grid.addWidget(QLabel("Plot backend:"), 0, 0)
        self.plot_backend = QComboBox()
        self.plot_backend.addItems(backends)
        self.plot_backend.setCurrentIndex(backends.index(backend))
        grid.addWidget(self.plot_backend, 0, 1)

        grid.addWidget(QLabel("Recent files:"), 1, 0)
        self.max_recent = QSpinBox()
        self.max_recent.setRange(5, 25)
        self.max_recent.setValue(_get_value("max_recent"))
        self.max_recent.setAlignment(Qt.AlignRight)
        grid.addWidget(self.max_recent, 1, 1)

        grid.addWidget(QLabel("Displayed channels:"), 2, 0)
        self.max_channels = QSpinBox()
        self.max_channels.setRange(1, 256)
        self.max_channels.setValue(_get_value("max_channels"))
        self.max_channels.setAlignment(Qt.AlignRight)
        grid.addWidget(self.max_channels, 2, 1)

        self.reset_to_defaults = QPushButton("Reset to defaults")
        self.reset_to_defaults.clicked.connect(self.reset_settings)
        grid.addWidget(self.reset_to_defaults, 3, 0)

        self.reset_to_defaults = QPushButton("Reset window")
        self.reset_to_defaults.clicked.connect(self.reset_window)
        grid.addWidget(self.reset_to_defaults, 4, 0)

        hbox = QHBoxLayout()
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        hbox.addWidget(self.buttonbox)
        grid.addLayout(hbox, 5, 0, 1, 2)
        self.buttonbox.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.accepted.connect(self.apply_settings)
        self.buttonbox.rejected.connect(self.reject)

    @Slot()
    def apply_settings(self):
        QSettings().setValue("max_recent", int(self.max_recent.text()))
        self.parent().recent = self.parent().recent[: _get_value("max_recent")]
        QSettings().setValue("max_channels", int(self.max_channels.text()))
        self.parent().recent = self.parent().recent[: _get_value("max_channels")]
        QSettings().setValue("recent", self.parent().recent)
        QSettings().setValue("plot_backend", self.plot_backend.currentText())

    @Slot()
    def reset_settings(self):
        self.max_recent.setValue(_DEFAULTS["max_recent"])
        self.max_channels.setValue(_DEFAULTS["max_channels"])
        self.plot_backend.setValue(_DEFAULTS["plot_backend"])

    @Slot()
    def reset_window(self):
        self.parent().resize(_DEFAULTS["size"])
        self.parent().move(_DEFAULTS["pos"])
