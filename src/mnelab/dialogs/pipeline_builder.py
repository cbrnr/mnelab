# © MNELAB developers
#
# License: BSD (3-clause)

"""Pipeline Builder dialog.

Lets users view, edit, reorder and save a .mnepipe pipeline, and export it
as a Python script.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mnelab.dialogs.pipeline import load_pipeline
from mnelab.model import PIPELINE_EXECUTION_MODES
from mnelab.widgets.pipeline_tree import _OP_LABELS, _operation_label

# ---------------------------------------------------------------------------
# Step editor sub-dialog
# ---------------------------------------------------------------------------


class _StepEditorDialog(QDialog):
    """Edit a single pipeline step dict."""

    def __init__(self, step: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit step")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._op_combo = QComboBox()
        for key, label in sorted(_OP_LABELS.items(), key=lambda kv: kv[1]):
            self._op_combo.addItem(label, key)
        idx = self._op_combo.findData(step.get("operation", ""))
        if idx >= 0:
            self._op_combo.setCurrentIndex(idx)
        form.addRow("Operation:", self._op_combo)

        self._name_edit = QLineEdit(step.get("name", ""))
        self._name_edit.setPlaceholderText("Leave empty to auto-generate label")
        form.addRow("Label:", self._name_edit)

        self._mode_combo = QComboBox()
        mode = step.get("execution_mode", "automatic")
        for execution_mode in PIPELINE_EXECUTION_MODES:
            self._mode_combo.addItem(execution_mode.title(), execution_mode)
        mode_index = self._mode_combo.findData(mode)
        if mode_index >= 0:
            self._mode_combo.setCurrentIndex(mode_index)
        form.addRow("Execution mode:", self._mode_combo)

        layout.addLayout(form)

        params_box = QGroupBox(
            'Parameters (JSON dict, e.g. {"lower": 1.0, "upper": 40.0})'
        )
        params_layout = QVBoxLayout(params_box)
        self._params_edit = QTextEdit()
        self._params_edit.setFont(
            QFont("Consolas" if sys.platform == "win32" else "Monospace")
        )
        self._params_edit.setPlainText(json.dumps(step.get("params") or {}, indent=2))
        self._params_edit.setFixedHeight(90)
        params_layout.addWidget(self._params_edit)
        layout.addWidget(params_box)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _on_accept(self):
        try:
            json.loads(self._params_edit.toPlainText() or "{}")
        except json.JSONDecodeError as exc:
            QMessageBox.warning(
                self, "Invalid JSON", f"Parameters are not valid JSON:\n{exc}"
            )
            return
        self.accept()

    def get_step(self) -> dict:
        params = json.loads(self._params_edit.toPlainText() or "{}")
        operation = self._op_combo.currentData()
        name = self._name_edit.text().strip()
        if not name:
            name = _operation_label(operation, params)
        step = {"operation": operation, "name": name, "params": params}
        execution_mode = self._mode_combo.currentData()
        if execution_mode != "automatic":
            step["execution_mode"] = execution_mode
        return step


# ---------------------------------------------------------------------------
# Step row widget (displayed inside the QListWidget)
# ---------------------------------------------------------------------------


class _StepRowWidget(QWidget):
    def __init__(self, step: dict, parent=None):
        super().__init__(parent)
        self.step = step
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)

        op = step.get("operation", "")
        params = step.get("params")
        label = _operation_label(op, params)
        row.addWidget(QLabel(label), stretch=1)
        execution_mode = step.get("execution_mode", "automatic")
        if execution_mode != "automatic":
            mode_label = QLabel(execution_mode.title())
            mode_label.setStyleSheet("color: #6b7280;")
            row.addWidget(mode_label)


# ---------------------------------------------------------------------------
# Main Pipeline Builder dialog
# ---------------------------------------------------------------------------


class PipelineBuilderDialog(QDialog):
    """View and edit a .mnepipe pipeline before applying or saving it.

    Parameters
    ----------
    parent :
        Parent widget (MainWindow).
    pipeline_dict :
        Existing pipeline dict to edit. If None, starts with an empty pipeline.
    """

    _last_directory: str | None = None

    def __init__(self, parent=None, pipeline_dict: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Builder")
        self.setMinimumSize(560, 440)
        self._pipeline = pipeline_dict or {
            "pipeline_format": 1,
            "mnelab_version": "unknown",
            "created": datetime.now().isoformat(),
            "hints": {},
            "steps": [],
        }

        layout = QVBoxLayout(self)

        # step list
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setSpacing(2)
        layout.addWidget(self._list)

        # step action buttons
        step_btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add step…")
        self._edit_btn = QPushButton("Edit…")
        self._del_btn = QPushButton("Remove")
        self._up_btn = QPushButton("▲")
        self._down_btn = QPushButton("▼")
        for btn in (
            self._add_btn,
            self._edit_btn,
            self._del_btn,
            self._up_btn,
            self._down_btn,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            step_btn_row.addWidget(btn)
        step_btn_row.addStretch()
        layout.addLayout(step_btn_row)

        self._add_btn.clicked.connect(self._add_step)
        self._edit_btn.clicked.connect(self._edit_step)
        self._del_btn.clicked.connect(self._remove_step)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)

        # bottom buttons
        bb = QDialogButtonBox()
        self._save_btn = bb.addButton(
            "Save pipeline…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._load_btn = bb.addButton(
            "Load pipeline…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._export_btn = bb.addButton(
            "Export Python script…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._apply_btn = bb.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        close_btn = bb.addButton(QDialogButtonBox.StandardButton.Close)

        self._save_btn.clicked.connect(self._save_pipeline)
        self._load_btn.clicked.connect(self._load_pipeline)
        self._export_btn.clicked.connect(self._export_python)
        self._apply_btn.clicked.connect(self.accept)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(bb)

        self._rebuild_list()

    # ------------------------------------------------------------------
    # list helpers
    # ------------------------------------------------------------------

    def _rebuild_list(self):
        self._list.clear()
        for step in self._pipeline.get("steps", []):
            item = QListWidgetItem(self._list)
            widget = _StepRowWidget(step)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _current_row(self) -> int:
        return self._list.currentRow()

    def _sync_order(self):
        """Sync steps list order to the current list widget order."""
        steps = []
        for i in range(self._list.count()):
            widget = self._list.itemWidget(self._list.item(i))
            steps.append(widget.step)
        self._pipeline["steps"] = steps

    # ------------------------------------------------------------------
    # step CRUD
    # ------------------------------------------------------------------

    def _add_step(self):
        dlg = _StepEditorDialog({"operation": "filter", "params": {}}, self)
        if dlg.exec():
            step = dlg.get_step()
            self._pipeline.setdefault("steps", []).append(step)
            self._rebuild_list()
            self._list.setCurrentRow(self._list.count() - 1)

    def _edit_step(self):
        row = self._current_row()
        if row < 0:
            return
        widget = self._list.itemWidget(self._list.item(row))
        dlg = _StepEditorDialog(widget.step, self)
        if dlg.exec():
            new_step = dlg.get_step()
            self._pipeline["steps"][row] = new_step
            self._rebuild_list()
            self._list.setCurrentRow(row)

    def _remove_step(self):
        row = self._current_row()
        if row < 0:
            return
        self._sync_order()
        del self._pipeline["steps"][row]
        self._rebuild_list()
        self._list.setCurrentRow(min(row, self._list.count() - 1))

    def _move_up(self):
        row = self._current_row()
        if row <= 0:
            return
        self._sync_order()
        steps = self._pipeline["steps"]
        steps.insert(row - 1, steps.pop(row))
        self._rebuild_list()
        self._list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self._current_row()
        if row < 0 or row >= self._list.count() - 1:
            return
        self._sync_order()
        steps = self._pipeline["steps"]
        steps.insert(row + 1, steps.pop(row))
        self._rebuild_list()
        self._list.setCurrentRow(row + 1)

    # ------------------------------------------------------------------
    # file I/O
    # ------------------------------------------------------------------

    def _save_pipeline(self):
        start = PipelineBuilderDialog._last_directory or str(Path.home())
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Save pipeline",
            start,
            "Pipeline files (*.mnepipe);;All files (*)",
        )
        if fname:
            if not fname.endswith(".mnepipe"):
                fname += ".mnepipe"
            self._sync_order()
            Path(fname).write_text(
                json.dumps(self._pipeline, indent=2), encoding="utf-8"
            )
            PipelineBuilderDialog._last_directory = str(Path(fname).parent)

    def _load_pipeline(self):
        start = PipelineBuilderDialog._last_directory or str(Path.home())
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Load pipeline",
            start,
            "Pipeline files (*.mnepipe);;All files (*)",
        )
        if fname:
            try:
                self._pipeline = load_pipeline(fname)
            except Exception as exc:
                QMessageBox.critical(self, "Could not load pipeline", str(exc))
                return
            self._rebuild_list()
            PipelineBuilderDialog._last_directory = str(Path(fname).parent)

    def _export_python(self):
        start = PipelineBuilderDialog._last_directory or str(Path.home())
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Export Python script",
            start,
            "Python files (*.py);;All files (*)",
        )
        if fname:
            if not fname.endswith(".py"):
                fname += ".py"
            self._sync_order()
            Path(fname).write_text(self._to_python_script(), encoding="utf-8")
            PipelineBuilderDialog._last_directory = str(Path(fname).parent)

    def _to_python_script(self) -> str:
        lines = [
            "import mne",
            "",
            "# Load your data here",
            "# raw = mne.io.read_raw_fif('your_file.fif', preload=True)",
            "",
        ]
        for step in self._pipeline.get("steps", []):
            op = step.get("operation", "")
            params = step.get("params") or {}
            execution_mode = step.get("execution_mode", "automatic")
            label = _operation_label(op, params)
            if execution_mode == "skip":
                lines.append(f"# Skipped: {label}")
                continue
            if execution_mode in {"prompt", "review"}:
                lines.append(f"# {execution_mode.title()} checkpoint: {label}")
            if op == "filter":
                lower = params.get("lower")
                upper = params.get("upper")
                notch = params.get("notch")
                if notch:
                    lines.append(f"raw.notch_filter({notch!r})")
                else:
                    lines.append(f"raw.filter({lower!r}, {upper!r})")
            elif op == "crop":
                lines.append(
                    f"raw.crop({params.get('start')!r}, {params.get('stop')!r})"
                )
            elif op == "pick_channels":
                lines.append(f"raw.pick({params.get('picks')!r})")
            elif op == "set_montage":
                montage = params.get("montage")
                if isinstance(montage, dict):
                    montage = montage.get("name")
                if montage:
                    lines.append(f"raw.set_montage({montage!r})")
            elif op == "change_reference":
                lines.append(f"raw.set_eeg_reference({params.get('ref')!r})")
            else:
                lines.append(f"# {op}({params!r})")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def get_pipeline(self) -> dict:
        """Return the current (possibly modified) pipeline dict."""
        self._sync_order()
        return self._pipeline
