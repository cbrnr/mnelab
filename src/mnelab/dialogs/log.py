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


class LoggingDialog(QDialog):
    _last_directory = None  # track last used directory

    def __init__(self, parent, log):
        super().__init__(parent=parent)
        self.setWindowTitle("Log")
        self.log = "\n".join(log)

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
        text.setReadOnly(True)
        text.setPlainText(self.log)
        layout.addWidget(text)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        clipboardbutton = QPushButton("Copy to clipboard")
        savebutton = QPushButton("Save to file...")
        buttonbox.addButton(clipboardbutton, QDialogButtonBox.ActionRole)
        buttonbox.addButton(savebutton, QDialogButtonBox.ActionRole)
        clipboard = QGuiApplication.clipboard()
        clipboardbutton.clicked.connect(lambda: clipboard.setText(self.log))
        savebutton.clicked.connect(self._save_to_file)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)

    def _save_to_file(self):
        """Save log to a file."""
        if LoggingDialog._last_directory is not None:
            start_dir = LoggingDialog._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Log",
            str(
                Path(start_dir)
                / f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}-mne-log.txt"
            ),
            "Text Files (*.txt);;All Files (*)",
        )

        if filename:
            filename = str(Path(filename).with_suffix(".txt"))
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log)
                f.write("\n")
            LoggingDialog._last_directory = str(Path(filename).parent)
