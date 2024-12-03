# © MNELAB developers
#
# License: BSD (3-clause)
import os

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QPushButton,
    QTableWidget,
)

ROW_HEIGHT = 10


class SidebarTableWidget(QTableWidget):
    rowsMoved = Signal(int, int)  # custom signal emitted, when drag&dropping rows

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(False)
        self.setDragDropOverwriteMode(False)
        self.setFrameStyle(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.setColumnCount(3)
        self.setShowGrid(False)
        self.drop_row = -1

        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, 20)
        self.resizeColumnToContents(0)

        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        elif event.source() == self:
            event.accept()
            super().dragEnterEvent(event)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        elif event.source() == self:
            drop_row = self.indexAt(event.pos()).row()
            if drop_row == -1:
                drop_row = self.rowCount()
            if drop_row != self.drop_row:
                self.drop_row = drop_row
            event.accept()
            super().dragMoveEvent(event)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drop_row >= 0:
            painter = QPainter(self.viewport())
            if self.drop_row < self.rowCount():
                y = self.visualRect(self.model().index(self.drop_row, 0)).top()
            else:
                y = self.visualRect(self.model().index(self.rowCount() - 1, 0)).bottom()
            painter.drawLine(0, y, self.viewport().width(), y)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.parent.model.load(file_path)

        elif event.source() == self:
            drop_row = self.indexAt(event.pos()).row()
            if drop_row == -1:
                drop_row = self.rowCount()
            selected_rows = sorted(
                index.row() for index in self.selectionModel().selectedRows()
            )
            if selected_rows and drop_row > selected_rows[-1]:
                drop_row -= len(selected_rows)

            self.drop_row = -1
            self.viewport().update()
            self.rowsMoved.emit(selected_rows[0], drop_row)
            event.setDropAction(Qt.IgnoreAction)
            event.accept()
        else:
            event.ignore()

    def style_rows(self):
        self.resizeColumnToContents(0)
        for i in range(self.rowCount()):
            self.resizeRowToContents(i)
            self.setRowHeight(i, ROW_HEIGHT)
            self.item(i, 0).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.item(i, 0).setForeground(QColor("gray"))
            self.item(i, 0).setFlags(self.item(i, 0).flags() & ~Qt.ItemIsEditable)
            self.item(i, 1).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.item(i, 1).setFlags(self.item(i, 1).flags() | Qt.ItemIsEditable)

    def update_vertical_header(self):
        row_count = self.rowCount()
        self.setVerticalHeaderLabels([str(i) for i in range(row_count)])

    def eventFilter(self, source, event):
        if source == self.viewport() and event.type() == QEvent.MouseMove:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.showCloseButton(index.row())
        return False

    def showCloseButton(self, row_index):
        for i in range(self.rowCount()):
            if i == row_index:
                delete_button = QPushButton(self)
                delete_button.setIcon(QIcon.fromTheme("close-data"))
                delete_button.setStyleSheet(
                    "background: transparent; border: none; margin: auto;"
                )
                delete_button.clicked.connect(
                    lambda _, index=row_index: self.parent.model.remove_data(index)
                )
                self.setCellWidget(row_index, 2, delete_button)
            else:
                self.removeCellWidget(i, 2)
