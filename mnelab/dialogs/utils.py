# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


def select_all(list_widget):
    """Select all items in a QListWidget."""
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)


class IntTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))

    def __lt__(self, other):
        return int(self.data(Qt.EditRole)) < int(other.data(Qt.EditRole))

    def setData(self, role, value):
        try:
            value = int(value)
        except ValueError:
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))

    def value(self):
        return float(self.data(Qt.DisplayRole))
