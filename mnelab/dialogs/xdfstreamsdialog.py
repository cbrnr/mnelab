from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox,
                             QAbstractItemView, QTableView)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class XDFStreamsDialog(QDialog):
    def __init__(self, parent, rows, selected=None, disabled=None):
        super().__init__(parent)
        self.setWindowTitle("Select XDF Stream")

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["ID", "Name", "Type", "Channels",
                                              "Format", "Sampling Rate"])

        for index, stream in enumerate(rows):
            items = []
            for item in stream:
                tmp = QStandardItem()
                tmp.setData(item, Qt.DisplayRole)
                items.append(tmp)
            for item in items:
                item.setEditable(False)
                if disabled is not None and index in disabled:
                    item.setFlags(Qt.NoItemFlags)
            self.model.appendRow(items)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        if selected is not None:
            self.view.selectRow(selected)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.resize(750, 650)
        self.view.setColumnWidth(0, 80)
        self.view.setColumnWidth(1, 200)
        self.view.setColumnWidth(2, 120)
