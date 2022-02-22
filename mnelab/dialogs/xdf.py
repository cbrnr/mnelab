# © MNELAB developers
#
# License: BSD (3-clause)

import xml.etree.ElementTree as ETree

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
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
        self.parent().show_xdf_information(self.fname)


def populate_tree(parent, node):
    item = QTreeWidgetItem(parent)
    item.setText(0, node.tag.strip())
    if node.text is not None and node.text.strip():
        item.setText(1, node.text.strip())
    for element in node:
        populate_tree(item, element)


class XDFInfoDialog(QDialog):
    def __init__(self, parent, xml):
        super().__init__(parent)
        self.setWindowTitle("XDF information")

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Name", "Value"])
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 350)

        for stream in xml:
            header = xml[stream][2]
            header.tag = "Header"
            footer = xml[stream][6]
            footer.tag = "Footer"

            root = ETree.Element(f"Stream {stream}")
            root.extend([header, footer])
            populate_tree(tree, root)

        tree.expandAll()

        vbox = QVBoxLayout(self)
        vbox.addWidget(tree)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)

        self.resize(650, 550)


def _add_item(item):
    tmp = QStandardItem()
    tmp.setData(item, Qt.DisplayRole)
    return tmp


class XDFChunksDialog(QDialog):
    def __init__(self, parent, chunks, fname):
        super().__init__(parent)
        self.setWindowTitle(f"XDF Chunks ({fname})")

        self.chunks = chunks

        TAGS = {1: "FileHeader", 2: "StreamHeader", 3: "Samples", 4: "ClockOffset",
                5: "Boundary", 6: "StreamFooter"}

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["#", "Bytes", "Tag", "Stream ID"])

        for i, chunk in enumerate(chunks, start=1):
            row = []
            row.append(_add_item(i))
            row.append(_add_item(chunk["nbytes"]))
            row.append(_add_item(f"{chunk['tag']} ({TAGS[chunk['tag']]})"))
            row.append(_add_item(chunk.get("stream_id", "")))
            self.model.appendRow(row)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.setEditTriggers(QTableView.NoEditTriggers)
        self.view.selectRow(0)
        self.view.setFixedWidth(450)

        self.details = QPlainTextEdit("")
        self.details.setFixedWidth(450)
        self.details.setReadOnly(True)
        self.details.setTabStopDistance(30)
        font = QFont()
        font.setFamily("monospace")
        font.setStyleHint(QFont.Monospace)
        self.details.setFont(font)
        self.details.setLineWrapMode(QPlainTextEdit.NoWrap)

        hbox = QHBoxLayout()
        hbox.addWidget(self.view)
        hbox.addWidget(self.details)

        vbox = QVBoxLayout(self)
        vbox.addLayout(hbox)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Close)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.rejected.connect(self.reject)

        self.view.clicked.connect(self._update_details)
        self._update_details()

        self.setFixedSize(980, 650)
        self.view.setColumnWidth(0, 70)
        self.view.setColumnWidth(1, 80)
        self.view.setColumnWidth(2, 150)
        self.view.setColumnWidth(3, 70)

    @Slot()
    def _update_details(self):
        selection = self.view.selectionModel()
        if selection.hasSelection():
            n = int(selection.selectedIndexes()[0].data())
            self.details.setPlainText(self.chunks[n - 1].get("content", ""))
