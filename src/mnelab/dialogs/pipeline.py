# © MNELAB developers
#
# License: BSD (3-clause)

"""Review and reuse processing steps recorded on a dataset."""

from copy import deepcopy
from pathlib import Path

import mne
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from mnelab.model import (
    read_bad_channels,
    read_imported_annotations,
    read_imported_events,
)
from mnelab.pipeline import (
    FILE_IMPORTS,
    has_unsupported,
    load_pipeline,
    make_file_spec,
    resolve_file_spec,
    save_pipeline,
    serialize_montage,
    step_label,
    validate_file_spec,
)
from mnelab.settings import read_settings, write_settings
from mnelab.utils import Montage


class FileRuleDialog(QDialog):
    """Edit a file path rule and preview it for the selected dataset."""

    def __init__(self, parent, spec, source_fname=None, *, embed_label=None):
        super().__init__(parent)
        self.setWindowTitle("File Rule")
        self.source_fname = source_fname
        self.embed_label = embed_label
        self.embedded_data = spec.get("data")
        layout = QVBoxLayout(self)
        self.matching_radio = QRadioButton("Matching file for each dataset")
        self.fixed_radio = QRadioButton(
            f"Embed {embed_label} in pipeline" if embed_label else "Fixed file"
        )
        modes = QButtonGroup(self)
        modes.addButton(self.matching_radio)
        modes.addButton(self.fixed_radio)
        self.matching_radio.setChecked(spec["mode"] == "matching")
        self.fixed_radio.setChecked(spec["mode"] != "matching")
        layout.addWidget(self.matching_radio)
        matching_row = QHBoxLayout()
        matching_row.addSpacing(24)
        matching_fields = QVBoxLayout()
        data_label = QLabel("Dataset filename")
        self.data_pattern = QLineEdit(spec.get("data_pattern", ""))
        data_label.setBuddy(self.data_pattern)
        self.data_pattern.setPlaceholderText("{id}.fif")
        matching_fields.addWidget(data_label)
        matching_fields.addWidget(self.data_pattern)
        file_label = QLabel("Matching file")
        self.file_pattern = QLineEdit(spec.get("file_pattern", ""))
        file_label.setBuddy(self.file_pattern)
        self.file_pattern.setPlaceholderText("{id}-bad_channels.csv")
        matching_fields.addWidget(file_label)
        matching_fields.addWidget(self.file_pattern)
        matching_row.addLayout(matching_fields, stretch=1)
        layout.addLayout(matching_row)
        layout.addWidget(self.fixed_radio)
        fixed_row = QHBoxLayout()
        fixed_row.addSpacing(24)
        fixed_path = spec.get("path", "")
        if not fixed_path and source_fname and spec["mode"] == "matching":
            try:
                fixed_path = str(
                    resolve_file_spec(spec, source_fname, check_exists=False)
                )
            except ValueError:
                pass
        self.fixed_path = QLineEdit(fixed_path)
        fixed_row.addWidget(self.fixed_path)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse)
        fixed_row.addWidget(self.browse_button)
        layout.addLayout(fixed_row)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttons)
        self.matching_radio.toggled.connect(self._refresh)
        self.data_pattern.textChanged.connect(self._refresh)
        self.file_pattern.textChanged.connect(self._refresh)
        self.fixed_path.textChanged.connect(self._refresh)
        self.resize(720, 300)
        self._refresh()

    def file_spec(self):
        """Return the edited file rule."""
        if self.matching_radio.isChecked():
            return {
                "mode": "matching",
                "data_pattern": self.data_pattern.text().strip(),
                "file_pattern": self.file_pattern.text().strip(),
            }
        path = self.fixed_path.text().strip()
        if self.embed_label and not path and self.embedded_data is not None:
            return {"mode": "embedded", "data": self.embedded_data}
        return {"mode": "fixed", "path": path}

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", self.fixed_path.text() or read_settings("last_dir")
        )
        if path:
            self.fixed_path.setText(path)
            suggestion = make_file_spec(path, self.source_fname)
            if suggestion["mode"] == "matching":
                self.data_pattern.setText(suggestion["data_pattern"])
                self.file_pattern.setText(suggestion["file_pattern"])

    def _refresh(self):
        matching = self.matching_radio.isChecked()
        self.data_pattern.setEnabled(matching)
        self.file_pattern.setEnabled(matching)
        self.fixed_path.setEnabled(not matching)
        self.browse_button.setEnabled(not matching)
        try:
            spec = self.file_spec()
            validate_file_spec(spec)
        except (TypeError, ValueError) as error:
            self.preview.setText(str(error))
            self.ok_button.setEnabled(False)
            return
        if spec["mode"] == "embedded":
            self.preview.setText("Contents are stored in the pipeline.")
            self.ok_button.setEnabled(True)
            return
        self.ok_button.setEnabled(True)
        try:
            path = resolve_file_spec(spec, self.source_fname, check_exists=False)
        except ValueError as error:
            self.preview.setText(f"Preview unavailable: {error}")
        else:
            status = "Found" if path.is_file() else "Missing"
            self.preview.setText(f"{status} for selected dataset: {path}")
            if self.embed_label and not path.is_file():
                self.ok_button.setEnabled(False)


class PipelineDialog(QDialog):
    """Reorder, remove, save, or load recorded processing steps."""

    def __init__(self, parent, steps, source_name=None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline")
        self.steps = deepcopy(steps)
        self.source_name = source_name
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
        self.file_rule_button = QPushButton("File Rule...")
        self.file_rule_button.clicked.connect(self._edit_file_rule)
        row.addWidget(self.file_rule_button)
        row.addStretch()
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear)
        row.addWidget(self.clear_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        load_button = QPushButton("Load...")
        load_button.clicked.connect(self._load)
        row.addWidget(load_button)
        self.save_button = QPushButton("Save...")
        self.save_button.clicked.connect(self._save)
        row.addWidget(self.save_button)
        row.addStretch()
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
        self.file_rule_button.setEnabled(
            selected and self._file_spec_for_step(self.steps[row]) is not None
        )
        self.clear_button.setEnabled(bool(self.steps))
        ready = bool(self.steps) and not has_unsupported(self.steps)
        self.save_button.setEnabled(ready)

    def _file_spec_for_step(self, step):
        if step.get("unsupported"):
            return None
        if step["op"] in FILE_IMPORTS:
            return step["params"]["file"]
        if step["op"] == "set_montage":
            positions = step["params"]["montage_positions"]
            if isinstance(positions, dict):
                if "file" in positions:
                    return positions["file"]
                return {"mode": "embedded", "data": positions}
        return None

    def _selected_source_fname(self):
        parent = self.parent()
        if parent is None or not hasattr(parent, "model"):
            return None
        current = parent.model.current
        return (
            current.get("source_fname") or current.get("fname")
            if current is not None
            else None
        )

    def _edit_file_rule(self):
        row = self.list.currentRow()
        if row < 0:
            return
        step = self.steps[row]
        spec = self._file_spec_for_step(step)
        if spec is None:
            return
        source_fname = self._selected_source_fname()
        embed_label = (
            None
            if step["op"] == "import_ica"
            else "montage coordinates"
            if step["op"] == "set_montage"
            else "contents"
        )
        dialog = FileRuleDialog(self, spec, source_fname, embed_label=embed_label)
        if spec["mode"] == "fixed" and spec["path"] and source_fname:
            suggestion = make_file_spec(spec["path"], source_fname)
            if suggestion["mode"] == "matching":
                dialog.data_pattern.setText(suggestion["data_pattern"])
                dialog.file_pattern.setText(suggestion["file_pattern"])
        if step["op"] == "set_montage" and spec["mode"] == "embedded":
            parent = self.parent()
            current = (
                parent.model.current
                if parent is not None and hasattr(parent, "model")
                else None
            )
            montage = current.get("montage") if current is not None else None
            if (
                montage is not None
                and montage.path is not None
                and montage.name == step["params"]["montage_name"]
                and (self.source_name is None or current["name"] == self.source_name)
            ):
                suggestion = make_file_spec(montage.path, source_fname)
                if suggestion["mode"] == "matching":
                    dialog.data_pattern.setText(suggestion["data_pattern"])
                    dialog.file_pattern.setText(suggestion["file_pattern"])
        if dialog.exec():
            new_spec = dialog.file_spec()
            if new_spec["mode"] == "fixed" and embed_label:
                path = new_spec["path"]
                try:
                    if step["op"] == "import_bads":
                        data = read_bad_channels(path)
                    elif step["op"] == "import_events":
                        data = read_imported_events(path)
                    elif step["op"] == "import_annotations":
                        params = step["params"]
                        data = read_imported_annotations(
                            path, params["types"], params["description"]
                        )
                    else:
                        montage = Montage(
                            mne.channels.read_custom_montage(path), Path(path).name
                        )
                        params = step["params"]
                        serialized = serialize_montage(
                            {
                                "montage": montage,
                                "match_case": params["match_case"],
                                "match_alias": params["match_alias"],
                                "on_missing": params["on_missing"],
                            }
                        )
                        data = serialized["montage_positions"]
                        params["montage_name"] = montage.name
                except Exception as error:
                    QMessageBox.warning(self, "Could Not Embed File", str(error))
                    return
                new_spec = {"mode": "embedded", "data": data}
            if step["op"] == "set_montage":
                step["params"]["montage_positions"] = (
                    {"file": new_spec}
                    if new_spec["mode"] == "matching"
                    else new_spec["data"]
                )
            else:
                step["params"]["file"] = new_spec
            self._refresh(row)

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
