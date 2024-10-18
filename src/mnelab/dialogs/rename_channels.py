# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class RenameChannelsDialog(QDialog):
    def __init__(self, parent, channels):
        super().__init__(parent)
        self.setWindowTitle("Rename channels")

        self.old_names = channels

        self.method = QComboBox()
        self.method.addItems(["Strip characters", "Delete characters"])
        self.method.setCurrentIndex(0)

        self.strip_chars = QLineEdit()
        self.slice_num = QDoubleSpinBox()
        self.slice_num.setMinimum(0)
        self.slice_num.setDecimals(0)

        self.where = QComboBox()
        self.where.addItems(["from beginning", "from end"])
        self.where.setCurrentIndex(0)

        option_grid = QGridLayout()
        option_grid.setColumnStretch(0, 1)
        option_grid.setColumnStretch(1, 1)
        option_grid.setColumnStretch(2, 1)
        option_grid.addWidget(self.method, 0, 0)
        option_grid.addWidget(self.strip_chars, 0, 1)
        option_grid.addWidget(self.slice_num, 0, 1)
        option_grid.addWidget(self.where, 0, 2)

        self.preview = QTableWidget(len(channels), 2)
        self.preview.setHorizontalHeaderLabels(["Before", "After"])
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.verticalHeader().setVisible(False)
        self.preview.setShowGrid(False)
        self.preview.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview.setColumnWidth(0, 190)
        self.preview.setColumnWidth(1, 190)
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview.setSelectionMode(QTableWidget.NoSelection)
        self.preview.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(self)
        vbox.addLayout(option_grid)
        vbox.addSpacing(10)
        vbox.addWidget(self.preview)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.method.currentTextChanged.connect(self.toggle_input)
        self.method.currentTextChanged.connect(self.update_preview)
        self.where.currentTextChanged.connect(self.update_preview)
        self.strip_chars.textEdited.connect(self.update_preview)
        self.slice_num.valueChanged.connect(self.update_preview)

        self.toggle_input()
        self.update_preview()
        self.setFixedSize(450, 450)

    @Slot()
    def toggle_input(self):
        if self.method.currentText() == "Strip characters":
            self.strip_chars.setVisible(True)
            self.slice_num.setVisible(False)
        elif self.method.currentText() == "Delete characters":
            self.strip_chars.setVisible(False)
            self.slice_num.setVisible(True)

    @Slot()
    def update_preview(self):
        if self.method.currentText() == "Strip characters":
            if self.where.currentText() == "from beginning":
                new_names = [n.lstrip(self.strip_chars.text()) for n in self.old_names]
            else:
                new_names = [n.rstrip(self.strip_chars.text()) for n in self.old_names]

        else:
            if self.where.currentText() == "from beginning":
                new_names = [n[int(self.slice_num.value()) :] for n in self.old_names]
            else:
                if self.slice_num.value() > 0:
                    new_names = [
                        n[: -int(self.slice_num.value())] for n in self.old_names
                    ]
                else:
                    new_names = self.old_names[:]

        self.new_names = new_names
        for row, (old, new) in enumerate(zip(self.old_names, self.new_names)):
            self.preview.setItem(row, 0, QTableWidgetItem(old))
            self.preview.setItem(row, 1, QTableWidgetItem(new))
