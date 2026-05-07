# © MNELAB developers
#
# License: BSD (3-clause)

import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class DatasetDetailsDialog(QDialog):
    """Show dataset provenance details."""

    datasetSelected = Signal(int)

    def __init__(self, parent, details):
        super().__init__(parent=parent)
        self.setWindowTitle("Dataset Details")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)

        row = 0
        generated_code = details.get("Generated code", "-")
        parent_index = details.get("_parent_dataset_index")

        for key, value in details.items():
            if key.startswith("_") or key == "Generated code":
                continue
            left = QLabel(f"{key}:")
            right = QLabel(str(value))
            right.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            right.setWordWrap(True)
            right.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )
            grid.addWidget(left, row, 0)
            grid.addWidget(right, row, 1)

            if key == "Parent dataset" and parent_index is not None and value != "-":
                jump_button = QPushButton("Jump")
                jump_button.setToolTip("Jump to parent dataset")
                jump_button.clicked.connect(
                    lambda checked=False, idx=parent_index: self.datasetSelected.emit(
                        idx
                    )
                )
                grid.addWidget(jump_button, row, 2)

            row += 1

        layout.addLayout(grid)

        layout.addWidget(QLabel("Generated code:"))
        code = QPlainTextEdit()
        font = QFont()
        if sys.platform.startswith("darwin"):
            font.setFamily("menlo")
        elif sys.platform.startswith("win32"):
            font.setFamily("consolas")
        else:
            font.setFamily("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        code.setFont(font)
        code.setReadOnly(True)
        code.setPlainText(str(generated_code))
        layout.addWidget(code)

        buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttonbox.accepted.connect(self.accept)
        layout.addWidget(buttonbox)
