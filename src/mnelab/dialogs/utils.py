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


class IntTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))

    def __lt__(self, other):
        return int(self.data(Qt.EditRole)) < int(other.data(Qt.EditRole))

    def setData(self, role, value):
        try:
            value = int(value)
        except ValueError:
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))

    def value(self):
        return int(self.data(Qt.DisplayRole))


class FloatTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))

    def __lt__(self, other):
        return float(self.data(Qt.EditRole)) < float(other.data(Qt.EditRole))

    def setData(self, role, value):
        try:
            value = float(value)
        except ValueError:
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))

    def value(self):
        return float(self.data(Qt.DisplayRole))


class NumberSortProxyModel(QSortFilterProxyModel):
    """Helper class to sort columns with numerical data."""

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


class CheckBoxDelegate(QStyledItemDelegate):
    """Helper class to center checkboxes in a QTableView."""

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        # remove the checkbox from the item view drawing
        option.features &= ~QStyleOptionViewItem.HasCheckIndicator
        option.widget.style().drawControl(
            QStyle.CE_ItemViewItem, option, painter, option.widget
        )

        data = index.data(Qt.CheckStateRole)

        if data is None:
            check_state = Qt.CheckState.Unchecked
        else:
            check_state = Qt.CheckState(data)

        opts = QStyleOptionButton()
        opts.state |= QStyle.State_Enabled

        if check_state == Qt.CheckState.Checked:
            opts.state |= QStyle.State_On
        else:
            opts.state |= QStyle.State_Off

        # checkbox size
        s_size = (
            option.widget.style()
            .subElementRect(QStyle.SE_CheckBoxIndicator, opts, option.widget)
            .size()
        )

        # center the checkbox in the cell
        rect = option.rect
        x = rect.x() + (rect.width() - s_size.width()) // 2
        y = rect.y() + (rect.height() - s_size.height()) // 2
        opts.rect = QRect(x, y, s_size.width(), s_size.height())

        # draw the checkbox
        option.widget.style().drawPrimitive(
            QStyle.PE_IndicatorCheckBox, opts, painter, option.widget
        )

    def editorEvent(self, event, model, _option, index):
        flags = model.flags(index)
        if not (flags & Qt.ItemIsUserCheckable) or not (flags & Qt.ItemIsEnabled):
            return False

        if (
            event.type() == QEvent.MouseButtonRelease
            and event.button() == Qt.LeftButton
        ):
            self.toggle(model, index)
            return True
        return False

    def toggle(self, model, index):
        curr = index.data(Qt.CheckStateRole)
        new_state = (
            Qt.CheckState.Checked
            if curr != Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )
        model.setData(index, new_state, Qt.CheckStateRole)
