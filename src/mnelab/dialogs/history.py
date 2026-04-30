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


class LogDialog(QDialog):
    """Show the MNE log messages."""

    _last_directory = None  # track last used directory

    def __init__(self, parent, log):
        super().__init__(parent=parent)
        self.setWindowTitle("Log")
        self.log = "\n".join(log)

        font = QFont()
        if sys.platform.startswith("darwin"):
            fontname = "menlo"
        elif sys.platform.startswith("win32"):
            fontname = "consolas"
        else:
            fontname = "monospace"
        font.setFamily(fontname)
        font.setStyleHint(QFont.StyleHint.Monospace)

        log_text = QPlainTextEdit()
        log_text.setFont(font)
        log_text.setReadOnly(True)
        log_text.setPlainText(self.log)

        layout = QVBoxLayout()
        layout.addWidget(log_text)

        buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.clipboardbutton = QPushButton("Copy to clipboard")
        self.savebutton = QPushButton("Save to file...")
        buttonbox.addButton(
            self.clipboardbutton, QDialogButtonBox.ButtonRole.ActionRole
        )
        buttonbox.addButton(self.savebutton, QDialogButtonBox.ButtonRole.ActionRole)
        self.clipboardbutton.clicked.connect(self._copy_to_clipboard)
        self.savebutton.clicked.connect(self._save_log)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)
        self.setFocus()

    def _copy_to_clipboard(self):
        QGuiApplication.clipboard().setText(self.log)

    def _save_log(self):
        """Save MNE log to a file."""
        if LogDialog._last_directory is not None:
            start_dir = LogDialog._last_directory
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
            LogDialog._last_directory = str(Path(filename).parent)


# backward-compatibility alias
HistoryDialog = LogDialog
