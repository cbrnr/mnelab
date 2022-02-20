# © MNELAB developers
#
# License: BSD (3-clause)

import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


def populate_tree(parent, nodes):
    if isinstance(nodes, list):  # struct (available as list)
        for i, v in enumerate(nodes):
            item = QTreeWidgetItem(parent)
            item.setText(0, f"[{i}]")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            populate_tree(item, v)
    else:  # dict containing variable/value pairs
        for k, v in nodes.items():
            item = QTreeWidgetItem(parent)
            item.setText(0, k)
            if isinstance(v, dict):
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                populate_tree(item, v)
            elif isinstance(v, list):
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                populate_tree(item, v)
            else:
                item.setText(1, type(v).__name__)
                if isinstance(v, np.ndarray):
                    item.setText(2, " × ".join(map(str, v.shape)))
                    if v.ndim != 2:  # only two-dimensional arrays can be loaded
                        item.setFlags(Qt.NoItemFlags)
                else:
                    item.setFlags(Qt.NoItemFlags)
                    item.setText(3, repr(v))


class MatDialog(QDialog):
    def __init__(self, parent, fname, nodes):
        super().__init__(parent)
        self.setWindowTitle("Select variable")

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Name", "Type", "Shape", "Value"])
        self.tree.setColumnWidth(0, 175)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 125)

        self.root = QTreeWidgetItem(self.tree)
        self.root.setText(0, fname)
        self.root.setFlags(self.root.flags() & ~Qt.ItemIsSelectable)

        populate_tree(self.root, nodes)

        self.tree.expandAll()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.tree)
        hbox = QHBoxLayout()
        self._fs = QDoubleSpinBox()
        self._fs.setMaximum(999999)
        self._fs.setValue(250)
        self._fs.setDecimals(2)
        self._fs.setSuffix(" Hz")
        hbox.addWidget(QLabel("Sampling frequency:"))
        hbox.addWidget(self._fs)
        hbox.addStretch()
        self._transpose = QCheckBox("Transpose")
        self._transpose.setChecked(False)
        hbox.addWidget(self._transpose)
        vbox.addLayout(hbox)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.tree.itemSelectionChanged.connect(self.toggle)
        self.toggle()
        self.resize(650, 550)

    @property
    def name(self):
        item = self.tree.selectedItems()[0]
        text = item.text(0)
        parent = item.parent()
        while parent is not self.root:
            text = f"{parent.text(0)}.{text}"
            parent = parent.parent()
        return text

    @property
    def fs(self):
        return self._fs.value()

    @property
    def transpose(self):
        return self._transpose.isChecked()

    @Slot()
    def toggle(self):
        """Toggle OK and Transpose buttons."""
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
        if (items := self.tree.selectedItems()):
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
            shape = [int(dim) for dim in items[0].text(2).split(" × ")]
            if shape[0] > shape[1]:  # check transpose if there are more rows than columns
                self._transpose.setChecked(True)
            else:
                self._transpose.setChecked(False)
