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
    QTabWidget,
    QVBoxLayout,
)

from mnelab.utils import PythonHighlighter, format_code


class HistoryDialog(QDialog):
    _last_directory = None  # track last used directory

    def __init__(self, parent, history, log):
        super().__init__(parent=parent)
        self.setWindowTitle("History")
        self.history = format_code("\n".join(history))
        self.log = "\n".join(log)

        font = QFont()
        if sys.platform.startswith("darwin"):
            fontname = "menlo"
        elif sys.platform.startswith("win32"):
            fontname = "consolas"
        else:
            fontname = "monospace"
        font.setFamily(fontname)
        font.setStyleHint(QFont.Monospace)

        history_text = QPlainTextEdit()
        history_text.setFont(font)
        highlighter = PythonHighlighter(history_text.document())  # noqa: F841
        history_text.setReadOnly(True)
        history_text.setPlainText(self.history)

        log_text = QPlainTextEdit()
        log_text.setFont(font)
        log_text.setReadOnly(True)
        log_text.setPlainText(self.log)

        self.tabs = QTabWidget()
        self.tabs.addTab(history_text, "History")
        self.tabs.addTab(log_text, "MNE Log")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.clipboardbutton = QPushButton("Copy to clipboard")
        self.savebutton = QPushButton("Save to file...")
        buttonbox.addButton(self.clipboardbutton, QDialogButtonBox.ActionRole)
        buttonbox.addButton(self.savebutton, QDialogButtonBox.ActionRole)
        self.clipboardbutton.clicked.connect(self._copy_to_clipboard)
        self.savebutton.clicked.connect(self._save_to_file)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)

    def _copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        if self.tabs.currentIndex() == 0:
            clipboard.setText(self.history)
        else:
            clipboard.setText(self.log)

    def _save_to_file(self):
        if self.tabs.currentIndex() == 0:
            self._save_history()
        else:
            self._save_log()

    def _save_history(self):
        """Save history to a file."""
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

    def _save_log(self):
        """Save MNE log to a file."""
        if HistoryDialog._last_directory is not None:
            start_dir = HistoryDialog._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save MNE Log",
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
            HistoryDialog._last_directory = str(Path(filename).parent)
