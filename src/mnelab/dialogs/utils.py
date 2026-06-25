# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QEvent, QRect, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QTableWidgetItem,
)


def select_all(list_widget):
    """Select all items in a QListWidget."""
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)


def set_header_alignments(model, alignments):
    """Set text alignment for each horizontal header item.

    `Qt.AlignmentFlag.AlignVCenter` is always applied automatically.

    Parameters
    ----------
    model
        A `QStandardItemModel` or `QTableWidget` whose horizontal header items will be
        updated.
    alignments
        String of alignment characters, one per column. Use `"l"` for left, `"c"` for
        center, and `"r"` for right alignment.
    """
    _map = {
        "l": Qt.AlignmentFlag.AlignLeft,
        "c": Qt.AlignmentFlag.AlignCenter,
        "r": Qt.AlignmentFlag.AlignRight,
    }
    for col, char in enumerate(alignments):
        item = model.horizontalHeaderItem(col)
        if item is not None:
            item.setTextAlignment(_map[char] | Qt.AlignmentFlag.AlignVCenter)


class IntTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

    def __lt__(self, other):
        return int(self.data(Qt.ItemDataRole.EditRole)) < int(
            other.data(Qt.ItemDataRole.EditRole)
        )

    def setData(self, role, value):
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            super().setData(role, value)
            return
        try:
            value = int(value)
        except (TypeError, ValueError):
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))

    def value(self):
        return int(self.data(Qt.ItemDataRole.DisplayRole))


class FloatTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

    def __lt__(self, other):
        return float(self.data(Qt.ItemDataRole.EditRole)) < float(
            other.data(Qt.ItemDataRole.EditRole)
        )

    def setData(self, role, value):
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            super().setData(role, value)
            return
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))

    def value(self):
        return float(self.data(Qt.ItemDataRole.DisplayRole))


class NumberSortProxyModel(QSortFilterProxyModel):
    """Helper class to sort columns with numerical data."""

    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left, Qt.ItemDataRole.UserRole)
        if left_data is None:
            left_data = self.sourceModel().data(left, Qt.ItemDataRole.CheckStateRole)
        right_data = self.sourceModel().data(right, Qt.ItemDataRole.UserRole)
        if right_data is None:
            right_data = self.sourceModel().data(right, Qt.ItemDataRole.CheckStateRole)

        if left_data is None:
            return True
        if right_data is None:
            return False

        try:
            return float(left_data) < float(right_data)
        except (ValueError, TypeError):
            return str(left_data) < str(right_data)


class CheckBoxDelegate(QStyledItemDelegate):
    """Helper class to center checkboxes in a QTableView."""

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        # remove the checkbox from the item view drawing
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        option.widget.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget
        )

        data = index.data(Qt.ItemDataRole.CheckStateRole)

        if data is None:
            check_state = Qt.CheckState.Unchecked
        else:
            check_state = Qt.CheckState(data)

        opts = QStyleOptionButton()
        opts.state |= QStyle.StateFlag.State_Enabled

        if check_state == Qt.CheckState.Checked:
            opts.state |= QStyle.StateFlag.State_On
        else:
            opts.state |= QStyle.StateFlag.State_Off

        # checkbox size
        s_size = (
            option.widget.style()
            .subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opts, option.widget)
            .size()
        )

        # center the checkbox in the cell
        rect = option.rect
        x = rect.x() + (rect.width() - s_size.width()) // 2
        y = rect.y() + (rect.height() - s_size.height()) // 2
        opts.rect = QRect(x, y, s_size.width(), s_size.height())

        # draw the checkbox
        option.widget.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_IndicatorCheckBox, opts, painter, option.widget
        )

    def editorEvent(self, event, model, _option, index):
        flags = model.flags(index)
        if not (flags & Qt.ItemFlag.ItemIsUserCheckable) or not (
            flags & Qt.ItemFlag.ItemIsEnabled
        ):
            return False

        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.toggle(model, index)
            return True
        return False

    def toggle(self, model, index):
        curr = index.data(Qt.ItemDataRole.CheckStateRole)
        new_state = (
            Qt.CheckState.Checked
            if curr != Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )
        model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
