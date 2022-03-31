# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
                               QPushButton, QHBoxLayout)


class InfoWidget(QWidget):
    """Display basic file information in a table (two columns).

    Parameters
    ----------
    values : dict
        Each key/value pair in this dict will be displayed in a row, separated by a colon.
    """
    def __init__(self, values=None):
        super().__init__()
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)

    def _get_shortcut_style(self):
        return " \
            .shortcut { \
                background-color:#ededed; \
                border-radius:5px; \
                border:2px solid #dcdcdc; \
                color:#666666; \
                font-size:15px; \
                font-weight:bold; \
                padding:15px 15px; \
            } \
        "

    def _add_text_entry(self, row, left, right):
        left = QLabel(left + ":")
        self.grid.addWidget(left, row, 0)
        right = QLabel(right)
        right.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.grid.addWidget(right, row, 1)

    def _add_shortcut(self, row, left, right):
        left = left.replace('...', '')
        left = QLabel(left)
        spacer = QWidget()
        self.grid.addWidget(left, row, 0)

        keys = right.split('+')
        right = QHBoxLayout()
        for key in keys:
            button = QPushButton(key)
            button.setStyleSheet(self._get_shortcut_style())
            button.setProperty("class", "shortcut")
            right.addWidget(button)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right.addWidget(spacer)
        self.grid.addLayout(right, row, 1)

    def set_values(self, values=None, shortcut=False):
        """Set values (and overwrite existing values).

        Parameters
        ----------
        values : dict
            Each key/value pair in this dict is displayed in a row separated by a colon.
        """
        self.clear()
        if values:
            for row, (key, value) in enumerate(values.items()):
                left = str(key)
                right = str(value)
                if shortcut:
                    self._add_shortcut(row, left, right)
                else:
                    self._add_text_entry(row, left, right)

    def clear(self):
        """Clear all values."""
        item = self.grid.takeAt(0)
        while item:
            if isinstance(item, QHBoxLayout):
                sub = item.takeAt(0)
                while sub:
                    sub.widget().deleteLater()
                    sub = item.takeAt(0)
            else:
                item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)
