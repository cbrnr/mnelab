# © MNELAB developers
#
# License: BSD (3-clause)

from collections import defaultdict

import numpy as np
from mne import channel_type
from mne.defaults import _handle_default
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


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
        self.resize(630, 550)
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
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def populate_table(self, raw):
        # extract channel stats (logic from raw.describe())
        nchan = raw.info["nchan"]
        cols = defaultdict(list)
        cols["name"] = raw.ch_names
        for i in range(nchan):
            ch = raw.info["chs"][i]
            data = raw[i][0]
            cols["type"].append(channel_type(raw.info, i))
            cols["unit"].append(ch.get("unit", ""))
            cols["min"].append(np.min(data))
            cols["Q1"].append(np.percentile(data, 25))
            cols["median"].append(np.median(data))
            cols["Q3"].append(np.percentile(data, 75))
            cols["max"].append(np.max(data))

        # unit scaling
        scalings = _handle_default("scalings")
        units = _handle_default("units")
        for i in range(nchan):
            unit = units.get(cols["type"][i])
            scaling = scalings.get(cols["type"][i], 1)
            if scaling != 1:
                cols["unit"][i] = unit
                for col in ["min", "Q1", "median", "Q3", "max"]:
                    cols[col][i] *= scaling

        # set up tabel
        headers = [
            "Channel",
            "Name",
            "Type",
            "Unit",
            "Min",
            "Q1",
            "Median",
            "Q3",
            "Max",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(nchan)
        self.table.setHorizontalHeaderLabels(headers)

        # populate
        for i in range(nchan):
            item = SortableTableWidgetItem(i)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item)

            item = SortableTableWidgetItem(cols["name"][i])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, item)

            item = SortableTableWidgetItem(cols["type"][i].upper())
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 2, item)

            item = SortableTableWidgetItem(cols["unit"][i])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, item)

            for j, key in enumerate(["min", "Q1", "median", "Q3", "max"], start=4):
                formatted_value = f"{cols[key][i]:.2f}"
                item = SortableTableWidgetItem(float(formatted_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
