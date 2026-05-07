# © MNELAB developers
#
# License: BSD (3-clause)

"""Pipeline Builder dialog.

Lets users view, edit, reorder and save a .mnepipe pipeline, and
optionally inspect the dataset's Python history.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mnelab.model import PIPELINE_EXECUTION_MODES
from mnelab.utils import PythonHighlighter, format_code
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

    def __init__(
        self,
        parent=None,
        pipeline_dict: dict | None = None,
        history: list[str] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Pipeline")
        self.setMinimumSize(560, 440)
        self._pipeline = pipeline_dict or {
            "pipeline_format": 1,
            "mnelab_version": "unknown",
            "created": datetime.now().isoformat(),
            "hints": {},
            "steps": [],
        }

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        # --- Pipeline tab ---
        pipeline_tab = QWidget()
        pipeline_layout = QVBoxLayout(pipeline_tab)
        pipeline_layout.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setSpacing(2)
        pipeline_layout.addWidget(self._list)

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
        pipeline_layout.addLayout(step_btn_row)

        self._tabs.addTab(pipeline_tab, "Pipeline")

        # --- History tab (optional) ---
        if history is not None:
            history_tab = QWidget()
            history_layout = QVBoxLayout(history_tab)
            history_layout.setContentsMargins(0, 0, 0, 0)

            self._history_text = QPlainTextEdit()
            font = QFont()
            font.setFamily(
                "Menlo"
                if sys.platform == "darwin"
                else "Consolas"
                if sys.platform == "win32"
                else "Monospace"
            )
            font.setStyleHint(QFont.StyleHint.Monospace)
            self._history_text.setFont(font)
            fm = QFontMetrics(font)
            min_w = fm.horizontalAdvance("x") * 90 + 60  # 60 for margins + scrollbar
            if min_w > self.minimumWidth():
                self.setMinimumWidth(min_w)
            self._history_text.setReadOnly(True)
            self._history_text.setPlainText(format_code("\n".join(history)))
            PythonHighlighter(self._history_text.document())

            copy_btn = QPushButton("Copy to clipboard")
            copy_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            copy_btn.clicked.connect(self._copy_history)

            history_layout.addWidget(self._history_text)
            history_layout.addWidget(copy_btn)
            self._tabs.addTab(history_tab, "History")
        else:
            self._history_text = None

        layout.addWidget(self._tabs)

        self._add_btn.clicked.connect(self._add_step)
        self._edit_btn.clicked.connect(self._edit_step)
        self._del_btn.clicked.connect(self._remove_step)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)
        self._list.currentRowChanged.connect(self._update_step_buttons)
        self._list.model().rowsInserted.connect(self._update_step_buttons)
        self._list.model().rowsRemoved.connect(self._update_step_buttons)

        # bottom buttons
        bb = QDialogButtonBox()
        self._open_btn = bb.addButton("Open…", QDialogButtonBox.ButtonRole.ActionRole)
        self._save_btn = bb.addButton("Save…", QDialogButtonBox.ButtonRole.ActionRole)
        self._apply_btn = bb.addButton("Apply…", QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = bb.addButton(QDialogButtonBox.StandardButton.Close)

        self._open_btn.clicked.connect(self._load_pipeline)
        self._apply_btn.clicked.connect(self.accept)
        self._save_btn.clicked.connect(self._save_pipeline)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(bb)

        self._rebuild_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._update_step_buttons()

    # ------------------------------------------------------------------
    # list helpers
    # ------------------------------------------------------------------

    def _rebuild_list(self):
        self._list.clear()
        for step in self._pipeline.get("steps", []):
            op = step.get("operation", "")
            params = step.get("params")
            label = _operation_label(op, params)
            execution_mode = step.get("execution_mode", "automatic")
            if execution_mode != "automatic":
                label = f"{label}  [{execution_mode.title()}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, step)
            self._list.addItem(item)

    def _current_row(self) -> int:
        return self._list.currentRow()

    def _sync_order(self):
        """Sync steps list order to the current list widget order."""
        steps = [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        self._pipeline["steps"] = steps

    def _update_step_buttons(self, *_):
        """Enable/disable step action buttons based on current selection."""
        row = self._current_row()
        count = self._list.count()
        has_selection = row >= 0
        self._edit_btn.setEnabled(has_selection)
        self._del_btn.setEnabled(has_selection)
        self._up_btn.setEnabled(has_selection and row > 0)
        self._down_btn.setEnabled(has_selection and row < count - 1)
        self._save_btn.setEnabled(count > 0)
        self._apply_btn.setEnabled(count > 0)

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
            self._update_step_buttons()

    def _edit_step(self):
        row = self._current_row()
        if row < 0:
            return
        step = self._list.item(row).data(Qt.ItemDataRole.UserRole)
        dlg = _StepEditorDialog(step, self)
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
        self._update_step_buttons()

    def _move_up(self):
        row = self._current_row()
        if row <= 0:
            return
        self._sync_order()
        steps = self._pipeline["steps"]
        steps.insert(row - 1, steps.pop(row))
        self._rebuild_list()
        self._list.setCurrentRow(row - 1)
        self._update_step_buttons()

    def _move_down(self):
        row = self._current_row()
        if row < 0 or row >= self._list.count() - 1:
            return
        self._sync_order()
        steps = self._pipeline["steps"]
        steps.insert(row + 1, steps.pop(row))
        self._rebuild_list()
        self._list.setCurrentRow(row + 1)
        self._update_step_buttons()

    # ------------------------------------------------------------------
    # file I/O
    # ------------------------------------------------------------------

    def _load_pipeline(self):
        from mnelab.dialogs.pipeline import load_pipeline

        start = PipelineBuilderDialog._last_directory or str(Path.home())
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open pipeline",
            start,
            "Pipeline files (*.mnepipe);;All files (*)",
        )
        if fname:
            try:
                pipeline = load_pipeline(fname)
            except (ValueError, KeyError) as e:
                QMessageBox.critical(self, "Invalid pipeline file", str(e))
                return
            self._pipeline = pipeline
            self._rebuild_list()
            self._update_step_buttons()
            PipelineBuilderDialog._last_directory = str(Path(fname).parent)

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

    def _copy_history(self):
        """Copy the history text to the clipboard."""
        if self._history_text is not None:
            QGuiApplication.clipboard().setText(self._history_text.toPlainText())

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def get_pipeline(self) -> dict:
        """Return the current (possibly modified) pipeline dict."""
        self._sync_order()
        return self._pipeline

    def show_history_tab(self):
        """Switch to the History tab (if present)."""
        history_index = self._tabs.indexOf(
            self._history_text.parent() if self._history_text is not None else None
        )
        if history_index >= 0:
            self._tabs.setCurrentIndex(history_index)
