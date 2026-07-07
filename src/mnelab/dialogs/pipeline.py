# © MNELAB developers
#
# License: BSD (3-clause)

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from mnelab.pipeline import (
    has_unsupported,
    is_supported,
    pipeline_from_dict,
    pipeline_to_dict,
    step_label,
    step_summary,
)
from mnelab.settings import read_settings, write_settings


class PipelineDialog(QDialog):
    """Dialog to view, edit, save, and load a processing pipeline."""

    def __init__(self, parent, steps, source_name=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Pipeline")
        self.steps = deepcopy(steps)  # edit a copy; caller reads back on accept
        self.source_name = source_name

        vbox = QVBoxLayout(self)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        vbox.addWidget(self.info_label)

        hbox = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._update_buttons)
        hbox.addWidget(self.list, 1)

        button_vbox = QVBoxLayout()
        self.up_button = QPushButton("↑")
        self.down_button = QPushButton("↓")
        self.remove_button = QPushButton("Remove")
        self.clear_button = QPushButton("Clear")
        for button in (self.up_button, self.down_button, self.remove_button):
            button.setEnabled(False)
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button.clicked.connect(lambda: self._move(1))
        self.remove_button.clicked.connect(self._remove)
        self.clear_button.clicked.connect(self._clear)
        button_vbox.addWidget(self.up_button)
        button_vbox.addWidget(self.down_button)
        button_vbox.addSpacing(8)
        button_vbox.addWidget(self.remove_button)
        button_vbox.addWidget(self.clear_button)
        button_vbox.addStretch()
        hbox.addLayout(button_vbox)
        vbox.addLayout(hbox)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.load_button = QPushButton("Load...")
        self.save_button = QPushButton("Save...")
        buttonbox.addButton(self.load_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttonbox.addButton(self.save_button, QDialogButtonBox.ButtonRole.ActionRole)
        self.load_button.clicked.connect(self._load)
        self.save_button.clicked.connect(self._save)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.addWidget(buttonbox)

        self.resize(500, 360)
        self._populate()

    def _populate(self):
        self.list.clear()
        for step in self.steps:
            summary = step_summary(step)
            text = step_label(step)
            if summary:
                text += f"  ({summary})"
            item = QListWidgetItem(text)
            if not is_supported(step):
                item.setText("⚠ " + text)
                item.setToolTip("This operation cannot be reproduced automatically.")
            self.list.addItem(item)
        if not self.steps:
            self.info_label.setText("The pipeline is empty.")
        elif has_unsupported(self.steps):
            self.info_label.setText(
                "⚠ This pipeline contains operations that cannot be reproduced "
                "(marked below). It cannot be applied until they are removed."
            )
        else:
            source = f" from “{self.source_name}”" if self.source_name else ""
            self.info_label.setText(
                f"{len(self.steps)} step(s){source}. Reorder, remove, save, or load."
            )
        self._update_buttons()

    def _update_buttons(self, *_):
        row = self.list.currentRow()
        has_selection = row >= 0
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row < len(self.steps) - 1)
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(bool(self.steps))
        self.save_button.setEnabled(bool(self.steps))

    def _move(self, offset):
        row = self.list.currentRow()
        target = row + offset
        if 0 <= row < len(self.steps) and 0 <= target < len(self.steps):
            self.steps[row], self.steps[target] = self.steps[target], self.steps[row]
            self._populate()
            self.list.setCurrentRow(target)

    def _remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.steps):
            del self.steps[row]
            self._populate()
            self.list.setCurrentRow(min(row, len(self.steps) - 1))

    def _clear(self):
        self.steps = []
        self._populate()

    def _save(self):
        start_dir = read_settings("last_dir") or str(Path.home())
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Pipeline",
            str(
                Path(start_dir) / f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.json"
            ),
            "Pipeline Files (*.json);;All Files (*)",
        )
        if filename:
            filename = str(Path(filename).with_suffix(".json"))
            document = pipeline_to_dict(self.steps, self.source_name)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(document, f, indent=2)
            write_settings(last_dir=str(Path(filename).parent))

    def _load(self):
        start_dir = read_settings("last_dir") or str(Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Pipeline",
            start_dir,
            "Pipeline Files (*.json);;All Files (*)",
        )
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8") as f:
                document = json.load(f)
            steps = pipeline_from_dict(document)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Could not load pipeline", str(e))
            return
        self.steps = steps
        self.source_name = document.get("source")
        write_settings(last_dir=str(Path(filename).parent))
        self._populate()
