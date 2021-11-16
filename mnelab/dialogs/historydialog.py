# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QPlainTextEdit, QPushButton,
                             QVBoxLayout)

from ..utils import PythonHighlighter


class HistoryDialog(QDialog):
    def __init__(self, parent, history):
        super().__init__(parent=parent)
        self.setWindowTitle("History")
        layout = QVBoxLayout()
        text = QPlainTextEdit()
        font = QFont()
        font.setFamily("monospace")
        font.setStyleHint(QFont.Monospace)
        text.setFont(font)
        highlighter = PythonHighlighter(text.document())  # noqa: F841
        text.setReadOnly(True)
        text.setPlainText(history)
        layout.addWidget(text)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        clipboardbutton = QPushButton("Copy to clipboard")
        buttonbox.addButton(clipboardbutton, QDialogButtonBox.ActionRole)
        clipboard = QGuiApplication.clipboard()
        clipboardbutton.clicked.connect(lambda: clipboard.setText(history + "\n"))
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(700, 500)
