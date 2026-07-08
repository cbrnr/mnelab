# © MNELAB developers
#
# License: BSD (3-clause)

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
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

    def __init__(
        self, parent, steps, source_name=None, dataset_steps=None, dataset_name=None
    ):
        super().__init__(parent=parent)
        self.setWindowTitle("Pipeline")
        self.steps = deepcopy(steps)  # edit a copy; caller reads back on accept
        self.source_name = source_name
        self.dataset_steps = dataset_steps  # steps of the currently selected data set
        self.dataset_name = dataset_name

        vbox = QVBoxLayout(self)

        hbox = QHBoxLayout()
        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._update_buttons)
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

        if self.dataset_name:
            elided = QFontMetrics(self.font()).elidedText(
                self.dataset_name, Qt.TextElideMode.ElideMiddle, 160
            )
            create_label = f'Create from "{elided}"'
        else:
            create_label = "Create from Dataset"
        self.create_button = QPushButton(create_label)
        self.create_button.setEnabled(bool(self.dataset_steps))
        if not self.dataset_steps:
            self.create_button.setToolTip(
                "The selected data set has no reproducible steps."
            )
        elif self.dataset_name:
            self.create_button.setToolTip(
                f'Create a pipeline from "{self.dataset_name}"'
            )
        self.create_button.clicked.connect(self._create_from_dataset)

        self.load_button = QPushButton("Load...")
        self.save_button = QPushButton("Save...")
        self.load_button.clicked.connect(self._load)
        self.save_button.clicked.connect(self._save)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addWidget(self.create_button)
        bottom_hbox.addWidget(self.load_button)
        bottom_hbox.addWidget(self.save_button)
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(buttonbox)
        vbox.addLayout(bottom_hbox)

        self.resize(650, 400)
        self._populate()

    def _populate(self):
        self.list.clear()
        for i, step in enumerate(self.steps, start=1):
            summary = step_summary(step)
            text = f"{i}. {step_label(step)}"
            if summary:
                text += f"  ({summary})"
            item = QListWidgetItem(text)
            if not is_supported(step):
                item.setText(f"⚠ {text}")
                item.setToolTip("This operation cannot be reproduced automatically.")
            self.list.addItem(item)
        self._update_buttons()

    def _update_buttons(self, *_):
        row = self.list.currentRow()
        has_selection = bool(self.list.selectedItems())
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row < len(self.steps) - 1)
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(bool(self.steps))
        self.save_button.setEnabled(bool(self.steps) and not has_unsupported(self.steps))
        if self.steps and has_unsupported(self.steps):
            self.save_button.setToolTip(
                "The pipeline contains non-reproducible steps and cannot be saved."
            )
        else:
            self.save_button.setToolTip("")

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

    def _create_from_dataset(self):
        if self.steps:  # guard against clobbering unsaved edits
            reply = QMessageBox.question(
                self,
                "Replace pipeline?",
                f"Replace the current pipeline with the "
                f'{len(self.dataset_steps)} step(s) from "{self.dataset_name}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.steps = deepcopy(self.dataset_steps)
        self.source_name = self.dataset_name
        self._populate()

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
