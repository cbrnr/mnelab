# © MNELAB developers
#
# License: BSD (3-clause)

import sys

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from mnelab.utils import PythonHighlighter, format_code


class HistoryDialog(QDialog):
    def __init__(self, parent, history):
        super().__init__(parent=parent)
        self.setWindowTitle("History")
        layout = QVBoxLayout()
        text = QPlainTextEdit()
        font = QFont()
        if sys.platform.startswith("darwin"):
            fontname = "menlo"
        elif sys.platform.startswith("win32"):
            fontname = "consolas"
        else:
            fontname = "monospace"
        font.setFamily(fontname)
        font.setStyleHint(QFont.Monospace)
        text.setFont(font)
        highlighter = PythonHighlighter(text.document())  # noqa: F841
        text.setReadOnly(True)
        history = format_code(history)
        text.setPlainText(history)
        layout.addWidget(text)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        clipboardbutton = QPushButton("Copy to clipboard")
        buttonbox.addButton(clipboardbutton, QDialogButtonBox.ActionRole)
        clipboard = QGuiApplication.clipboard()
        clipboardbutton.clicked.connect(lambda: clipboard.setText(history))
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)
