# © MNELAB developers
#
# License: BSD (3-clause)

import matplotlib.gridspec as gridspec
import numpy as np
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


def get_detailed_ica_properties(ica, raw, comp_id, ic_probs, labels):
    # initialize mne properties plot
    figs = ica.plot_properties(raw, picks=comp_id, show=False)
    fig = figs[0]

    # adjust overall figure dimensions
    w, h = fig.get_size_inches()
    fig.set_size_inches(w, h + 0.5)

    # define main grid structure
    gs = gridspec.GridSpec(3, 2, figure=fig, height_ratios=[1, 0.3, 1])

    # create nested grids for column-specific spacing
    gs_left_group = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=gs[:2, 0], hspace=0.2, height_ratios=[3.75, 1]
    )
    gs_right_group = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=gs[:2, 1], hspace=0, height_ratios=[3.5, 1]
    )

    # map existing mne axes to new grid locations
    fig.axes[0].set_subplotspec(gs_left_group[0])
    fig.axes[1].set_subplotspec(gs_right_group[0])
    fig.axes[2].set_subplotspec(gs_right_group[1])
    fig.axes[3].set_subplotspec(gs[2, 0])
    fig.axes[4].set_subplotspec(gs[2, 1])

    # custom probability bar plot
    labels = [label.replace(" ", "\n") for label in labels]
    ax_hist = fig.add_subplot(gs_left_group[1])

    colors = ["#4c72b0"] * len(labels)
    colors[np.argmax(ic_probs)] = "#228B22"

    x_pos = range(len(labels))
    ax_hist.bar(x_pos, ic_probs, color=colors)
    ax_hist.set_xticks(x_pos)
    ax_hist.set_xticklabels(labels, ha="center", fontsize=7)
    ax_hist.tick_params(axis="x", which="both", length=0)
    ax_hist.set_ylim(0, 1.1)
    ax_hist.set_yticks([])
    ax_hist.set_facecolor("none")

    # keep only the bottom spine
    for name, spine in ax_hist.spines.items():
        if name != "bottom":
            spine.set_visible(False)

    # annotate bars with probability values
    for i, v in enumerate(ic_probs):
        ax_hist.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=8)

    fig.align_ylabels([ax_hist, fig.axes[3]])
    fig.tight_layout()
    return fig


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
