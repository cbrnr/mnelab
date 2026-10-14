# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QPoint, QSignalBlocker, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QStyle,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
)

COL_CHECK = 0
CHECK_COLUMN_WIDTH = 30


class CheckTableWidgetItem(QTableWidgetItem):
    """Checkable table item without text."""

    def __init__(self, noun="items", checked=True):
        super().__init__()
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.setCheckState(state)
        self.setToolTip(f"Shift-click to check or uncheck a range of {noun}")


class CheckHeaderView(QHeaderView):
    """Horizontal header with a checkbox to check or uncheck all rows.

    Clicking the checkbox column emits `check_all_clicked` instead of sorting. Clicking
    any of the `unsortable` columns does nothing.

    Parameters
    ----------
    parent : QTableWidget
        Table this header belongs to.
    unsortable : tuple[int, ...]
        Columns that cannot be sorted (in addition to the checkbox column).
    """

    check_all_clicked = Signal()

    def __init__(self, parent, unsortable=()):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)  # only the default header is clickable
        self._unsortable = (COL_CHECK, *unsortable)
        self._check_state = Qt.CheckState.Checked

    def set_check_state(self, state):
        if state != self._check_state:
            self._check_state = state
            self.viewport().update()

    def paintSection(self, painter, rect, logical_index):
        painter.save()
        super().paintSection(painter, rect, logical_index)
        painter.restore()
        if logical_index != COL_CHECK:
            return
        # draw the checkbox like the checkboxes in the cells below
        option = QStyleOptionViewItem()
        option.initFrom(self)
        option.rect = rect
        option.features |= QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        option.rect = self.style().subElementRect(
            QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, self.parent()
        )
        option.rect.moveCenter(QPoint(option.rect.center().x(), rect.center().y()))
        option.state |= {
            Qt.CheckState.Checked: QStyle.StateFlag.State_On,
            Qt.CheckState.PartiallyChecked: QStyle.StateFlag.State_NoChange,
            Qt.CheckState.Unchecked: QStyle.StateFlag.State_Off,
        }[self._check_state]
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,
            option,
            painter,
            self.parent(),
        )

    def _column(self, event):
        return self.logicalIndexAt(event.position().toPoint())

    def mousePressEvent(self, event):
        if self._column(event) not in self._unsortable:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        column = self._column(event)
        if column not in self._unsortable:
            super().mouseReleaseEvent(event)
        elif column == COL_CHECK and event.button() == Qt.MouseButton.LeftButton:
            self.check_all_clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if self._column(event) not in self._unsortable:
            super().mouseDoubleClickEvent(event)


class CheckTableWidget(QTableWidget):
    """Table with a checkbox column to select multiple rows.

    The first column contains one checkbox per row. Shift-clicking a checkbox sets the
    check state of all rows between the previously and the currently clicked checkbox,
    and the checkbox in the header checks or unchecks all rows. Rows cannot be selected
    or edited.

    Parameters
    ----------
    rows : int
        Number of rows.
    columns : int
        Number of columns (including the checkbox column).
    noun : str
        Plural noun describing the rows (used in tooltips).
    unsortable : tuple[int, ...]
        Columns that cannot be sorted (in addition to the checkbox column).
    parent : QWidget | None
        Parent widget.

    Signals
    -------
    checks_changed
        Emitted after the check state of at least one row changed.
    """

    checks_changed = Signal()

    def __init__(self, rows, columns, noun="items", unsortable=(), parent=None):
        super().__init__(rows, columns, parent)
        self.noun = noun
        self._last_check_item = None  # last (un)checked item for Shift-click ranges
        self._header = CheckHeaderView(self, unsortable)
        self._header.check_all_clicked.connect(self._check_all_clicked)
        self.setHorizontalHeader(self._header)
        self._header.setStretchLastSection(True)
        self._header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(COL_CHECK, CHECK_COLUMN_WIDTH)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setShowGrid(False)
        self.itemChanged.connect(self._item_changed)

    def set_check_item(self, row, checked=True):
        """Add a checkbox to `row`."""
        with QSignalBlocker(self):  # remaining rows might not be populated yet
            self.setItem(row, COL_CHECK, CheckTableWidgetItem(self.noun, checked))

    def set_labels(self, labels):
        """Set the header labels (the label of the checkbox column should be empty)."""
        self.setHorizontalHeaderLabels(labels)
        self.horizontalHeaderItem(COL_CHECK).setToolTip(
            f"Check or uncheck all {self.noun}"
        )

    def is_checked(self, row):
        return self.item(row, COL_CHECK).checkState() == Qt.CheckState.Checked

    def checked_rows(self):
        """Return the checked rows (in the order in which they are displayed)."""
        return [row for row in range(self.rowCount()) if self.is_checked(row)]

    def update_check_state(self):
        """Update the checkbox in the header after rows were (un)checked."""
        n_checked = len(self.checked_rows())
        if n_checked == 0:
            self._header.set_check_state(Qt.CheckState.Unchecked)
        elif n_checked == self.rowCount():
            self._header.set_check_state(Qt.CheckState.Checked)
        else:
            self._header.set_check_state(Qt.CheckState.PartiallyChecked)

    def set_all_checked(self, checked):
        """Check or uncheck all rows."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        with QSignalBlocker(self):
            for row in range(self.rowCount()):
                self.item(row, COL_CHECK).setCheckState(state)
        self.update_check_state()
        self.checks_changed.emit()

    def _item_changed(self, item):
        """Update the header after a row was (un)checked.

        With Shift, all rows between the previously and the currently (un)checked row
        get the new check state.
        """
        if item.column() != COL_CHECK:
            return
        shift = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        if shift and self._last_check_item is not None:
            first, last = sorted((self._last_check_item.row(), item.row()))
            with QSignalBlocker(self):
                for row in range(first, last + 1):
                    self.item(row, COL_CHECK).setCheckState(item.checkState())
        self._last_check_item = item
        self.update_check_state()
        self.checks_changed.emit()

    @Slot()
    def _check_all_clicked(self):
        """Check all rows, or uncheck all rows if all are already checked."""
        self.set_all_checked(len(self.checked_rows()) != self.rowCount())

    def set_max_visible_rows(self, n):
        """Limit the height of the table to the header and `n` rows."""
        self.setMaximumHeight(
            int(
                self._header.sizeHint().height()
                + n * self.verticalHeader().defaultSectionSize()
                + 2 * self.frameWidth()
            )
        )


class CheckListWidget(CheckTableWidget):
    """List of texts with a checkbox in front of each text.

    Parameters
    ----------
    items : list[str]
        Texts to show.
    header : str
        Header of the text column.
    noun : str
        Plural noun describing the items (used in tooltips).
    checked : bool
        Whether all items are initially checked.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(self, items, header, noun, checked=True, parent=None):
        super().__init__(len(items), 2, noun, unsortable=(1,), parent=parent)
        for row, text in enumerate(items):
            self.set_check_item(row, checked)
            self.setItem(row, 1, QTableWidgetItem(str(text)))
        self.set_labels(["", header])
        self.horizontalHeaderItem(1).setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.update_check_state()

    def checked_texts(self):
        """Return the texts of the checked items."""
        return [self.item(row, 1).text() for row in self.checked_rows()]
