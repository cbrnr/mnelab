# © MNELAB developers
#
# License: BSD (3-clause)

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from mnelab.utils import PythonHighlighter, format_code


class HistoryDialog(QDialog):
    _last_directory = None  # track last used directory

    def __init__(self, parent, history):
        super().__init__(parent=parent)
        self.setWindowTitle("History")
        self.history = format_code(history)

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
        text.setPlainText(self.history)
        layout.addWidget(text)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        clipboardbutton = QPushButton("Copy to clipboard")
        savebutton = QPushButton("Save to file...")
        buttonbox.addButton(clipboardbutton, QDialogButtonBox.ActionRole)
        buttonbox.addButton(savebutton, QDialogButtonBox.ActionRole)
        clipboard = QGuiApplication.clipboard()
        clipboardbutton.clicked.connect(lambda: clipboard.setText(self.history))
        savebutton.clicked.connect(self._save_to_file)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)

    def _save_to_file(self):
        """Save history to a file."""
        # determine starting directory
        if HistoryDialog._last_directory is not None:
            start_dir = HistoryDialog._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save History",
            str(Path(start_dir) / f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.py"),
            "Python Files (*.py);;All Files (*)",
        )

        if filename:
            filename = str(Path(filename).with_suffix(".py"))
            with open(filename, "w", encoding="utf-8") as f:
                f.write(format_code(self.history))
                f.write("\n")
            HistoryDialog._last_directory = str(Path(filename).parent)
