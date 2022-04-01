# © MNELAB developers
#
# License: BSD (3-clause)

import sys

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..utils import interface_style


class InfoWidget(QWidget):
    """Display basic file information in a table (two columns).

    Parameters
    ----------
    values : dict
        Each key/value pair in this dict will be displayed in a row, separated by a colon.
    """
    def __init__(self, values=None):
        super().__init__()
        self._shortcut = False
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        vbox.addLayout(self.grid)
        self.set_values(values)

    def set_shortcuts(self):
        shortcuts = {
            "Open": "Ctrl+O",
            "History": "Ctrl+H",
            "Quit": "Ctrl+Q",
        }
        self.set_values(shortcuts, shortcut=True)

    def _get_shortcut_style(self):
        stylesheet = ".shortcut {"
        style = interface_style()
        if style is None:
            style = 'light'
        if style == 'light':
            stylesheet += "  \
                    background-color:#ededed; \
                    color:#666666; \
                    border:2px solid #dcdcdc;"
        else:
            stylesheet += "  \
                    background-color:#131313; \
                    color:#9a9a9a; \
                    border:2px solid #242424;"
        stylesheet += " \
                border-radius:5px; \
                font-size:15px; \
                font-weight:bold; \
                padding:8px 8px;}"
        return stylesheet

    def _add_text_entry(self, row, left, right):
        left = QLabel(left + ":")
        self.grid.addWidget(left, row, 0)
        right = QLabel(right)
        right.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.grid.addWidget(right, row, 1)

    def _add_shortcut_entry(self, row, left, right):
        hbox = QHBoxLayout()
        hbox.addStretch(1)

        left = left.replace('...', '')
        left = QLabel(left)
        hbox.addWidget(left)

        keys = right.split('+')
        for key in keys:
            if sys.platform.startswith("darwin"):
                key = key.replace('Ctrl', '⌘')
            button = QPushButton(key)
            button.setStyleSheet(self._get_shortcut_style())
            button.setProperty("class", "shortcut")
            hbox.addWidget(button)
        hbox.addStretch(1)

        self.grid.addLayout(hbox, row, 0)

    def set_values(self, values=None, shortcut=False):
        """Set values (and overwrite existing values).

        Parameters
        ----------
        values : dict
            Each key/value pair in this dict is displayed in a row separated by a colon.
        shortcut : bool
            Whether the values describe shortcuts or not. Defaults to False.
        """
        self._shortcut = shortcut
        self.clear()
        self.layout().takeAt(1)  # remove vertical stretch
        if shortcut:
            self.grid.setColumnStretch(1, 0)
        else:
            self.grid.setColumnStretch(1, 1)
            self.layout().addStretch(1)
        if values:
            for row, (key, value) in enumerate(values.items()):
                left = str(key)
                right = str(value)
                if shortcut:
                    self._add_shortcut_entry(row, left, right)
                else:
                    self._add_text_entry(row, left, right)

    def clear(self):
        """Clear all values."""
        item = self.grid.takeAt(0)
        while item:
            if isinstance(item, QHBoxLayout):
                sub = item.takeAt(0)
                while sub:
                    if sub.widget() is not None:
                        sub.widget().deleteLater()
                    del sub
                    sub = item.takeAt(0)
            else:
                item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)
