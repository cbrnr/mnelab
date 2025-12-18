from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
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


class AutoSelectDialog(QDialog):
    def __init__(self, parent, labels):
        super().__init__(parent)
        self.setWindowTitle("Auto-Select Components")
        self.criteria = {}

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        layout.addLayout(grid)

        grid.addWidget(QLabel("Class"), 0, 0)
        grid.addWidget(QLabel("Threshold"), 0, 2)

        for idx, label in enumerate(labels):
            row = idx + 1

            checkbox = QCheckBox(label)

            if label in ["Eye", "Muscle"]:
                checkbox.setChecked(True)

            larger_than = QLabel(">")

            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setSingleStep(0.05)
            spinbox.setValue(0.90)
            spinbox.setDecimals(2)

            spinbox.setEnabled(checkbox.isChecked())
            checkbox.toggled.connect(spinbox.setEnabled)

            grid.addWidget(checkbox, row, 0)
            grid.addWidget(larger_than, row, 1)
            grid.addWidget(spinbox, row, 2)

            self.criteria[label] = (checkbox, spinbox)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        layout.addWidget(self.buttonbox)

    def get_selection_rules(self):
        rules = {}
        for label, (chk, spin) in self.criteria.items():
            if chk.isChecked():
                rules[label] = spin.value()
        return rules


class NumberSortProxyModel(QSortFilterProxyModel):
    """Helperclass to sort columns with numerical data."""

    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left, Qt.UserRole)
        right_data = self.sourceModel().data(right, Qt.UserRole)

        if left_data is None:
            return True
        if right_data is None:
            return False

        try:
            return float(left_data) < float(right_data)
        except (ValueError, TypeError):
            return str(left_data) < str(right_data)


class ICLabelDialog(QDialog):
    def __init__(self, parent, components_probs, exclude=None, labels=None):
        super().__init__(parent)
        self.setWindowTitle("ICLabel")
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

        headers = ["Component"] + self.labels + ["Exclude"]

        self.model = QStandardItemModel(len(components_probs), len(headers))
        self.model.setHorizontalHeaderLabels(headers)

        row_labels = [str(i + 1) for i in range(len(components_probs))]
        self.model.setVerticalHeaderLabels(row_labels)

        n_components = len(components_probs)
        for row_id in range(n_components):
            item = QStandardItem()
            item.setData(row_id, Qt.UserRole)
            item.setData(row_id, Qt.DisplayRole)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model.setItem(row_id, 0, item)

            for col_id, prob in enumerate(components_probs[row_id]):
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
            exclude.setCheckState(state)
            exclude.setData(int(is_excluded), Qt.UserRole)
            exclude.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.model.setItem(row_id, len(headers) - 1, exclude)

        self.proxy_model = NumberSortProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy_model)
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(True)
        self.view.setSelectionBehavior(QTableView.SelectRows)

        header = self.view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)
        for col in range(1, len(headers) - 1):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)

        button_layout = QHBoxLayout()
        self.autoselect_button = QPushButton("Auto-Select...")
        self.autoselect_button.clicked.connect(self.open_auto_select)
        button_layout.addWidget(self.autoselect_button)
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
            exclude_item.setCheckState(new_state)

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
