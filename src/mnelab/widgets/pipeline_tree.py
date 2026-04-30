# © MNELAB developers
#
# License: BSD (3-clause)

import sys

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHeaderView,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
)

from mnelab.widgets.sidebar import ROW_HEIGHT, TypeBadgeDelegate

_OP_LABELS = {
    "filter": "Filter",
    "crop": "Crop",
    "pick_channels": "Pick channels",
    "rename_channels": "Rename channels",
    "set_channel_properties": "Channel properties",
    "set_montage": "Set montage",
    "change_reference": "Change reference",
    "interpolate_bads": "Interpolate bads",
    "epoch_data": "Create epochs",
    "drop_bad_epochs": "Drop bad epochs",
    "drop_detected_artifacts": "Detect artifacts",
    "apply_ica": "Apply ICA",
    "convert_od": "Convert to OD",
    "convert_beer_lambert": "Beer-Lambert law",
    "find_events": "Find events",
    "events_from_annotations": "Events from annotations",
    "annotations_from_events": "Annotations from events",
    "append_data": "Append data",
    "duplicate": "Duplicate",
}


def _operation_label(operation, params):
    """Return a short human-readable label for a pipeline operation."""
    p = params or {}
    if operation == "filter":
        lower, upper, notch = p.get("lower"), p.get("upper"), p.get("notch")
        if lower and upper:
            return f"Filter: {lower}\u2013{upper}\u2009Hz"
        elif lower:
            return f"Filter: >{lower}\u2009Hz"
        elif upper:
            return f"Filter: <{upper}\u2009Hz"
        elif notch:
            return f"Notch: {notch}\u2009Hz"
        return "Filter"
    elif operation == "crop":
        return f"Crop: {p.get('start', '?')}\u2013{p.get('stop', '?')}\u2009s"
    elif operation == "epoch_data":
        tmin = p.get("tmin", "?")
        tmax = p.get("tmax", "?")
        return f"Epoch: {tmin}\u2013{tmax}\u2009s"
    elif operation == "change_reference":
        ref = p.get("ref", "?")
        if ref == "average":
            return "Reference: average"
        return f"Reference: {ref}"
    elif operation == "set_montage":
        montage = p.get("montage")
        name = None
        if montage is not None:
            name = getattr(montage, "name", None) or (
                montage.get("name") if isinstance(montage, dict) else None
            )
        return f"Montage: {name}" if name else "Set montage"
    return _OP_LABELS.get(operation, operation or "Unknown step")


class _TreeBadgeDelegate(TypeBadgeDelegate):
    """TypeBadgeDelegate variant that fills the cell background before drawing."""

    def paint(self, painter, option, index):
        # fill the background matching selection/base state so the cell is never white
        if option.state & QStyle.StateFlag.State_Selected:
            bg = option.palette.color(option.palette.ColorRole.Highlight)
        else:
            bg = option.palette.color(option.palette.ColorRole.Base)
        painter.fillRect(option.rect, bg)
        super().paint(painter, option, index)


class PipelineTreeWidget(QTreeWidget):
    """Sidebar tree widget that shows datasets organised by pipeline lineage.

    Each root dataset (no parent in the model) appears as a bold top-level item.
    Descendant operation steps are nested under their actual parent operation so that
    branches in the model are visible in the sidebar.
    """

    datasetSelected = Signal(int)  # emits the model.data index of the selected item
    datasetRenamed = Signal(int, str)  # emits (index, new_name) when renamed

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent

        self.setColumnCount(3)
        self.setHeaderHidden(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setObjectName("pipeline_tree")
        self.setIndentation(16)
        self.setAnimated(False)
        self.setTabKeyNavigation(False)
        self.setUniformRowHeights(True)

        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 56)
        self.setColumnWidth(2, ROW_HEIGHT)  # exactly one square button

        self.setItemDelegateForColumn(1, _TreeBadgeDelegate(self))

        if sys.platform != "darwin":
            self._apply_base_stylesheet()

        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.currentItemChanged.connect(self._on_current_item_changed)
        self.itemChanged.connect(self._on_item_changed)

        self.setAccessibleName("Pipeline tree")

    def _apply_base_stylesheet(self):
        app = QApplication.instance()
        palette = app.palette() if isinstance(app, QApplication) else self.palette()
        base = palette.color(palette.ColorRole.Base).name()
        text = palette.color(palette.ColorRole.Text).name()
        hl = palette.color(palette.ColorRole.Highlight).name()
        hl_text = palette.color(palette.ColorRole.HighlightedText).name()
        self.setStyleSheet(f"""
            QTreeWidget#pipeline_tree {{ outline: 0; background-color: {base}; }}
            QTreeWidget#pipeline_tree::item {{
                background: {base};
                color: {text};
                height: {ROW_HEIGHT}px;
            }}
            QTreeWidget#pipeline_tree::item:hover {{
                background: transparent;
                color: {text};
            }}
            QTreeWidget#pipeline_tree::item:selected {{
                background: {hl};
                color: {hl_text};
            }}
            QTreeWidget#pipeline_tree::item:focus {{
                background: {hl};
                color: {hl_text};
            }}
        """)

    def refresh_theme(self):
        if sys.platform != "darwin":
            self._apply_base_stylesheet()
            self.viewport().update()

    def populate(self, tree, active_index):
        """Rebuild the tree from the pipeline tree structure.

        Parameters
        ----------
        tree : list of dict
            Output of `Model.get_pipeline_tree()`.
        active_index : int
            The currently active dataset index in `model.data`.
        """
        self.blockSignals(True)
        self.clear()

        active_item = None
        previous_dtype = None

        def _set_dtype_badge(item, dtype):
            """Show dtype only for the first item and later dtype changes."""
            nonlocal previous_dtype
            dtype = dtype or ""
            if dtype and (previous_dtype is None or dtype != previous_dtype):
                item.setText(1, dtype)
                item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            if dtype:
                previous_dtype = dtype

        def _add_step(parent_item, node):
            """Add a pipeline node below its actual parent item."""
            nonlocal active_item
            idx = node["index"]
            operation = node.get("operation") or ""
            params = node.get("operation_params")

            item = QTreeWidgetItem(parent_item)
            item.setText(0, _operation_label(operation, params))
            item.setToolTip(0, node["name"])
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            # step items are selectable but not user-editable
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setSizeHint(0, QSize(0, ROW_HEIGHT))
            _set_dtype_badge(item, node.get("dtype"))

            if idx == active_index:
                active_item = item

            for child in node.get("children", []):
                _add_step(item, child)
            item.setExpanded(True)

        for root_node in tree:
            idx = root_node["index"]
            name = root_node["name"]
            dtype = root_node.get("dtype") or ""

            root_item = QTreeWidgetItem(self)
            font = QFont()
            font.setBold(True)
            root_item.setFont(0, font)
            root_item.setText(0, name)
            root_item.setToolTip(0, name)
            root_item.setData(0, Qt.ItemDataRole.UserRole, idx)
            root_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            root_item.setSizeHint(0, QSize(0, ROW_HEIGHT))
            _set_dtype_badge(root_item, dtype)

            if idx == active_index:
                active_item = root_item

            for child in root_node.get("children", []):
                _add_step(root_item, child)
            root_item.setExpanded(True)

        self.blockSignals(False)

        if active_item is not None:
            self.setCurrentItem(active_item)
            parent = active_item.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()

        self._refresh_close_buttons()
        self.setFocus()

    def _dataset_index_for_item(self, item):
        if item is None:
            return -1
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _on_current_item_changed(self, current, _previous):
        idx = self._dataset_index_for_item(current)
        if idx >= 0:
            self.datasetSelected.emit(idx)
        self._refresh_close_buttons()

    def _on_item_changed(self, item, column):
        # only root items (no Qt parent) are editable; emit rename signal for them
        if column == 0 and item.parent() is None:
            idx = self._dataset_index_for_item(item)
            if idx >= 0:
                self.datasetRenamed.emit(idx, item.text(0))

    def _refresh_close_buttons(self):
        """Update close-button visibility for the item under the cursor."""
        cursor_pos = self.viewport().mapFromGlobal(QCursor.pos())
        hovered = self.itemAt(cursor_pos)
        self._show_close_button(hovered)

    def _show_close_button(self, target_item):
        """Place a close button on target_item's row, remove from all others."""

        def _walk(item):
            if item is target_item:
                btn = QToolButton()
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.setFixedSize(ROW_HEIGHT, ROW_HEIGHT)
                btn.setIcon(QIcon.fromTheme("close-data"))
                btn.setToolTip("Close dataset")
                btn.setStyleSheet(
                    "QToolButton { background: transparent; border: none; }"
                    "QToolButton:hover {"
                    "  background: rgba(128,128,128,0.2); border-radius: 4px; }"
                    "QToolButton:pressed {"
                    "  background: rgba(128,128,128,0.4); border-radius: 4px; }"
                )
                idx = self._dataset_index_for_item(item)
                btn.clicked.connect(lambda _, i=idx: self._parent.model.remove_data(i))
                self.setItemWidget(item, 2, btn)
            else:
                self.removeItemWidget(item, 2)
            for i in range(item.childCount()):
                _walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            _walk(self.topLevelItem(i))

    def set_badges_visible(self, visible):
        """Show or hide the dtype badge column."""
        self.setColumnHidden(1, not visible)

    def contextMenuEvent(self, event):
        """Suppress the default right-click context menu."""
        event.ignore()

    def eventFilter(self, source, event):
        if source == self.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    return True  # consume: no selection change, no context menu
            elif event.type() == QEvent.Type.MouseMove:
                item = self.itemAt(event.pos())
                self._show_close_button(item)
            elif event.type() == QEvent.Type.Leave:
                self._show_close_button(None)
        return False
