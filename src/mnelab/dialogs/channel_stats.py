# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from mnelab.utils import calculate_channel_stats


class SortableTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.value = value

    def __lt__(self, other):
        try:
            return float(self.value) < float(other.value)
        except ValueError:
            return str(self.value) < str(other.value)


class ChannelStats(QDialog):
    def __init__(self, parent, raw):
        super().__init__(parent=parent)

        # window
        self.setWindowTitle("Channel Stats")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)

        # create table
        self.table = QTableWidget(self)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # populate table
        self.populate_table(raw)
        self.table.resizeColumnsToContents()

        # add close button
        buttonbox = QDialogButtonBox(QDialogButtonBox.Close)
        layout.addWidget(buttonbox)
        buttonbox.rejected.connect(self.reject)

        # calculate table width
        table_width = self.table.verticalHeader().width()
        table_width += sum(
            self.table.columnWidth(i) for i in range(self.table.columnCount())
        )
        table_width += self.table.verticalScrollBar().width()
        self.resize(table_width - 30, 550)
        self.setLayout(layout)

    def populate_table(self, raw):
        cols, nchan = calculate_channel_stats(raw)
        self.table.setColumnCount(9)
        self.table.setRowCount(nchan)
        self.table.setHorizontalHeaderLabels(
            [
                "Channel",
                "Name",
                "Type",
                "Unit",
                "Min",
                "Q1",
                "Mean",
                "Median",
                "Q3",
                "Max",
            ]
        )

        for i in range(nchan):
            item = QTableWidgetItem(str(i))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item)

            item = QTableWidgetItem(cols["name"][i])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, item)

            item = QTableWidgetItem(cols["type"][i].upper())
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 2, item)

            item = QTableWidgetItem(cols["unit"][i])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, item)

            for j, key in enumerate(["min", "Q1", "median", "Q3", "max"], start=4):
                formatted_value = f"{cols[key][i]:.2f}"
                item = QTableWidgetItem(formatted_value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, item)
