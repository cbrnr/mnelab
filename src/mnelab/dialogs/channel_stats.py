# © MNELAB developers
#
# License: BSD (3-clause)

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from mnelab.dialogs.utils import NumberSortProxyModel
from mnelab.utils import calculate_channel_stats


class ChannelStats(QDialog):
    _last_directory = None  # track last used directory

    def __init__(self, parent, raw):
        super().__init__(parent=parent)

        # window
        self.setWindowTitle("Channel Stats")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)

        # populate model
        self.populate_model(raw)

        # create proxy model for sorting
        self.proxy_model = NumberSortProxyModel()
        self.proxy_model.setSourceModel(self.model)

        # create table view
        self.view = QTableView(self)
        self.view.setModel(self.proxy_model)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        self.view.setEditTriggers(QTableView.NoEditTriggers)
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(True)

        # configure header
        header = self.view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, self.model.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # disable row height changes
        self.view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        layout.addWidget(self.view)

        # add buttons
        buttonbox = QDialogButtonBox(QDialogButtonBox.Close)
        savebutton = QPushButton("Save to CSV...")
        buttonbox.addButton(savebutton, QDialogButtonBox.ActionRole)
        savebutton.clicked.connect(self._save_to_csv)
        layout.addWidget(buttonbox)
        buttonbox.rejected.connect(self.reject)

        # set initial sort and size
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.resize(800, 550)

    def populate_model(self, raw):
        cols, nchan = calculate_channel_stats(raw)
        headers = [
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

        self.model = QStandardItemModel(nchan, len(headers))
        self.model.setHorizontalHeaderLabels(headers)

        for i in range(nchan):
            # Channel
            item = QStandardItem()
            item.setData(i, Qt.UserRole)
            item.setData(i, Qt.DisplayRole)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.model.setItem(i, 0, item)

            # Name
            item = QStandardItem(cols["name"][i])
            item.setFlags(Qt.ItemIsEnabled)
            self.model.setItem(i, 1, item)

            # Type
            item = QStandardItem(cols["type"][i].upper())
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model.setItem(i, 2, item)

            # Unit
            item = QStandardItem(cols["unit"][i])
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model.setItem(i, 3, item)

            # Numeric columns (Min, Q1, Mean, Median, Q3, Max)
            for j, key in enumerate(
                ["min", "Q1", "mean", "median", "Q3", "max"], start=4
            ):
                value = cols[key][i]
                item = QStandardItem()
                item.setData(f"{value:.2f}", Qt.DisplayRole)
                item.setData(value, Qt.UserRole)
                item.setFlags(Qt.ItemIsEnabled)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.model.setItem(i, j, item)

    def _save_to_csv(self):
        """Save channel statistics to a CSV file."""
        # determine starting directory
        if ChannelStats._last_directory is not None:
            start_dir = ChannelStats._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Channel Statistics",
            str(
                Path(start_dir)
                / f"channel_stats_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.csv"
            ),
            "CSV Files (*.csv);;All Files (*)",
        )

        if filename:
            filename = str(Path(filename).with_suffix(".csv"))
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)

                # write header
                headers = [
                    self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
                    for col in range(self.model.columnCount())
                ]
                writer.writerow(headers)

                # write data rows with full precision for numeric columns
                for row in range(self.model.rowCount()):
                    row_data = []
                    for col in range(self.model.columnCount()):
                        item = self.model.item(row, col)
                        user_data = item.data(Qt.UserRole)
                        if user_data is not None and isinstance(
                            user_data, (int, float)
                        ):
                            row_data.append(user_data)
                        else:
                            row_data.append(item.data(Qt.DisplayRole))
                    writer.writerow(row_data)

            ChannelStats._last_directory = str(Path(filename).parent)
