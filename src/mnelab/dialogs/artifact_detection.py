# © MNELAB developers
#
# License: BSD (3-clause)

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.colors import to_rgba_array
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from mnelab.dialogs.utils import CheckBoxDelegate, NumberSortProxyModel
from mnelab.utils import (
    find_bad_epochs_amplitude,
    find_bad_epochs_autoreject,
    find_bad_epochs_kurtosis,
    find_bad_epochs_ptp,
)
from mnelab.utils.dependencies import have
from mnelab.widgets import FlatDoubleSpinBox


class ArtifactDetectionDialog(QDialog):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.setWindowTitle("Artifact Detection")
        self.detection_methods = {
            "Extreme values": {
                "parameters": [
                    ("threshold", None, 100.0, "µV", "±")
                ],  # (param_name, display_name, default, unit, prefix)
                "function": find_bad_epochs_amplitude,
            },
            "Peak-to-peak": {
                "parameters": [("threshold", None, 150.0, "µV", "")],
                "function": find_bad_epochs_ptp,
            },
            "Kurtosis": {
                "parameters": [("threshold", None, 5.0, "SD", "")],
                "function": find_bad_epochs_kurtosis,
            },
        }

        if have["autoreject"]:
            self.detection_methods["AutoReject"] = {
                "parameters": [],
                "function": find_bad_epochs_autoreject,
            }

        # structure: {epoch_idx: {"method_name": bool, "reject": bool}}
        self.detection_results = {}
        self.method_widgets = {}
        self.data = data
        self.detection_done = False
        self.pending_methods = set()

        # timer for debouncing detection runs
        self.detection_timer = QTimer()
        self.detection_timer.setSingleShot(True)
        self.detection_timer.timeout.connect(self.run_detection)

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setVerticalSpacing(15)
        layout.addLayout(grid)

        grid.addWidget(QLabel("<b>Method</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Parameters</b>"), 0, 1)

        # dynamically create UI elements for each detection method
        for idx, (method, details) in enumerate(
            self.detection_methods.items(), start=1
        ):
            checkbox = QCheckBox(method)

            # parameter container
            param_container = QWidget()
            param_form = QFormLayout(param_container)
            param_form.setContentsMargins(0, 0, 0, 0)
            param_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

            inputs = {}
            for param_name, display_name, default, unit, prefix in details[
                "parameters"
            ]:
                spin_box = FlatDoubleSpinBox()
                spin_box.setRange(-1e6, 1e6)
                spin_box.setValue(default)
                spin_box.setDecimals(1)
                spin_box.setPrefix(prefix)
                spin_box.setSuffix(f" {unit}")
                spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)

                # single parameter - no label
                if display_name is None:
                    param_form.addRow(spin_box)
                # multiple parameters - with parameter label
                else:
                    param_form.addRow(f"{display_name}:", spin_box)

                inputs[param_name] = {"spinbox": spin_box, "unit": unit}
                spin_box.valueChanged.connect(
                    lambda _, m=method: self.schedule_detection(m)
                )

            grid.addWidget(checkbox, idx, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(param_container, idx, 1)

            # disable parameter inputs by default
            param_container.setEnabled(False)
            checkbox.toggled.connect(param_container.setEnabled)
            checkbox.toggled.connect(lambda _, m=method: self.schedule_detection(m))

            self.method_widgets[method] = {"checkbox": checkbox, "inputs": inputs}

        layout.addSpacing(3)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        metrics = self.info_label.fontMetrics()
        max_text = "When pressing OK, 0000/0000 epochs will be dropped."
        required_width = metrics.horizontalAdvance(max_text)
        self.info_label.setFixedWidth(required_width)
        layout.addWidget(self.info_label)
        layout.addSpacing(3)

        button_layout = QHBoxLayout()

        self.preview_button = QPushButton("Preview...")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.show_preview_table)
        button_layout.addWidget(self.preview_button)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        button_layout.addWidget(self.button_box)
        layout.addLayout(button_layout)

        self.setFixedSize(self.sizeHint())
        self.setFocus()

    def get_selected_methods(self):
        """Return dict of selected methods and their parameters."""
        results = {}
        for method, widgets in self.method_widgets.items():
            if widgets["checkbox"].isChecked():
                params = {}
                for param_name, param_info in widgets["inputs"].items():
                    value = param_info["spinbox"].value()
                    # convert to V
                    if param_info["unit"] == "µV":
                        value *= 1e-6
                    params[param_name] = value
                results[method] = params
        return results

    def schedule_detection(self, changed_method=None):
        """Schedule detection run with a short delay."""
        selected = self.get_selected_methods()

        # reset if no methods are selected
        if not selected:
            self.detection_results = {}
            self.detection_done = False
            self.info_label.setText("")
            self.preview_button.setEnabled(False)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.detection_timer.stop()
            self.pending_methods.clear()
            return

        self.info_label.setText("Detecting artifacts...")

        if changed_method is not None:
            self.pending_methods.add(changed_method)

        # 500ms debounce
        self.detection_timer.stop()
        self.detection_timer.start(500)

    def update_info_label(self):
        """Update info label and OK button tooltip based on detection state."""
        if not self.detection_done:
            self.info_label.setText("")
            return

        n_total = len(self.detection_results)
        n_rejected = len(self.get_bad_epochs())

        # update label
        self.info_label.setText(
            f"<i>When pressing OK, {n_rejected}/{n_total} epochs will be dropped.</i>"
        )

        # update tooltip
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setToolTip(
            f"Apply rejection (will drop {n_rejected}/{n_total} epochs)."
        )

    def run_detection(self):
        """Performs detection and updates UI."""
        selected = self.get_selected_methods()
        n_epochs = len(self.data)

        # initialize if first run
        if not self.detection_results:
            self.detection_results = {i: {} for i in range(n_epochs)}

        pending_methods = self.pending_methods.copy()
        self.pending_methods.clear()

        # determine which methods to run
        methods_to_run = {m: selected[m] for m in pending_methods if m in selected}
        methods_to_remove = {m for m in pending_methods if m not in selected}

        # clean up results for deselected methods
        for idx in range(n_epochs):
            for method in methods_to_remove:
                self.detection_results[idx].pop(method, None)

        # detection for relevant methods
        for method, params in methods_to_run.items():
            detection_func = self.detection_methods[method]["function"]
            bad_epochs = detection_func(self.data, **params)

            for idx in range(n_epochs):
                self.detection_results[idx][method] = bool(bad_epochs[idx])

        # OR logic across all methods
        method_names = list(selected.keys())
        for idx in range(n_epochs):
            self.detection_results[idx]["reject"] = any(
                self.detection_results[idx].get(method, False)
                for method in method_names
            )

        # update UI state
        self.detection_done = True
        self.update_info_label()
        self.preview_button.setEnabled(True)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def show_preview_table(self):
        """Show preview table dialog."""
        dialog = ArtifactPreviewTable(self, self.data, self.detection_results)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.detection_results = dialog.detection_results
            self.update_info_label()

    def get_bad_epochs(self):
        """Return list of epoch indices to reject."""
        return [
            idx
            for idx, results in self.detection_results.items()
            if results.get("reject", False)
        ]

    def get_history_code(self):
        """Generate code snippet to reproduce the artifact detection."""
        selected_methods = self.get_selected_methods()
        code_lines = ["\n# artifact detection"]
        bad_epochs_vars = []

        # code for selected methods
        for method, params in selected_methods.items():
            var_name = f"bad_epochs_{method.lower()}"
            func_name = self.detection_methods[method]["function"].__name__
            if params:
                param_str = ", ".join(
                    f"{name}={value}" for name, value in params.items()
                )
                code_lines.append(f"{var_name} = {func_name}(data, {param_str})")
            else:
                code_lines.append(f"{var_name} = {func_name}(data)")
            bad_epochs_vars.append(var_name)

        if len(bad_epochs_vars) == 1:
            code_lines.append(f"bad_epochs_mask = {bad_epochs_vars[0]}")
        else:
            code_lines.append(f"bad_epochs_mask = {' | '.join(bad_epochs_vars)}")

        code_lines.append("bad_epochs_auto = np.where(bad_epochs_mask)[0].tolist()")

        # manual detection
        auto_rejected = set()
        for idx, results in self.detection_results.items():
            if any(results.get(method, False) for method in selected_methods.keys()):
                auto_rejected.add(idx)

        final_rejects = set(self.get_bad_epochs())

        manual_added = list(final_rejects - auto_rejected)
        manual_removed = list(auto_rejected - final_rejects)

        if manual_added or manual_removed:
            code_lines.append("\n# manual modifications")
            code_lines.append("bad_epochs_final = bad_epochs_auto.copy()")

            if manual_added:
                code_lines.append(f"bad_epochs_final.extend({manual_added})")
            if manual_removed:
                code_lines.append(
                    "bad_epochs_final = "
                    f"[idx for idx in bad_epochs_final if idx not in {manual_removed}]"
                )

            code_lines.append(
                "data.drop(bad_epochs_final, reason='ARTIFACT_DETECTION')"
            )
        else:
            # no manual changes
            code_lines.append("data.drop(bad_epochs_auto, reason='ARTIFACT_DETECTION')")

        return "\n".join(code_lines)


class ArtifactPreviewTable(QDialog):
    def __init__(self, parent, data, detection_results):
        super().__init__(parent)
        self.setWindowTitle("Artifact Detection Preview")
        n_methods = len(detection_results[0].keys()) - 1
        width = min(800, 200 + n_methods * 120)
        self.setFixedSize(width, 400)

        self.data = data
        self.detection_results = {
            idx: results.copy() for idx, results in detection_results.items()
        }
        layout = QVBoxLayout(self)

        self.table_view = QTableView()
        self.model = QStandardItemModel()
        self.proxy_model = NumberSortProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)

        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.verticalHeader().setVisible(False)

        self.checkbox_delegate = CheckBoxDelegate()

        self.populate_table()
        layout.addWidget(self.table_view)

        self.info_label = QLabel()
        self.update_info_label()
        layout.addWidget(self.info_label)

        button_layout = QHBoxLayout()
        self.view_epochs_button = QPushButton("View Epochs...")
        self.view_epochs_button.clicked.connect(self.show_epoch_visualization)
        button_layout.addWidget(self.view_epochs_button)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

        self.model.dataChanged.connect(self.update_info_label)

    def populate_table(self):
        """Populate table with detection results."""
        n_epochs = len(self.detection_results)

        method_cols = [
            key for key in self.detection_results[0].keys() if key != "reject"
        ]
        header_labels = ["Epoch"] + method_cols + ["Reject"]
        self.model.setHorizontalHeaderLabels(header_labels)

        self.reject_col_idx = len(header_labels) - 1

        for epoch_idx in range(n_epochs):
            results = self.detection_results[epoch_idx]
            row_items = []

            item = QStandardItem()
            item.setData(epoch_idx, Qt.ItemDataRole.DisplayRole)
            item.setData(epoch_idx, Qt.ItemDataRole.UserRole)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            row_items.append(item)

            # method columns
            for col_name in method_cols:
                bad_epochs = results.get(col_name, False)
                label = "✔" if bad_epochs else ""
                item = QStandardItem(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bad_epochs:
                    color = QColor(255, 0, 0, 20)
                    item.setBackground(QBrush(color))
                    item.setForeground(QColor(220, 45, 45))

                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setData(int(bad_epochs), Qt.ItemDataRole.UserRole)
                row_items.append(item)

            reject_item = QStandardItem()
            reject_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            check_state = (
                Qt.CheckState.Checked
                if results.get("reject", False)
                else Qt.CheckState.Unchecked
            )
            reject_item.setData(check_state, Qt.ItemDataRole.CheckStateRole)
            row_items.append(reject_item)

            self.model.appendRow(row_items)

        self.table_view.setItemDelegateForColumn(
            self.reject_col_idx, self.checkbox_delegate
        )

        # set column widths
        self.table_view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        for col in range(1, len(header_labels)):
            self.table_view.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.Stretch
            )
        # initial sort by epoch index
        self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def update_info_label(self):
        """Update label showing rejection statistics."""
        n_total = self.model.rowCount()
        n_rejected = 0
        for row in range(n_total):
            if (
                self.model.item(row, self.reject_col_idx).checkState()
                == Qt.CheckState.Checked
            ):
                n_rejected += 1

        self.info_label.setText(
            f"<i>{n_rejected}/{n_total} epochs marked for rejection.</i>"
        )

    def show_epoch_visualization(self):
        """Show epoch visualization from the preview table."""

        self.sync_results_from_table()

        flagged_idx = [
            idx
            for idx, results in self.detection_results.items()
            if results.get("reject", False)
        ]

        fig = self.data.plot(scalings="auto", block=False, show=False)

        # initialize bad_epochs attribute
        fig.mne.bad_epochs = flagged_idx.copy()

        if isinstance(fig, QWidget):  # Qt backend
            fig.mne.epoch_color_ref[:, flagged_idx] = to_rgba_array(
                fig.mne.epoch_color_bad
            )

            # update traces
            for trace in fig.mne.traces:
                trace.update_color()

            fig._redraw(update_data=True)
            # update bad epochs in hscroll bar
            fig.mne.overview_bar.update_bad_epochs()

        else:  # Matplotlib backend
            fig._redraw()
            if hasattr(fig.mne.ax_hscroll, "patches"):
                for idx in flagged_idx:
                    fig.mne.ax_hscroll.patches[idx].set_color(fig.mne.epoch_color_bad)

        viz = EpochVisualization(self, fig)
        self.setModal(True)
        viz.finished.connect(lambda: self._update_from_visualization(viz))
        viz.exec()

    def _update_from_visualization(self, viz):
        """Called when visualization window closes to update detection results."""

        # reset all rejections
        for idx in self.detection_results:
            self.detection_results[idx]["reject"] = False

        # set rejections based on visualization
        for idx in viz.flagged_epochs:
            if idx in self.detection_results:
                self.detection_results[idx]["reject"] = True

        self.refresh_table()

    def refresh_table(self):
        """Refresh table to reflect updated metadata."""
        for row_idx in range(len(self.detection_results)):
            # update the reject checkbox
            reject_item = self.model.item(row_idx, self.reject_col_idx)
            check_state = (
                Qt.CheckState.Checked
                if self.detection_results[row_idx].get("reject", False)
                else Qt.CheckState.Unchecked
            )
            reject_item.setData(check_state, Qt.ItemDataRole.CheckStateRole)

        self.update_info_label()

    def sync_results_from_table(self):
        """Sync detection results with current table state."""
        for proxy_row in range(self.proxy_model.rowCount()):
            proxy_index = self.proxy_model.index(proxy_row, 0)
            source_index = self.proxy_model.mapToSource(proxy_index)
            real_row_idx = source_index.row()

            reject_item = self.model.item(real_row_idx, self.reject_col_idx)
            is_checked = (
                reject_item.data(Qt.ItemDataRole.CheckStateRole)
                == Qt.CheckState.Checked
            )

            self.detection_results[real_row_idx]["reject"] = is_checked

    def accept(self):
        """Update detection results based on user changes."""
        self.sync_results_from_table()
        super().accept()


class EpochVisualization(QDialog):
    def __init__(self, parent, fig):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(1600, 800)
        self.fig = fig
        self.flagged_epochs = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if isinstance(fig, QWidget):
            # Qt backend
            fig.setParent(self)
            self.canvas = fig
            fig.installEventFilter(self)
            for child in fig.findChildren(QWidget):
                child.installEventFilter(self)
        else:
            # Matplotlib backend
            self.canvas = FigureCanvas(self.fig)
            self.canvas.installEventFilter(self)
            self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.canvas.setFocus()

        layout.addWidget(self.canvas)

    def closeEvent(self, event):
        if hasattr(self.fig, "mne") and hasattr(self.fig.mne, "bad_epochs"):
            self.flagged_epochs = list(self.fig.mne.bad_epochs)

        super().closeEvent(event)

    def eventFilter(self, obj, event):
        """Block Escape key to prevent MNE from dropping epochs on close."""
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            return True
        return super().eventFilter(obj, event)
