from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QTableView, QHeaderView, QStyledItemDelegate)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class ChannelPropertiesDialog(QDialog):
    def __init__(self, parent, info, title="Channel Properties"):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.model = QStandardItemModel(info["nchan"], 4)
        self.model.setHorizontalHeaderLabels(["#", "Label", "Type", "Bad"])
        for index, ch in enumerate(info["chs"]):
            item = QStandardItem()
            item.setData(index, Qt.DisplayRole)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.model.setItem(index, 0, item)
            self.model.setItem(index, 1, QStandardItem(ch["ch_name"]))
            self.model.setItem(index, 2, QStandardItem(str(ch["kind"])))
            bad = QStandardItem()
            bad.setData(ch["ch_name"] in info["bads"], Qt.CheckStateRole)
            self.model.setItem(index, 3, bad)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.view.setShowGrid(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.resizeColumnsToContents()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.resize(400, 650)
