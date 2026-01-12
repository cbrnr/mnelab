# © MNELAB developers
#
# License: BSD (3-clause)

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from mnelab.dialogs.utils import (
    CheckBoxDelegate,
    NumberSortProxyModel,
    get_detailed_ica_properties,
)


class PlotDetailDialog(QDialog):
    def __init__(self, parent, fig):
        super().__init__(parent)
        self.resize(950, 700)

        layout = QVBoxLayout(self)

        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.setModal(False)


class AutoSelectDialog(QDialog):
    def __init__(self, parent, labels):
        super().__init__(parent)
        self.setWindowTitle("Auto-Select Components")
        self.criteria = {}

        layout = QVBoxLayout(self)

        grid = QGridLayout()

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        layout.addLayout(grid)

        grid.addWidget(QLabel("Label"), 0, 0)
        grid.addWidget(QLabel("Threshold"), 0, 2)

        for idx, label in enumerate(labels):
            row = idx + 1

            checkbox = QCheckBox(label)

            if label in ["Eye", "Muscle"]:
                checkbox.setChecked(True)

            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setSingleStep(0.05)
            spinbox.setValue(0.90)
            spinbox.setDecimals(2)

            spinbox.setEnabled(checkbox.isChecked())
            checkbox.toggled.connect(spinbox.setEnabled)

            grid.addWidget(checkbox, row, 0, Qt.AlignLeft)
            grid.addWidget(QLabel(">"), row, 1, Qt.AlignRight)
            grid.addWidget(spinbox, row, 2)

            self.criteria[label] = checkbox, spinbox

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        layout.addWidget(self.buttonbox)

        self.setFixedSize(300, self.sizeHint().height())

    def get_selection_rules(self):
        rules = {}
        for label, (chk, spin) in self.criteria.items():
            if chk.isChecked():
                rules[label] = spin.value()
        return rules


class ICLabelDialog(QDialog):
    def __init__(self, parent, raw, ica, components_probs, exclude=None, labels=None):
        super().__init__(parent)
        self.setWindowTitle("Label ICs")
        self.setMinimumSize(800, 500)
        self.raw = raw
        self.ica = ica
        self.probs = components_probs
        if labels is None:
            self.labels = [
                "Brain",
                "Muscle",
                "Eye",
                "Heart",
                "Line Noise",
                "Channel Noise",
                "Other",
            ]
        else:
            self.labels = labels

        if exclude is None:
            exclude_set = set()
        else:
            exclude_set = {int(x) for x in exclude}

        headers = ["IC"] + self.labels + ["Exclude"]
        self.check_col = len(headers) - 1

        self.model = QStandardItemModel(len(self.probs), len(headers))
        self.model.setHorizontalHeaderLabels(headers)

        row_labels = [str(i + 1) for i in range(len(self.probs))]
        self.model.setVerticalHeaderLabels(row_labels)

        n_components = len(self.probs)
        for row_id in range(n_components):
            item = QStandardItem()
            item.setData(row_id, Qt.UserRole)
            item.setData(row_id, Qt.DisplayRole)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model.setItem(row_id, 0, item)

            for col_id, prob in enumerate(self.probs[row_id]):
                prob_item = QStandardItem()
                prob_item.setData(f"{prob:.2f}", Qt.DisplayRole)
                prob_item.setData(prob, Qt.UserRole)
                prob_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                prob_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                alpha = int(prob * 200)
                color = QColor(34, 139, 34, alpha)
                prob_item.setBackground(QBrush(color))

                self.model.setItem(row_id, col_id + 1, prob_item)

            exclude = QStandardItem()
            exclude.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
            )
            is_excluded = row_id in exclude_set
            state = Qt.CheckState.Checked if is_excluded else Qt.CheckState.Unchecked
            exclude.setData(state, Qt.CheckStateRole)
            self.model.setItem(row_id, self.check_col, exclude)

        self.proxy_model = NumberSortProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy_model)
        self.view.setItemDelegateForColumn(self.check_col, CheckBoxDelegate(self))

        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setEditTriggers(QTableView.NoEditTriggers)
        self.view.selectionModel().selectionChanged.connect(self.selection_state)
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(True)

        header = self.view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.check_col, QHeaderView.ResizeToContents)
        for col in range(1, self.check_col):
            header.setSectionResizeMode(col, QHeaderView.Stretch)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)

        button_layout = QHBoxLayout()
        self.autoselect_button = QPushButton("Auto-Select...")
        self.reset_button = QPushButton("Reset All")
        self.visualize_button = QPushButton("Visualize IC properties")
        self.visualize_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_exclusions)
        self.autoselect_button.clicked.connect(self.open_auto_select)
        self.visualize_button.clicked.connect(self.plot_ic_properties)
        button_layout.addWidget(self.autoselect_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.visualize_button)
        button_layout.addStretch()

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        button_layout.addWidget(self.buttonbox)

        vbox.addLayout(button_layout)
        self.resize(900, 600)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def open_auto_select(self):
        dialog = AutoSelectDialog(self, self.labels)
        if dialog.exec():
            rules = dialog.get_selection_rules()
            self.apply_auto_selection(rules)

    def apply_auto_selection(self, rules):
        label_col_map = {name: i + 1 for i, name in enumerate(self.labels)}

        exclude_col = self.model.columnCount() - 1

        for row in range(self.model.rowCount()):
            should_exclude = False

            for label, threshold in rules.items():
                col_idx = label_col_map.get(label)
                if col_idx:
                    prob_item = self.model.item(row, col_idx)
                    prob = prob_item.data(Qt.UserRole)

                    if prob >= threshold:
                        should_exclude = True
                        break

            exclude_item = self.model.item(row, exclude_col)
            new_state = Qt.Checked if should_exclude else Qt.Unchecked
            exclude_item.setData(new_state, Qt.CheckStateRole)

    def get_excluded_indices(self):
        excluded_comp = []
        for row in range(self.model.rowCount()):
            last_col_idx = self.model.columnCount() - 1
            item = self.model.item(row, last_col_idx)

            if item.checkState() == Qt.CheckState.Checked:
                id_item = self.model.item(row, 0)
                comp_id = id_item.data(Qt.UserRole)
                excluded_comp.append(comp_id)
        return excluded_comp

    def reset_exclusions(self):
        exclude_col = self.model.columnCount() - 1
        for row in range(self.model.rowCount()):
            item = self.model.item(row, exclude_col)
            item.setData(Qt.CheckState.Unchecked, Qt.CheckStateRole)

    def selection_state(self):
        has_selection = self.view.selectionModel().hasSelection()
        self.visualize_button.setEnabled(has_selection)

    def plot_ic_properties(self):
        selected_rows = self.view.selectionModel().selectedRows()

        proxy_index = selected_rows[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        comp_id = self.model.item(source_index.row(), 0).data(Qt.UserRole)

        fig = get_detailed_ica_properties(
            ica=self.ica,
            raw=self.raw,
            comp_id=comp_id,
            ic_probs=self.probs[comp_id],
            labels=self.labels,
        )
        self.detail_plot = PlotDetailDialog(self, fig)
        self.detail_plot.show()
