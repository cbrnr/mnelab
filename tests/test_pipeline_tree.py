# © MNELAB developers
#
# License: BSD (3-clause)

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from mnelab.widgets.pipeline_tree import PipelineTreeWidget


def _tree():
    return [
        {
            "index": 0,
            "name": "sample",
            "dtype": "raw",
            "operation": None,
            "operation_params": None,
            "children": [
                {
                    "index": 1,
                    "name": "sample filtered",
                    "dtype": "raw",
                    "operation": "filter",
                    "operation_params": {"lower": None, "upper": 40, "notch": None},
                    "children": [
                        {
                            "index": 2,
                            "name": "sample cropped",
                            "dtype": "raw",
                            "operation": "crop",
                            "operation_params": {"start": 0, "stop": 5},
                            "children": [],
                        },
                        {
                            "index": 3,
                            "name": "sample epochs",
                            "dtype": "epochs",
                            "operation": "epoch_data",
                            "operation_params": {
                                "event_id": [1],
                                "tmin": -0.2,
                                "tmax": 0.5,
                                "baseline": None,
                            },
                            "children": [],
                        },
                    ],
                },
                {
                    "index": 4,
                    "name": "sample picked",
                    "dtype": "raw",
                    "operation": "pick_channels",
                    "operation_params": {"picks": ["EEG"]},
                    "children": [],
                },
            ],
        },
        {
            "index": 5,
            "name": "epochs file",
            "dtype": "epochs",
            "operation": None,
            "operation_params": None,
            "children": [],
        },
    ]


def _widget(qtbot):
    parent = QWidget()
    parent.model = SimpleNamespace(remove_data=lambda index: None)
    widget = PipelineTreeWidget(parent)
    qtbot.addWidget(parent)
    qtbot.addWidget(widget)
    return widget


def test_pipeline_tree_populate_uses_nested_branches(qtbot):
    """Pipeline steps are nested under their actual parent item."""
    widget = _widget(qtbot)
    widget.populate(_tree(), active_index=3)

    root = widget.topLevelItem(0)
    filtered = root.child(0)
    picked = root.child(1)
    cropped = filtered.child(0)
    epochs = filtered.child(1)

    assert widget.topLevelItemCount() == 2
    assert root.childCount() == 2
    assert filtered.childCount() == 2
    assert picked.childCount() == 0
    assert cropped.data(0, Qt.ItemDataRole.UserRole) == 2
    assert epochs.data(0, Qt.ItemDataRole.UserRole) == 3
    assert widget.currentItem() is epochs


def test_pipeline_tree_badges_show_only_type_changes(qtbot):
    """Repeated dtype badges are suppressed until the displayed dtype changes."""
    widget = _widget(qtbot)
    widget.populate(_tree(), active_index=0)

    root = widget.topLevelItem(0)
    filtered = root.child(0)
    cropped = filtered.child(0)
    epochs = filtered.child(1)
    picked = root.child(1)
    second_root = widget.topLevelItem(1)

    assert root.text(1) == "raw"
    assert filtered.text(1) == ""
    assert cropped.text(1) == ""
    assert epochs.text(1) == "epochs"
    assert picked.text(1) == "raw"
    assert second_root.text(1) == "epochs"


def test_pipeline_tree_selection_signal_and_edit_flags(qtbot):
    """Only root rows are editable and selections emit model indices."""
    widget = _widget(qtbot)
    widget.populate(_tree(), active_index=0)

    root = widget.topLevelItem(0)
    filtered = root.child(0)
    epochs = filtered.child(1)

    assert root.flags() & Qt.ItemFlag.ItemIsEditable
    assert not (filtered.flags() & Qt.ItemFlag.ItemIsEditable)

    with qtbot.waitSignal(widget.datasetSelected, timeout=1000) as blocker:
        widget.setCurrentItem(epochs)
    assert blocker.args == [3]
