# © MNELAB developers
#
# License: BSD (3-clause)

import sys

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QStyledItemDelegate,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

ROW_HEIGHT = 30

# settings for the data type badges in the sidebar
DTYPE_COLORS = {
    "raw": ("#2563EB", "#FFFFFF"),  # blue-600 bg, white text
    "epochs": ("#92400E", "#FFFFFF"),  # amber-800 bg, white text
}


class TypeBadgeDelegate(QStyledItemDelegate):
    """Renders a rounded-rectangle badge for the data type column."""

    def paint(self, painter, option, index):
        # draw selection/hover background first (without the text to avoid flicker)
        super().paint(painter, option, index)

        dtype = index.data(Qt.ItemDataRole.DisplayRole)
        if not dtype:
            return
        bg_hex, fg_hex = DTYPE_COLORS.get(dtype.lower(), ("#6B7280", "#FFFFFF"))
        label = dtype.capitalize()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        pad_y = 5
        badge_h = rect.height() - 2 * pad_y
        badge_rect = QRectF(rect.x() + 2, rect.y() + pad_y, rect.width() - 4, badge_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg_hex))
        painter.drawRoundedRect(badge_rect, badge_h / 2, badge_h / 2)

        # add a subtle border
        painter.setPen(QColor(0, 0, 0, 40))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(badge_rect, badge_h / 2, badge_h / 2)

        font = painter.font()
        font.setPointSizeF(max(6.0, font.pointSizeF() - 1))
        painter.setFont(font)
        painter.setPen(QColor(fg_hex))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setWidth(56)
        return hint

    def createEditor(self, parent, option, index):
        return None  # badge column is not editable


class SidebarTreeWidget(QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setColumnCount(3)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setUniformRowHeights(True)
        self.setObjectName("sidebar")
        self.setMouseTracking(True)
        self.setTabKeyNavigation(False)
        # prevent double-click from toggling expand/collapse so it can trigger editing
        self.setExpandsOnDoubleClick(False)
        self.setIndentation(16)
        self.setDragEnabled(False)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.header().setMinimumSectionSize(0)
        self.setColumnWidth(1, 56)
        self.setColumnWidth(2, 28)
        self.setItemDelegateForColumn(1, TypeBadgeDelegate(self))
        self.setAccessibleName("Opened datasets")
        self._dragging = False
        if sys.platform != "darwin":
            self._apply_base_stylesheet()
        self.viewport().installEventFilter(self)

    def _apply_base_stylesheet(self):
        app = QApplication.instance()
        palette = app.palette() if isinstance(app, QApplication) else self.palette()
        base_color = palette.color(QPalette.ColorRole.Base).name()
        text_color = palette.color(QPalette.ColorRole.Text).name()
        highlight_color = palette.color(QPalette.ColorRole.Highlight).name()
        highlighted_text_color = palette.color(
            QPalette.ColorRole.HighlightedText
        ).name()
        self.setPalette(palette)
        self.viewport().setPalette(palette)
        self.viewport().setAutoFillBackground(True)
        self.setStyleSheet(f"""
            QTreeWidget#sidebar {{ outline: 0; background-color: {base_color}; }}
            QTreeWidget#sidebar::item {{
                background: {base_color};
                color: {text_color};
            }}
            QTreeWidget#sidebar::item:hover {{
                background: transparent;
                color: {text_color};
            }}
            QTreeWidget#sidebar::item:selected {{
                background: {highlight_color};
                color: {highlighted_text_color};
            }}
            QTreeWidget#sidebar::item:focus {{
                background: {highlight_color};
                color: {highlighted_text_color};
            }}
        """)

    def refresh_theme(self):
        if sys.platform != "darwin":
            self._apply_base_stylesheet()
            self.viewport().update()

    def mousePressEvent(self, event):
        self._dragging = False
        item = self.itemAt(event.pos())
        if item:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        # suppress cursor-following selection while holding the mouse button
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._dragging = True
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            return  # don't change selection when releasing after a drag
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.parent.event(event)
        else:
            event.ignore()

    def set_dtype(self, item, dtype):
        """Set the data type badge for the given tree item."""
        item.setText(1, dtype)
        item.setToolTip(1, f"Data Type: {dtype.capitalize()}" if dtype else "")

    def set_badges_visible(self, visible):
        """Show or hide the data type badge column."""
        self.setColumnHidden(1, not visible)

    def make_item(self, name, dataset_id):
        """Create a styled tree item for a dataset."""
        item = QTreeWidgetItem(["", "", ""])
        item.setText(0, name)
        item.setData(0, Qt.ItemDataRole.UserRole, dataset_id)
        item.setSizeHint(0, QSize(0, ROW_HEIGHT))
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )
        return item

    def style_items(self):
        """Update the close button for the item currently under the cursor."""
        pos = self.viewport().mapFromGlobal(QCursor.pos())
        hovered = self.itemAt(pos)
        self.showCloseButton(hovered)

    def _all_items(self):
        """Yield every tree item in the widget, depth-first."""

        def _recurse(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                yield child
                yield from _recurse(child)

        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            yield top
            yield from _recurse(top)

    def eventFilter(self, source, event):
        if source == self.viewport() and event.type() == QEvent.Type.MouseMove:
            item = self.itemAt(event.pos())
            self.showCloseButton(item)
        elif source == self.viewport() and event.type() == QEvent.Type.Leave:
            self.showCloseButton(None)
        elif isinstance(source, QToolButton) and event.type() == QEvent.Type.Enter:
            source.setStyleSheet("""
                QToolButton {
                    background: rgba(128, 128, 128, 0.2);
                    border-radius: 4px;
                }
                QToolButton:pressed {
                    background: rgba(128, 128, 128, 0.35);
                    border-radius: 4px;
                }
            """)
        elif isinstance(source, QToolButton) and event.type() == QEvent.Type.Leave:
            # reset hover style, then transfer button to whichever row the cursor is on
            source.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                }
                QToolButton:pressed {
                    background: rgba(128, 128, 128, 0.35);
                    border-radius: 4px;
                }
            """)
            pos = self.viewport().mapFromGlobal(QCursor.pos())
            self.showCloseButton(self.itemAt(pos))
        return False

    def showCloseButton(self, hovered_item):
        """Show the close button on the hovered item; remove it from all others."""
        for item in self._all_items():
            if item is hovered_item:
                if self.itemWidget(item, 2) is not None:
                    continue  # button already present, don't recreate
                dataset_id = item.data(0, Qt.ItemDataRole.UserRole)
                btn = QToolButton()
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.setFixedSize(24, ROW_HEIGHT)
                btn.setIcon(QIcon.fromTheme("close-data"))
                btn.setToolTip("Close Dataset")
                btn.setStyleSheet("""
                    QToolButton {
                        background: transparent;
                        border: none;
                    }
                    QToolButton:pressed {
                        background: rgba(128, 128, 128, 0.35);
                        border-radius: 4px;
                    }
                """)
                btn.installEventFilter(self)
                btn.clicked.connect(lambda _, did=dataset_id: self._close_dataset(did))
                self.setItemWidget(item, 2, btn)
            else:
                self.removeItemWidget(item, 2)

    def _close_dataset(self, dataset_id):
        """Close a dataset, cascading to descendants with a confirmation dialog."""
        descendants = self.parent.model.find_descendants(dataset_id)
        if descendants:
            n = len(descendants)
            msg = QMessageBox(self)
            msg.setWindowTitle("Close Dataset")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                f"Closing this dataset will also close {n} child "
                f"dataset{'s' if n != 1 else ''}."
            )
            msg.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if msg.exec() != QMessageBox.StandardButton.Ok:
                return
        self.parent.model.remove_data_cascade(dataset_id)


class SidebarWidget(QWidget):
    """Container holding the sidebar tree and a bottom collapse-all toolbar."""

    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = SidebarTreeWidget(self)
        layout.addWidget(self.tree)

        self._bottom_bar = QWidget()
        self._bottom_bar.setAutoFillBackground(True)
        bottom_layout = QHBoxLayout(self._bottom_bar)
        bottom_layout.setContentsMargins(4, 2, 4, 2)

        self._collapse_btn = QToolButton()
        self._collapse_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._collapse_btn.setIcon(QIcon.fromTheme("unfold-less"))
        self._collapse_btn.setToolTip("Collapse All")
        self._collapse_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 0.2);
                border-radius: 4px;
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 0.35);
                border-radius: 4px;
            }
        """)
        self._collapse_btn.clicked.connect(self.tree.collapseAll)
        self._collapse_btn.hide()

        bottom_layout.addStretch()
        bottom_layout.addWidget(self._collapse_btn)
        layout.addWidget(self._bottom_bar)

        self._apply_bar_background()

    def _apply_bar_background(self):
        """Match the bottom bar background to the sidebar tree's base color."""
        app = QApplication.instance()
        palette = app.palette() if isinstance(app, QApplication) else self.palette()
        base_color = palette.color(QPalette.ColorRole.Base)
        bar_palette = self._bottom_bar.palette()
        bar_palette.setColor(QPalette.ColorRole.Window, base_color)
        self._bottom_bar.setPalette(bar_palette)

    def refresh_theme(self):
        """Propagate theme refresh to the tree and update the bar background."""
        self.tree.refresh_theme()
        self._apply_bar_background()

    def enterEvent(self, event):
        self._collapse_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._collapse_btn.hide()
        super().leaveEvent(event)
