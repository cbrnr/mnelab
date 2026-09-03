# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from mnelab.dialogs.utils import set_header_alignments
from mnelab.widgets import FlatDoubleSpinBox


class RenameChannelsDialog(QDialog):
    def __init__(self, parent, channels):
        super().__init__(parent)
        self.setWindowTitle("Rename Channels")

        self.old_names = channels

        self.method = QComboBox()
        self.method.addItems(["Strip characters", "Delete characters"])
        self.method.setCurrentIndex(0)
        self.method.setToolTip("Choose how to remove characters from channel names")

        self.strip_chars = QLineEdit()
        self.strip_chars.setToolTip("Enter characters to strip from channel names")
        self.slice_num = FlatDoubleSpinBox()
        self.slice_num.setMinimum(0)
        self.slice_num.setDecimals(0)
        self.slice_num.setToolTip(
            "Set the number of characters to remove from channel names"
        )

        self.where = QComboBox()
        self.where.addItems(["from beginning", "from end"])
        self.where.setCurrentIndex(0)
        self.where.setToolTip(
            "Choose whether to remove characters from the beginning or end of channel "
            "names"
        )

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
        set_header_alignments(self.preview, "ll")
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.verticalHeader().setVisible(False)
        self.preview.setShowGrid(False)
        self.preview.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview.setColumnWidth(0, 190)
        self.preview.setColumnWidth(1, 190)
        self.preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        vbox = QVBoxLayout(self)
        vbox.addLayout(option_grid)
        vbox.addSpacing(10)
        header_font = QFont(QApplication.font())
        header_font.setPointSizeF(header_font.pointSizeF() * 0.85)
        header_font.setBold(True)
        preview_header = QLabel("Preview")
        preview_header.setFont(header_font)
        vbox.addWidget(preview_header)
        vbox.addWidget(self.preview)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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
        self.setFocus()

    @property
    def mapping(self):
        """Return the selected channel renaming function."""
        if self.method.currentText() == "Strip characters":
            chars = self.strip_chars.text()
            if self.where.currentText() == "from beginning":
                return lambda name: name.lstrip(chars)
            return lambda name: name.rstrip(chars)

        num = int(self.slice_num.value())
        if self.where.currentText() == "from beginning":
            return lambda name: name[num:]
        if num > 0:
            return lambda name: name[:-num]
        return lambda name: name[:]

    @property
    def history_mapping(self):
        """Return the selected channel renaming function as history code."""
        if self.method.currentText() == "Strip characters":
            method = (
                "lstrip" if self.where.currentText() == "from beginning" else "rstrip"
            )
            return f"lambda name: name.{method}({self.strip_chars.text()!r})"

        num = int(self.slice_num.value())
        if self.where.currentText() == "from beginning":
            return f"lambda name: name[{num}:]"
        if num > 0:
            return f"lambda name: name[:-{num}]"
        return "lambda name: name[:]"

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
        self.new_names = [self.mapping(name) for name in self.old_names]
        for row, (old, new) in enumerate(zip(self.old_names, self.new_names)):
            self.preview.setItem(row, 0, QTableWidgetItem(old))
            self.preview.setItem(row, 1, QTableWidgetItem(new))
