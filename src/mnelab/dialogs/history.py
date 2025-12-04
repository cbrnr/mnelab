# © MNELAB developers
#
# License: BSD (3-clause)

import subprocess
import sys

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from mnelab.utils import PythonHighlighter


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

        formatted_history = self._format_with_ruff(history)
        text.setPlainText(formatted_history)

        layout.addWidget(text)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        clipboardbutton = QPushButton("Copy to clipboard")
        buttonbox.addButton(clipboardbutton, QDialogButtonBox.ActionRole)
        clipboard = QGuiApplication.clipboard()
        clipboardbutton.clicked.connect(lambda: clipboard.setText(formatted_history))
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(700, 500)

    def _format_with_ruff(self, code):
        """Format Python code using ruff (fall back to original if unavailable)."""
        try:
            result = subprocess.run(
                ["ruff", "format", "-"],
                input=code,
                text=True,
                capture_output=True,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return code
