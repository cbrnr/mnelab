# © MNELAB developers
#
# License: BSD (3-clause)

import json

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QListWidget,
    QVBoxLayout,
)

from mnelab.widgets.pipeline_tree import _operation_label


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
        for i, step in enumerate(steps, start=1):
            label = _operation_label(step["operation"], step.get("params"))
            step_list.addItem(f"{i}. {label}")
        layout.addWidget(step_list)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonbox.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
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
    if data.get("pipeline_format") != 1:
        raise ValueError(
            f"Unsupported pipeline format version: {data.get('pipeline_format')!r}"
        )
    return data
