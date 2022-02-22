# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
)


class XDFStreamsDialog(QDialog):
    def __init__(self, parent, rows, fname, selected=None, disabled=None):
        super().__init__(parent)
        self.setWindowTitle("Select XDF Stream")
        self.fname = fname

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["ID", "Name", "Type", "Channels", "Format",
                                              "Sampling Rate"])

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
        hbox = QHBoxLayout()
        self._effective_srate = QCheckBox("Use effective sampling rate")
        self._effective_srate.setChecked(True)
        hbox.addWidget(self._effective_srate)
        self._prefix_markers = QCheckBox("Prefix markers with stream ID")
        self._prefix_markers.setChecked(False)
        if len(disabled) < 2:
            self._prefix_markers.setEnabled(False)
        hbox.addWidget(self._prefix_markers)
        self.details_button = QPushButton("Details")
        self.details_button.clicked.connect(self.details)
        hbox.addWidget(self.details_button)
        vbox.addLayout(hbox)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.resize(775, 650)
        self.view.setColumnWidth(0, 90)
        self.view.setColumnWidth(1, 200)
        self.view.setColumnWidth(2, 140)

    @property
    def effective_srate(self):
        return self._effective_srate.isChecked()

    @property
    def prefix_markers(self):
        return self._prefix_markers.isChecked()

    def details(self):
        self.parent().xdf_metadata(self.fname)
