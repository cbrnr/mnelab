# © MNELAB developers
#
# License: BSD (3-clause)

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mnelab.utils import PythonHighlighter, format_code


class HistoryDialog(QDialog):
    _last_directory = None  # track last used directory

    def __init__(self, parent, history, log, pipeline=None, scope="branch"):
        super().__init__(parent=parent)
        self.scope = "dataset" if scope == "dataset" else "branch"
        self.scope_title = "Dataset" if self.scope == "dataset" else "Branch"
        self.setWindowTitle(f"{self.scope_title} History")
        self.history = format_code("\n".join(history))
        self.log = "\n".join(log)
        self.pipeline = pipeline or {
            "pipeline_format": 1,
            "created": "",
            "hints": {},
            "steps": [],
        }

        font = QFont()
        if sys.platform.startswith("darwin"):
            fontname = "menlo"
        elif sys.platform.startswith("win32"):
            fontname = "consolas"
        else:
            fontname = "monospace"
        font.setFamily(fontname)
        font.setStyleHint(QFont.StyleHint.Monospace)

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

        self.pipeline_list = QListWidget()
        self.pipeline_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        for i, step in enumerate(self.pipeline.get("steps", []), start=1):
            label = step.get("name") or step.get("operation", "Step")
            self.pipeline_list.addItem(f"{i}. {label}")

        pipeline_tab = QWidget()
        pipeline_layout = QVBoxLayout(pipeline_tab)
        scope_text = "dataset history" if self.scope == "dataset" else "branch"
        pipeline_layout.addWidget(
            QLabel(
                f"Select steps from this {scope_text} to seed the Pipeline Builder. "
                "If nothing is selected, all steps are used."
            )
        )
        if self.pipeline.get("steps"):
            pipeline_layout.addWidget(self.pipeline_list)
        else:
            empty_label = QLabel(
                f"No replayable pipeline steps available for this {self.scope} yet."
            )
            empty_label.setWordWrap(True)
            pipeline_layout.addWidget(empty_label)
        self.tabs.addTab(pipeline_tab, f"{self.scope_title} pipeline")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)

        buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.clipboardbutton = QPushButton("Copy to clipboard")
        self.savebutton = QPushButton("Save to file...")
        self.pipelinebutton = QPushButton(f"Create pipeline from {self.scope}...")
        buttonbox.addButton(
            self.clipboardbutton, QDialogButtonBox.ButtonRole.ActionRole
        )
        buttonbox.addButton(self.savebutton, QDialogButtonBox.ButtonRole.ActionRole)
        buttonbox.addButton(self.pipelinebutton, QDialogButtonBox.ButtonRole.ActionRole)
        self.clipboardbutton.clicked.connect(self._copy_to_clipboard)
        self.savebutton.clicked.connect(self._save_to_file)
        self.pipelinebutton.clicked.connect(self._create_pipeline)
        self.tabs.currentChanged.connect(self._update_action_buttons)
        self.pipeline_list.itemSelectionChanged.connect(self._update_action_buttons)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(750, 500)
        self.setFocus()
        self._update_action_buttons()

    def _current_pipeline(self):
        if not self.pipeline:
            return None

        selected_rows = sorted(
            index.row() for index in self.pipeline_list.selectionModel().selectedRows()
        )
        pipeline = deepcopy(self.pipeline)
        if selected_rows:
            pipeline["steps"] = [pipeline["steps"][row] for row in selected_rows]
        return pipeline

    def _update_action_buttons(self):
        is_pipeline_tab = self.tabs.currentIndex() == 2
        has_steps = bool(self.pipeline.get("steps"))
        self.pipelinebutton.setEnabled(is_pipeline_tab and has_steps)
        self.clipboardbutton.setEnabled(True)
        self.savebutton.setEnabled(True)

    def _copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        if self.tabs.currentIndex() == 0:
            clipboard.setText(self.history)
        elif self.tabs.currentIndex() == 1:
            clipboard.setText(self.log)
        else:
            pipeline = self._current_pipeline()
            if pipeline is not None:
                clipboard.setText(json.dumps(pipeline, indent=2))

    def _save_to_file(self):
        if self.tabs.currentIndex() == 0:
            self._save_history()
        elif self.tabs.currentIndex() == 1:
            self._save_log()
        else:
            self._save_pipeline()

    def _save_history(self):
        """Save history to a file."""
        if HistoryDialog._last_directory is not None:
            start_dir = HistoryDialog._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {self.scope_title} History",
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

    def _save_pipeline(self):
        """Save the selected pipeline steps to a file."""
        pipeline = self._current_pipeline()
        if pipeline is None or not pipeline.get("steps"):
            return

        if HistoryDialog._last_directory is not None:
            start_dir = HistoryDialog._last_directory
        else:
            start_dir = str(Path.home())

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {self.scope_title} Pipeline",
            str(
                Path(start_dir)
                / f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.mnepipe"
            ),
            "MNELAB pipeline (*.mnepipe);;All Files (*)",
        )

        if filename:
            filename = str(Path(filename).with_suffix(".mnepipe"))
            with open(filename, "w", encoding="utf-8") as f:
                f.write(json.dumps(pipeline, indent=2))
                f.write("\n")
            HistoryDialog._last_directory = str(Path(filename).parent)

    def _create_pipeline(self):
        """Open the selected history steps in the Pipeline Builder."""
        pipeline = self._current_pipeline()
        if pipeline is None or not pipeline.get("steps"):
            return

        from mnelab.dialogs.pipeline_builder import PipelineBuilderDialog

        parent = self.parent()
        dialog = PipelineBuilderDialog(parent, pipeline)
        if dialog.exec() and hasattr(parent, "_confirm_and_apply_pipeline"):
            parent._confirm_and_apply_pipeline(dialog.get_pipeline())
