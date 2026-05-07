# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyledItemDelegate

ROW_HEIGHT = 30

# settings for the data type badges in the sidebar
DTYPE_COLORS = {
    "raw": ("#2563EB", "#FFFFFF"),  # blue-600 bg, white text
    "epochs": ("#92400E", "#FFFFFF"),  # amber-800 bg, white text
}


class TypeBadgeDelegate(QStyledItemDelegate):
    """Renders a rounded-rectangle badge for the data type column."""

    def paint(self, painter, option, index):
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
