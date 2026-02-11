# © MNELAB developers
#
# License: BSD (3-clause)

from xml.dom import minidom

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPlainTextEdit,
    QTableView,
    QVBoxLayout,
)


def _add_item(item):
    tmp = QStandardItem()
    tmp.setData(item, Qt.DisplayRole)
    return tmp


class XDFChunksDialog(QDialog):
    def __init__(self, parent, chunks, fname):
        super().__init__(parent)
        self.setWindowTitle(f"XDF Chunks ({fname})")

        self.chunks = chunks

        TAGS = {
            1: "FileHeader",
            2: "StreamHeader",
            3: "Samples",
            4: "ClockOffset",
            5: "Boundary",
            6: "StreamFooter",
        }

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
            content = self.chunks[n - 1].get("content", "")
            # prettify XML chunks
            try:
                prettified = minidom.parseString(content).toprettyxml(indent="  ")
                lines = [line for line in prettified.split("\n") if line.strip()]
                content = "\n".join(lines)
            except Exception:
                pass  # Not XML or invalid XML, use original content

            self.details.setPlainText(content)
