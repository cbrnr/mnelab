# © MNELAB developers
#
# License: BSD (3-clause)

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressDialog,
    QVBoxLayout,
)

from mnelab.model import PIPELINE_EXECUTION_MODES, UNREPLAYABLE_PIPELINE_OPS
from mnelab.widgets.pipeline_tree import _operation_label


def _unreplayable_operations(pipeline_dict):
    """Return unreplayable operation names used by a pipeline."""
    return [
        step.get("operation")
        for step in pipeline_dict.get("steps", [])
        if step.get("operation") in UNREPLAYABLE_PIPELINE_OPS
    ]


def validate_pipeline(pipeline_dict):
    """Validate the basic .mnepipe structure.

    Parameters
    ----------
    pipeline_dict : dict
        Pipeline dictionary loaded from JSON or built by the Pipeline Builder.

    Raises
    ------
    ValueError
        If required top-level fields or step fields are malformed.
    """
    if not isinstance(pipeline_dict, dict):
        raise ValueError("Pipeline file must contain a JSON object.")
    if pipeline_dict.get("pipeline_format") != 1:
        raise ValueError(
            "Unsupported pipeline format version: "
            f"{pipeline_dict.get('pipeline_format')!r}"
        )
    steps = pipeline_dict.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Pipeline field 'steps' must be a list.")
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Pipeline step {index} must be a JSON object.")
        operation = step.get("operation")
        if not isinstance(operation, str) or not operation:
            raise ValueError(f"Pipeline step {index} has no operation name.")
        params = step.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"Pipeline step {index} params must be a JSON object.")
        execution_mode = step.get("execution_mode", "automatic")
        if execution_mode not in PIPELINE_EXECUTION_MODES:
            raise ValueError(
                f"Pipeline step {index} has invalid execution mode: {execution_mode!r}."
            )
    return pipeline_dict


class ApplyPipelineDialog(QDialog):
    """Show pipeline summary and compatibility hints before applying."""

    def __init__(self, parent, pipeline_dict, current_dataset):
        super().__init__(parent=parent)
        self.setWindowTitle("Apply Pipeline")
        self.resize(480, 400)

        layout = QVBoxLayout()

        hints = pipeline_dict.get("hints", {})
        steps = pipeline_dict.get("steps", [])
        version = pipeline_dict.get("mnelab_version", "unknown")
        created = pipeline_dict.get("created", "")[:10]  # date portion only

        layout.addWidget(
            QLabel(f"<b>Pipeline</b> &mdash; created {created} (MNELAB {version})")
        )

        # compatibility hints
        unreplayable_operations = _unreplayable_operations(pipeline_dict)
        if unreplayable_operations:
            operations = ", ".join(sorted(set(unreplayable_operations)))
            warn_label = QLabel(
                "<b>This pipeline cannot be applied automatically.</b><br>"
                "The following operations depend on session-specific datasets: "
                f"{operations}."
            )
            warn_label.setWordWrap(True)
            warn_label.setStyleSheet("color: #b91c1c;")
            layout.addWidget(warn_label)

        if hints and current_dataset is not None:
            warnings = []
            if "dtype" in hints:
                cur_dtype = current_dataset.get("dtype")
                if cur_dtype and cur_dtype != hints["dtype"]:
                    warnings.append(
                        f"Expected data type <b>{hints['dtype']}</b>, "
                        f"current is <b>{cur_dtype}</b>."
                    )
            if "sfreq" in hints:
                cur_sfreq = current_dataset.get("data")
                if cur_sfreq is not None:
                    cur_sfreq = cur_sfreq.info["sfreq"]
                    if abs(cur_sfreq - hints["sfreq"]) > 0.01:
                        warnings.append(
                            f"Expected sampling rate "
                            f"<b>{hints['sfreq']:.6g}\u2009Hz</b>, "
                            f"current is <b>{cur_sfreq:.6g}\u2009Hz</b>."
                        )
            if "nchan" in hints:
                cur_data = current_dataset.get("data")
                if cur_data is not None:
                    cur_nchan = cur_data.info["nchan"]
                    if cur_nchan != hints["nchan"]:
                        warnings.append(
                            f"Expected <b>{hints['nchan']}</b> channels, "
                            f"current has <b>{cur_nchan}</b>."
                        )

            if warnings:
                warn_label = QLabel(
                    "<b>\u26a0 Compatibility warnings:</b><br>"
                    + "<br>".join(f"&bull; {w}" for w in warnings)
                )
                warn_label.setWordWrap(True)
                warn_label.setStyleSheet("color: #b45309;")  # amber
                layout.addWidget(warn_label)

        # step list
        layout.addWidget(QLabel(f"<b>Steps ({len(steps)})</b>"))
        step_list = QListWidget()
        step_list.setFrameStyle(QFrame.Shape.StyledPanel)
        for step in steps:
            label = _operation_label(step.get("operation"), step.get("params"))
            execution_mode = step.get("execution_mode", "automatic")
            if execution_mode != "automatic":
                label = f"{label} [{execution_mode}]"
            item = QListWidgetItem(label)
            if execution_mode == "skip":
                item.setForeground(QColor("gray"))
            step_list.addItem(item)
        layout.addWidget(step_list)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonbox.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
        if unreplayable_operations:
            buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        layout.addWidget(buttonbox)

        self.setLayout(layout)


def load_pipeline(path):
    """Load a .mnepipe JSON file.

    Parameters
    ----------
    path : str or Path
        Path to the .mnepipe file.

    Returns
    -------
    pipeline : dict
        The loaded pipeline dictionary.

    Raises
    ------
    ValueError
        If the file format is invalid.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return validate_pipeline(data)


class PipelineProgressDialog(QProgressDialog):
    """Simple progress dialog shown while a pipeline is being applied."""

    def __init__(self, parent, n_steps):
        super().__init__("Applying pipeline...", "Cancel", 0, n_steps, parent)
        self.setWindowTitle("Applying Pipeline")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumDuration(0)
        self.setValue(0)

    def update_progress(self, step_index, step):
        """Advance the dialog to the completed step."""
        label = _operation_label(step["operation"], step.get("params"))
        self.setLabelText(f"Applying step {step_index} of {self.maximum()}: {label}")
        self.setValue(step_index)
