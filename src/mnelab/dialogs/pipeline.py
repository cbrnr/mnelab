# © MNELAB developers
#
# License: BSD (3-clause)

"""Review and reuse processing steps recorded on a dataset."""

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
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

from mnelab.pipeline import has_unsupported, load_pipeline, save_pipeline, step_label
from mnelab.settings import read_settings, write_settings


class PipelineDialog(QDialog):
    """Reorder, remove, save, load, or apply recorded processing steps."""

    APPLY = 2

    def __init__(self, parent, steps, source_name=None, can_apply=True):
        super().__init__(parent)
        self.setWindowTitle("Pipeline")
        self.steps = deepcopy(steps)
        self.source_name = source_name
        self.can_apply = can_apply
        layout = QVBoxLayout(self)
        self.note = QLabel()
        self.note.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.note)

        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.list)

        row = QHBoxLayout()
        self.up_button = QPushButton("Move Up")
        self.up_button.clicked.connect(lambda: self._move(-1))
        row.addWidget(self.up_button)
        self.down_button = QPushButton("Move Down")
        self.down_button.clicked.connect(lambda: self._move(1))
        row.addWidget(self.down_button)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove)
        row.addWidget(self.remove_button)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear)
        row.addWidget(self.clear_button)
        row.addStretch()
        layout.addLayout(row)

        row = QHBoxLayout()
        load_button = QPushButton("Load...")
        load_button.clicked.connect(self._load)
        row.addWidget(load_button)
        self.save_button = QPushButton("Save...")
        self.save_button.clicked.connect(self._save)
        row.addWidget(self.save_button)
        row.addStretch()
        self.apply_button = QPushButton("Apply to Selected Dataset")
        self.apply_button.clicked.connect(lambda: self.done(self.APPLY))
        row.addWidget(self.apply_button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)

        self.resize(620, 380)
        self._refresh()

    def _refresh(self, selected=None):
        self.note.setText(
            f"Steps from {self.source_name} run in order on a new dataset."
            if self.source_name
            else "Steps run in order on a new copy of the selected dataset."
        )
        self.list.clear()
        for number, step in enumerate(self.steps, 1):
            item = QListWidgetItem(f"{number}. {step_label(step)}")
            if step.get("unsupported"):
                item.setText(f"⚠ {item.text()}")
                item.setToolTip("Remove this step before saving or applying.")
            self.list.addItem(item)
        if selected is not None and self.steps:
            self.list.setCurrentRow(min(selected, len(self.steps) - 1))
        self._update_buttons()

    def _update_buttons(self):
        row = self.list.currentRow()
        selected = 0 <= row < len(self.steps)
        self.up_button.setEnabled(selected and row > 0)
        self.down_button.setEnabled(selected and row < len(self.steps) - 1)
        self.remove_button.setEnabled(selected)
        self.clear_button.setEnabled(bool(self.steps))
        ready = bool(self.steps) and not has_unsupported(self.steps)
        self.save_button.setEnabled(ready)
        self.apply_button.setEnabled(ready and self.can_apply)

    def _remove(self):
        row = self.list.currentRow()
        if row >= 0:
            del self.steps[row]
            self._refresh(row)

    def _clear(self):
        self.steps.clear()
        self._refresh()

    def _move(self, offset):
        row = self.list.currentRow()
        target = row + offset
        if 0 <= row < len(self.steps) and 0 <= target < len(self.steps):
            self.steps[row], self.steps[target] = self.steps[target], self.steps[row]
            self._refresh(target)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Pipeline",
            read_settings("last_dir"),
            "Pipeline Files (*.json)",
        )
        if not path:
            return
        try:
            self.steps = load_pipeline(path)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(self, "Could Not Load Pipeline", str(error))
            return
        self.source_name = Path(path).name
        write_settings(last_dir=str(Path(path).parent))
        self._refresh()

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Pipeline",
            read_settings("last_dir"),
            "Pipeline Files (*.json)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".json"
            if Path(path).exists():
                choice = QMessageBox.question(
                    self, "Overwrite Pipeline?", f"Overwrite {Path(path).name}?"
                )
                if choice != QMessageBox.StandardButton.Yes:
                    return
        try:
            save_pipeline(path, self.steps)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Could Not Save Pipeline", str(error))
            return
        write_settings(last_dir=str(Path(path).parent))
