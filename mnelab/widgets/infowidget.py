# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                             QSizePolicy)


class InfoWidget(QWidget):
    """Display basic file information in a table (two columns).

    Parameters
    ----------
    values : dict
        Each key/value pair in this dict will be displayed in a row, separated
        by a colon.
    """
    def __init__(self, values=None):
        super().__init__()
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)

    def set_values(self, values=None):
        """Set values (and overwrite existing values).

        Parameters
        ----------
        values : dict
            Each key/value pair in this dict will be displayed in a row,
            separated by a colon.
        """
        self.clear()
        if values:
            for row, (key, value) in enumerate(values.items()):
                left = QLabel(str(key) + ":")
                right = QLabel(str(value))
                right.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
                self.grid.addWidget(left, row, 0)
                self.grid.addWidget(right, row, 1)

    def clear(self):
        """Clear all values.
        """
        item = self.grid.takeAt(0)
        while item:
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)
