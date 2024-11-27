# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QPushButton,
    QTableWidget,
)


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
        self.setColumnCount(2)
        self.setShowGrid(False)
        self.drop_row = -1

        self.horizontalHeader().hide()
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.setColumnWidth(1, 20)

        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        event.accept()
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        drop_row = self.indexAt(event.pos()).row()
        if drop_row == -1:
            drop_row = self.rowCount()
        if drop_row != self.drop_row:
            self.drop_row = drop_row
            self.viewport().update()
        event.accept()
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.drop_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drop_row >= 0:
            painter = QPainter(self.viewport())
            pen = QPen(QColor("black"))
            pen.setWidth(1.5)
            painter.setPen(pen)
            if self.drop_row < self.rowCount():
                rect = self.visualRect(self.model().index(self.drop_row, 0))
                y = rect.top()
            else:
                last_row_rect = self.visualRect(
                    self.model().index(self.rowCount() - 1, 0)
                )
                y = last_row_rect.bottom()
            painter.drawLine(0, y, self.viewport().width(), y)

    def dropEvent(self, event):
        if event.source() == self:
            drop_row = self.indexAt(event.pos()).row()
            if drop_row == -1:
                drop_row = self.rowCount()
            selected_rows = sorted(set(index.row() for index in self.selectedIndexes()))
            if selected_rows and drop_row > selected_rows[-1]:
                drop_row -= len(selected_rows)

            self.drop_row = -1
            self.viewport().update()
            self.rowsMoved.emit(selected_rows[0], drop_row)
            event.setDropAction(Qt.IgnoreAction)
            event.accept()

        else:
            event.ignore()

    def styleRows(self):
        for i in range(self.rowCount()):
            self.resizeRowToContents(i)
            self.setRowHeight(i, 10)
        self.update_vertical_header()

    def update_vertical_header(self):
        row_count = self.rowCount()
        self.setVerticalHeaderLabels([str(i) for i in range(row_count)])

    def eventFilter(self, source, event):
        if source == self.viewport() and event.type() == QEvent.MouseMove:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.showCloseButton(index.row())

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
                self.setCellWidget(row_index, 1, delete_button)
            else:
                self.removeCellWidget(i, 1)
