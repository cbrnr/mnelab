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
    QMenu,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
)

from mnelab.widgets.sidebar import ROW_HEIGHT, TypeBadgeDelegate

_OP_LABELS = {
    "filter": "Filter",
    "crop": "Crop",
    "import_annotations": "Import annotations",
    "import_bads": "Import bad channels",
    "import_events": "Import events",
    "import_ica": "Import ICA",
    "pick_channels": "Pick channels",
    "rename_channels": "Rename channels",
    "run_ica": "Run ICA",
    "set_annotations": "Edit annotations",
    "set_channel_properties": "Channel properties",
    "set_events": "Edit events",
    "set_ica_exclude": "Set ICA excludes",
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
    elif operation == "run_ica":
        method = p.get("method")
        n_components = p.get("n_components")
        if method == "fastica":
            method = "FastICA"
        elif isinstance(method, str):
            method = method.title()
        if method and n_components is not None:
            return f"Run ICA: {method} ({n_components})"
        if method:
            return f"Run ICA: {method}"
        return "Run ICA"
    elif operation == "set_ica_exclude":
        exclude = p.get("exclude") or []
        if not exclude:
            return "Set ICA excludes: none"
        return f"Set ICA excludes: {', '.join(str(component) for component in exclude)}"
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
    Descendant operation steps are shown as nested children so branches can split off
    at any point in a dataset tree.
    """

    datasetSelected = Signal(int)  # emits the model.data index of the selected item
    datasetRenamed = Signal(int, str)  # emits (index, new_name) when renamed
    showHistoryRequested = Signal(int)
    savePipelineRequested = Signal(int)
    applyPipelineRequested = Signal(int)
    exportHistoryRequested = Signal(int)
    showDetailsRequested = Signal(int)

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

        self._drag_pre_item = None  # selection before a drag started
        self._drag_drop_item = None  # item currently under drag cursor
        self.setAcceptDrops(True)

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
            """Show dtype only for the first item and dtype transitions."""
            nonlocal previous_dtype
            dtype_key = dtype.lower() if dtype else None
            if dtype and (previous_dtype is None or dtype_key != previous_dtype):
                item.setText(1, dtype)
                item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
                item.setToolTip(1, f"Data type: {dtype.capitalize()}")
            if dtype_key is not None:
                previous_dtype = dtype_key

        def _add_children(parent_item, node):
            """DFS: add descendants as nested children of parent_item."""
            nonlocal active_item
            for child in node.get("children", []):
                idx = child["index"]
                operation = child.get("operation") or ""
                params = child.get("operation_params")
                dtype = child.get("dtype") or ""
                label = _operation_label(operation, params)

                item = QTreeWidgetItem(parent_item)
                item.setText(0, label)
                item.setToolTip(0, child["name"])
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                # step items are selectable but not user-editable
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setSizeHint(0, QSize(0, ROW_HEIGHT))
                _set_dtype_badge(item, dtype)

                if idx == active_index:
                    active_item = item

                _add_children(item, child)
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

            _add_children(root_item, root_node)
            root_item.setExpanded(True)

        self.blockSignals(False)

        if active_item is not None:
            self.setCurrentItem(active_item)

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
                btn.setStyleSheet(self._close_button_stylesheet(False))
                btn.installEventFilter(self)
                idx = self._dataset_index_for_item(item)
                btn.clicked.connect(lambda _, i=idx: self._parent.model.remove_data(i))
                self.setItemWidget(item, 2, btn)
            else:
                self.removeItemWidget(item, 2)
            for i in range(item.childCount()):
                _walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            _walk(self.topLevelItem(i))

    def _close_button_stylesheet(self, hovered):
        if hovered:
            return """
                QToolButton {
                    background: rgba(128, 128, 128, 0.2);
                    border-radius: 4px;
                }
                QToolButton:pressed {
                    background: rgba(128, 128, 128, 0.4);
                    border-radius: 4px;
                }
            """
        return """
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 0.4);
                border-radius: 4px;
            }
        """

    def _item_for_close_button(self, button):
        """Return the tree item that owns a close button."""

        def _walk(item):
            if self.itemWidget(item, 2) is button:
                return item
            for i in range(item.childCount()):
                child = _walk(item.child(i))
                if child is not None:
                    return child
            return None

        for i in range(self.topLevelItemCount()):
            item = _walk(self.topLevelItem(i))
            if item is not None:
                return item
        return None

    def _close_button_rect(self, item):
        index = self.indexFromItem(item, 2)
        if not index.isValid():
            return None
        return self.visualRect(index)

    def set_badges_visible(self, visible):
        """Show or hide the dtype badge column."""
        self.setColumnHidden(1, not visible)

    def _branch_has_replayable_steps(self, dataset_index):
        """Return whether a branch has replayable pipeline steps."""
        model = getattr(self._parent, "model", None)
        if model is None or dataset_index < 0 or dataset_index >= len(model.data):
            return False
        return model.has_replayable_pipeline(dataset_index)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            u.toLocalFile().endswith(".mnepipe") for u in event.mimeData().urls()
        ):
            self._drag_pre_item = self.currentItem()
            event.acceptProposedAction()
        else:
            event.ignore()  # let non-pipeline files propagate to MainWindow

    def dragMoveEvent(self, event):
        if not (
            event.mimeData().hasUrls()
            and any(
                u.toLocalFile().endswith(".mnepipe") for u in event.mimeData().urls()
            )
        ):
            event.ignore()
            return
        item = self.itemAt(event.pos())
        if item is not None and item is not self._drag_drop_item:
            self._drag_drop_item = item
            self.blockSignals(True)
            self.setCurrentItem(item)
            self.blockSignals(False)
        elif item is None:
            self._drag_drop_item = None
            self.blockSignals(True)
            self.clearSelection()
            self.blockSignals(False)
        event.acceptProposedAction() if item is not None else event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_drop_item = None
        self.blockSignals(True)
        if self._drag_pre_item is not None:
            self.setCurrentItem(self._drag_pre_item)
        else:
            self.clearSelection()
        self.blockSignals(False)
        self._drag_pre_item = None
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        pipeline_paths = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().endswith(".mnepipe")
        ]
        if not pipeline_paths:
            event.ignore()
            return
        item = self.itemAt(event.pos())
        idx = self._dataset_index_for_item(item)
        # restore selection before applying (avoid side-effects)
        self._drag_drop_item = None
        self.blockSignals(True)
        if self._drag_pre_item is not None:
            self.setCurrentItem(self._drag_pre_item)
        self.blockSignals(False)
        self._drag_pre_item = None
        if idx >= 0:
            for path in pipeline_paths:
                self._parent._apply_pipeline_from_path(path, idx)
        event.acceptProposedAction()

    def _is_root_dataset(self, dataset_index):
        """Return whether the given dataset index points to a root dataset."""
        model = getattr(self._parent, "model", None)
        if model is None or dataset_index < 0 or dataset_index >= len(model.data):
            return False
        return model.data[dataset_index].get("parent_index") is None

    def _create_context_menu(self, dataset_index):
        """Build the branch context menu for the given dataset index."""
        menu = QMenu(self)
        is_root = self._is_root_dataset(dataset_index)
        if is_root:
            show_history_label = "Show dataset history..."
            export_history_label = "Export dataset history..."
        else:
            show_history_label = "Show branch history..."
            export_history_label = "Export branch history..."

        show_details_action = menu.addAction("Dataset details...")
        menu.addSeparator()
        show_history_action = menu.addAction(show_history_label)
        export_history_action = menu.addAction(export_history_label)
        menu.addSeparator()
        apply_pipeline_action = menu.addAction("Apply pipeline...")

        has_steps = self._branch_has_replayable_steps(dataset_index)

        actions = {
            "show_details": show_details_action,
            "show_history": show_history_action,
            "export_history": export_history_action,
            "apply_pipeline": apply_pipeline_action,
        }

        if has_steps:
            menu.addSeparator()
            actions["save_pipeline"] = menu.addAction("Save pipeline...")

        return menu, actions

    def contextMenuEvent(self, event):
        """Show branch actions for the item under the cursor."""
        item = self.itemAt(event.pos())
        idx = self._dataset_index_for_item(item)
        if idx < 0:
            event.ignore()
            return

        menu, actions = self._create_context_menu(idx)

        selected_action = menu.exec(event.globalPos())
        if selected_action == actions["show_details"]:
            self.showDetailsRequested.emit(idx)
            event.accept()
            return
        if selected_action == actions["show_history"]:
            self.showHistoryRequested.emit(idx)
            event.accept()
            return
        if selected_action == actions["apply_pipeline"]:
            self.applyPipelineRequested.emit(idx)
            event.accept()
            return
        if "save_pipeline" in actions and selected_action == actions["save_pipeline"]:
            self.savePipelineRequested.emit(idx)
            event.accept()
            return
        if selected_action == actions["export_history"]:
            self.exportHistoryRequested.emit(idx)
            event.accept()
            return

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
        elif isinstance(source, QToolButton):
            if event.type() == QEvent.Type.Enter:
                item = self._item_for_close_button(source)
                rect = self._close_button_rect(item) if item is not None else None
                cursor = self.viewport().mapFromGlobal(QCursor.pos())
                source.setStyleSheet(
                    self._close_button_stylesheet(
                        rect is not None and rect.contains(cursor)
                    )
                )
            elif event.type() == QEvent.Type.Leave:
                source.setStyleSheet(self._close_button_stylesheet(False))
        return False
