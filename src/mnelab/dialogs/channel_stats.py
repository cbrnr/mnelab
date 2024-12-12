# © MNELAB developers
#
# License: BSD (3-clause)
from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ChannelStats(QDialog):
    def __init__(self, parent, data):
        super().__init__(parent=parent)

        # window
        self.setWindowTitle("Channel Stats")
        self.resize(690, 800)
        self.setMinimumSize(200, 150)
        self.setMaximumWidth(690)
        layout = QVBoxLayout(self)

        # table widget
        self.table = QTableWidget()
        self.table.setRowCount(len(data))
        self.table.setColumnCount(len(data.columns))
        self.table.setHorizontalHeaderLabels(data.columns)

        # populate table
        for row in range(len(data)):
            for col in range(len(data.columns)):
                item = QTableWidgetItem(str(data.iloc[row, col]))
                self.table.setItem(row, col, item)

        self.table.resizeColumnToContents(0)  # name
        self.table.resizeColumnToContents(1)  # type
        self.table.resizeColumnToContents(2)  # unit
        layout.addWidget(self.table)

        # add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)
