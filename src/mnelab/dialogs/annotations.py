# © MNELAB developers
#
# License: BSD (3-clause)

import re
from collections import defaultdict

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mnelab.dialogs.utils import IntTableWidgetItem, select_all

_HEX_PARTIAL = re.compile(r"#[0-9A-Fa-f]{0,6}$")
_HEX_FULL = re.compile(r"#[0-9A-Fa-f]{6}$")


class _HexColorValidator(QValidator):
    """Validator that enforces the # prefix and hex digits for color codes."""

    def validate(self, text, pos):
        if _HEX_FULL.match(text):
            return QValidator.State.Acceptable, text, pos
        if _HEX_PARTIAL.match(text):
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Invalid, text, pos


class AnnotationsDialog(QDialog):
    def __init__(self, parent, onset, duration, description):
        super().__init__(parent)
        self.setWindowTitle("Edit Annotations")

        self.table = QTableWidget(len(onset), 3)

        for row, annotation in enumerate(zip(onset, duration, description)):
            self.table.setItem(row, 0, IntTableWidgetItem(annotation[0]))
            self.table.setItem(row, 1, IntTableWidgetItem(annotation[1]))
            self.table.setItem(row, 2, QTableWidgetItem(annotation[2]))

        self.table.setHorizontalHeaderLabels(["Onset", "Duration", "Type"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)
        hbox = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.remove_button = QPushButton("-")
        self.counts_button = QPushButton("Counts...")
        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        hbox.addWidget(self.add_button)
        hbox.addWidget(self.remove_button)
        hbox.addWidget(self.counts_button)
        hbox.addStretch()
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.table.itemSelectionChanged.connect(self.toggle_buttons)
        self.remove_button.clicked.connect(self.remove_event)
        self.add_button.clicked.connect(self.add_event)
        self.remove_button.clicked.connect(self.toggle_buttons)
        self.add_button.clicked.connect(self.toggle_buttons)
        self.counts_button.clicked.connect(self.open_counts_dialog)
        self.toggle_buttons()
        self.setMinimumSize(600, 500)
        self.setFocus()

    @property
    def unique_annotations(self):
        _unique_annotations = defaultdict(int)
        for i in range(self.table.rowCount()):
            if item := self.table.item(i, 2):
                _unique_annotations[item.text()] += 1
        return _unique_annotations

    @Slot()
    def toggle_buttons(self):
        """Toggle + and - buttons."""
        n_items = len(self.table.selectedItems())
        if self.table.rowCount() == 0:  # no annotations available
            self.remove_button.setEnabled(False)
            self.counts_button.setEnabled(False)
        elif n_items == 3:  # one row (3 items) selected
            self.remove_button.setEnabled(True)
        elif n_items > 3:  # more than one row selected
            self.remove_button.setEnabled(True)
        else:  # no rows selected
            self.remove_button.setEnabled(False)
            self.counts_button.setEnabled(True)

    def add_event(self):
        if self.table.selectedIndexes():
            current_row = self.table.selectedIndexes()[0].row()
            pos = int(self.table.item(current_row, 0).data(Qt.ItemDataRole.DisplayRole))
        else:
            current_row = 0
            pos = 0
        self.table.setSortingEnabled(False)
        self.table.insertRow(current_row)
        self.table.setItem(current_row, 0, IntTableWidgetItem(pos))
        self.table.setItem(current_row, 1, IntTableWidgetItem(0))
        self.table.setItem(current_row, 2, QTableWidgetItem("New Annotation"))
        self.table.setSortingEnabled(True)

    def remove_event(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        self.table.clearSelection()
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def open_counts_dialog(self):
        dialog = EventCountsDialog(self)
        dialog.exec()


class EventCountsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Annotation Counts")
        self.unique_annotations = parent.unique_annotations

        self.counts_table = QTableWidget(0, 2)
        self.counts_table.setHorizontalHeaderLabels(["Description", "Count"])
        self.counts_table.horizontalHeader().setStretchLastSection(True)
        self.counts_table.verticalHeader().setVisible(False)
        self.counts_table.setShowGrid(False)
        self.counts_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.fill_counts_table()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.counts_table)
        buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)

        self.counts_table.setMinimumHeight(225)
        self.setFocus()

    def fill_counts_table(self):
        self.counts_table.setRowCount(0)
        for row, (id_, count) in enumerate(sorted(self.unique_annotations.items())):
            id_item = IntTableWidgetItem(id_)
            id_item.setFlags(id_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.counts_table.insertRow(row)
            self.counts_table.setItem(row, 0, id_item)
            self.counts_table.setItem(row, 1, QTableWidgetItem(str(count)))


class AnnotationTypesDialog(QDialog):
    """Dialog for selecting annotation types to import or export."""

    def __init__(self, parent, types, title="Select annotation types", label=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        if label is not None:
            vbox.addWidget(QLabel(label))
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.insertItems(0, types)
        select_all(self.list_widget)
        vbox.addWidget(self.list_widget)
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.list_widget.itemSelectionChanged.connect(self.toggle_ok)
        self.toggle_ok()
        self.setFocus()

    @Slot()
    def toggle_ok(self):
        """Disable OK when nothing is selected."""
        self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.list_widget.selectedItems())
        )

    @property
    def selected_types(self):
        """Return list of selected annotation type strings."""
        return [item.text() for item in self.list_widget.selectedItems()]


class AnnotationColorsDialog(QDialog):
    """Dialog for managing custom annotation description to color mappings."""

    def __init__(self, parent, colors):
        super().__init__(parent)
        self.setWindowTitle("Annotation Colors")

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Description", "Color"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._toggle_buttons)

        for desc, color in colors.items():
            self._insert_row(desc, color)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)

        hbox = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.remove_button = QPushButton("-")
        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        hbox.addWidget(self.add_button)
        hbox.addWidget(self.remove_button)
        hbox.addStretch()
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)

        self.add_button.clicked.connect(self._add_row)
        self.remove_button.clicked.connect(self._remove_row)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self._toggle_buttons()
        self.setMinimumSize(400, 300)
        self.setFocus()

    def _make_color_cell(self, color):
        """Create a cell widget showing a circular swatch and editable hex value."""
        container = QWidget()
        container.setProperty("color", color)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        swatch = QPushButton()
        swatch.setFixedSize(20, 20)
        self._style_swatch(swatch, color)
        swatch.clicked.connect(lambda: self._pick_color(container))
        layout.addWidget(swatch)

        qcolor = QColor(color)
        hex_edit = QLineEdit(qcolor.name() if qcolor.isValid() else color)
        hex_edit.setMaxLength(7)
        hex_edit.setValidator(_HexColorValidator(hex_edit))
        hex_edit.setStyleSheet("QLineEdit { border: none; background: transparent; }")
        hex_edit.textEdited.connect(lambda text: self._hex_edited(container, text))
        layout.addWidget(hex_edit)

        return container

    def _style_swatch(self, btn, color):
        """Apply a circular background style to the swatch button."""
        qcolor = QColor(color)
        if qcolor.isValid():
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {qcolor.name()}; "
                "border-radius: 10px; "
                "border: 1px solid rgba(128,128,128,0.5); padding: 0px; }}"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { border-radius: 10px; "
                "border: 1px solid rgba(128,128,128,0.5); padding: 0px; }"
            )

    def _pick_color(self, container):
        """Open a color picker and update the cell widget."""
        initial = QColor(container.property("color") or "#ffffff")
        color = QColorDialog.getColor(initial, self, "Pick Color")
        if color.isValid():
            container.setProperty("color", color.name())
            swatch = container.findChild(QPushButton)
            hex_edit = container.findChild(QLineEdit)
            if swatch:
                self._style_swatch(swatch, color.name())
            if hex_edit:
                hex_edit.setText(color.name())

    def _hex_edited(self, container, text):
        """Update the swatch when the user types a valid hex color."""
        qcolor = QColor(text)
        if qcolor.isValid():
            container.setProperty("color", qcolor.name())
            swatch = container.findChild(QPushButton)
            if swatch:
                self._style_swatch(swatch, qcolor.name())

    def _insert_row(self, desc="New Annotation", color="#ffffff"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(desc))
        cell = self._make_color_cell(color)
        self.table.setCellWidget(row, 1, cell)

    @Slot()
    def _add_row(self):
        self._insert_row()
        self._toggle_buttons()

    @Slot()
    def _remove_row(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        self.table.clearSelection()
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
        self._toggle_buttons()

    @Slot()
    def _toggle_buttons(self):
        self.remove_button.setEnabled(bool(self.table.selectedItems()))

    @property
    def annotation_colors(self):
        """Return the current description to color mapping as a dict."""
        result = {}
        for row in range(self.table.rowCount()):
            desc_item = self.table.item(row, 0)
            cell = self.table.cellWidget(row, 1)
            if desc_item and cell:
                desc = desc_item.text().strip()
                color = cell.property("color")
                if desc and color:
                    result[desc] = color
        return result
