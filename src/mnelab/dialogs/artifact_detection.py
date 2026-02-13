# © MNELAB developers
#
# License: BSD (3-clause)

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.colors import to_rgba_array
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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

from mnelab.dialogs.utils import (
    CheckBoxDelegate,
    NumberSortProxyModel,
)
from mnelab.utils.artifact_detection import (
    detect_extreme_values,
    detect_kurtosis,
    detect_peak_to_peak,
    detect_with_autoreject,
)
from mnelab.utils.dependencies import have


class ArtifactDetectionDialog(QDialog):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.setWindowTitle("Configure Artifact Detection")
        self.setFixedSize(375, 230)
        self.detection_methods = {
            "Extreme values": {
                "parameters": [
                    ("threshold", None, 100.0, "µV")
                ],  # (param_name, display_name, default, unit)
                "function": detect_extreme_values,
            },
            "Peak-to-peak": {
                "parameters": [("ptp_threshold", None, 150.0, "µV")],
                "function": detect_peak_to_peak,
            },
            "Kurtosis": {
                "parameters": [("kurtosis", None, 5.0, "SD")],
                "function": detect_kurtosis,
            },
        }

        if have.get("autoreject", False):
            self.detection_methods["AutoReject"] = {
                "parameters": [],
                "function": detect_with_autoreject,
            }

        # structure: {epoch_idx: {"method_name": bool, "reject": bool}}
        self.detection_results = {}
        self.method_widgets = {}
        self.data = data
        self.detection_done = False

        # timer for debouncing detection runs
        self.detection_timer = QTimer()
        self.detection_timer.setSingleShot(True)
        self.detection_timer.timeout.connect(self.run_detection)

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setVerticalSpacing(15)
        layout.addLayout(grid)

        grid.addWidget(QLabel("Method"), 0, 0)
        grid.addWidget(QLabel("Parameters"), 0, 1)

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
            for param_name, display_name, default, unit in details["parameters"]:
                spin_box = QDoubleSpinBox()
                spin_box.setRange(-1e6, 1e6)
                spin_box.setValue(default)
                spin_box.setDecimals(2)
                spin_box.setSuffix(f" {unit}")

                # single parameter - no label
                if display_name is None:
                    param_form.addRow(spin_box)
                # multiple parameters - with parameter label
                else:
                    param_form.addRow(f"{display_name}:", spin_box)

                inputs[param_name] = spin_box
                spin_box.valueChanged.connect(self.schedule_detection)

            grid.addWidget(checkbox, idx, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(param_container, idx, 1)

            # disable parameter inputs by default
            param_container.setEnabled(False)
            checkbox.toggled.connect(param_container.setEnabled)
            checkbox.toggled.connect(self.schedule_detection)

            self.method_widgets[method] = {"checkbox": checkbox, "inputs": inputs}

        self.info_label = QLabel("Please select at least one detection method")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        button_layout = QHBoxLayout()

        self.preview_button = QPushButton("Preview...")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.show_preview_table)
        button_layout.addWidget(self.preview_button)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        button_layout.addWidget(self.button_box)
        layout.addLayout(button_layout)

    def get_selected_methods(self):
        """Return dict of selected methods and their parameters."""
        results = {}
        for method, widgets in self.method_widgets.items():
            if widgets["checkbox"].isChecked():
                results[method] = {
                    name: spin.value() for name, spin in widgets["inputs"].items()
                }
        return results

    def schedule_detection(self):
        """Schedule detection run with a short delay."""
        selected = self.get_selected_methods()

        # reset if no methods are selected
        if not selected:
            self.detection_results = {}
            self.detection_done = False
            self.info_label.setText("Please select at least one detection method")
            self.preview_button.setEnabled(False)
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
            self.detection_timer.stop()
            return

        self.info_label.setText("Detecting artifacts...")

        # 500ms debounce
        self.detection_timer.stop()
        self.detection_timer.start(500)

    def update_info_label(self):
        """Update info label and OK button tooltip based on detection state."""
        if not self.detection_done:
            self.info_label.setText("Please select method and press Detect")
            return

        n_total = len(self.detection_results)
        n_rejected = sum(
            1
            for results in self.detection_results.values()
            if results.get("reject", False)
        )

        # update label
        self.info_label.setText(
            f"When pressing OK, {n_rejected} out of {n_total} epochs will be dropped"
        )

        # update tooltip
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setToolTip(
            f"Apply rejection (will drop {n_rejected} out of {n_total} epochs)"
        )

    def run_detection(self):
        """Performs detection and updates UI."""
        selected = self.get_selected_methods()
        n_epochs = len(self.data)

        self.detection_results = {i: {} for i in range(n_epochs)}

        # run each selected detection method
        for method, params in selected.items():
            detection_func = self.detection_methods[method]["function"]
            bad_epochs = detection_func(self.data, **params)

            # store results
            for idx in range(n_epochs):
                self.detection_results[idx][method] = bool(bad_epochs[idx])

        # OR logic across all methods
        method_names = list(selected.keys())
        for idx in range(n_epochs):
            if method_names:
                self.detection_results[idx]["reject"] = any(
                    self.detection_results[idx].get(method, False)
                    for method in method_names
                )
            else:
                self.detection_results[idx]["reject"] = False

        # update UI state
        self.detection_done = True
        self.update_info_label()
        self.preview_button.setEnabled(True)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def show_preview_table(self):
        """Show preview table dialog."""
        dialog = ArtifactPreviewTable(self, self.data, self.detection_results)
        if dialog.exec() == QDialog.Accepted:
            self.detection_results = dialog.detection_results
            self.update_info_label()

    def get_bad_epochs(self):
        """Return list of epoch indices to reject."""
        return [
            idx
            for idx, results in self.detection_results.items()
            if results.get("reject", False)
        ]


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
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
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

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
            item.setData(epoch_idx, Qt.DisplayRole)
            item.setData(epoch_idx, Qt.UserRole)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            row_items.append(item)

            # method columns
            for col_name in method_cols:
                bad_epochs = results.get(col_name, False)
                label = "✘" if bad_epochs else "✔"
                item = QStandardItem(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bad_epochs:
                    item.setBackground(QColor("#FFF0F0"))
                    item.setForeground(QColor("#800000"))
                else:
                    item.setBackground(QColor("#F0FFF0"))
                    item.setForeground(QColor("#008000"))

                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setData(int(bad_epochs), Qt.UserRole)
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
            reject_item.setData(check_state, Qt.CheckStateRole)
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
        """Update label showing rejection statistics"""
        n_total = self.model.rowCount()
        n_rejected = 0
        for row in range(n_total):
            if (
                self.model.item(row, self.reject_col_idx).checkState()
                == Qt.CheckState.Checked
            ):
                n_rejected += 1
        n_accepted = n_total - n_rejected

        self.info_label.setText(
            f"Total: {n_total} epochs  |  "
            f"Accepted: {n_accepted}  |  "
            f"Rejected: {n_rejected}"
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

        if isinstance(fig, QWidget):
            # Qt-Backend
            fig.mne.epoch_color_ref[:, flagged_idx] = to_rgba_array(
                fig.mne.epoch_color_bad
            )

            # update traces
            for trace in fig.mne.traces:
                trace.update_color()

            fig._redraw(update_data=True)
            # update bad epochs in hscroll bar
            fig.mne.overview_bar.update_bad_epochs()

        else:
            # Matplotlib Backend
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
            reject_item.setData(check_state, Qt.CheckStateRole)

        self.update_info_label()

    def sync_results_from_table(self):
        """Sync detection results with current table state."""
        for proxy_row in range(self.proxy_model.rowCount()):
            proxy_index = self.proxy_model.index(proxy_row, 0)
            source_index = self.proxy_model.mapToSource(proxy_index)
            real_row_idx = source_index.row()

            reject_item = self.model.item(real_row_idx, self.reject_col_idx)
            is_checked = reject_item.data(Qt.CheckStateRole) == Qt.CheckState.Checked

            self.detection_results[real_row_idx]["reject"] = is_checked

    def accept(self):
        """Update detection results based on user changes."""
        self.sync_results_from_table()
        super().accept()


class EpochVisualization(QDialog):
    def __init__(self, parent, fig):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(1600, 800)
        self.fig = fig
        self.flagged_epochs = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if isinstance(fig, QWidget):
            # Qt-Backend
            fig.setParent(self)
            layout.addWidget(fig)
            self.canvas = fig
        else:
            # Matplotlib-Backend
            self.canvas = FigureCanvas(self.fig)
            layout.addWidget(self.canvas)

    def closeEvent(self, event):
        if hasattr(self.fig, "mne") and hasattr(self.fig.mne, "bad_epochs"):
            self.flagged_epochs = list(self.fig.mne.bad_epochs)

        super().closeEvent(event)
