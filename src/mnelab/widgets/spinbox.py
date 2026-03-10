# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QWidget


class _StepButton(QWidget):
    """Symbol-only step button rendered as an overlay inside a spin box."""

    clicked = Signal()

    def __init__(self, symbol, parent=None):
        super().__init__(parent)
        self._symbol = symbol
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._hovered:
            color = self.palette().color(QPalette.Highlight)
            color.setAlpha(60)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)
        painter.setPen(self.palette().color(QPalette.WindowText))
        font = painter.font()
        font.setPixelSize(max(10, self.height() - 8))
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._symbol)


class FlatDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox with inline − / + step buttons instead of tiny arrows.

    The buttons are rendered as plain symbols (no button chrome) inside the
    right edge of the input field.  Hovering highlights them with a subtle
    rounded background.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self._minus_btn = _StepButton("−", self)
        self._plus_btn = _StepButton("+", self)
        self._minus_btn.clicked.connect(self.stepDown)
        self._plus_btn.clicked.connect(self.stepUp)

    def sizeHint(self):
        sh = super().sizeHint()
        return QSize(sh.width() + self._btn_area_width(sh.height()), sh.height())

    def minimumSizeHint(self):
        msh = super().minimumSizeHint()
        return QSize(msh.width() + self._btn_area_width(msh.height()), msh.height())

    def _btn_area_width(self, h):
        # Two buttons of size (h-4), one gap pixel, one right-edge pixel, two
        # breathing pixels — must match _reposition_buttons exactly.
        return (h - 4) * 2 + 1 + 1 + 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Defer so Qt's native-style child-geometry adjustments settle first.
        QTimer.singleShot(0, self._reposition_buttons)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_buttons)

    def _reposition_buttons(self):
        h = self.height()
        btn_size = h - 4
        gap = 1
        x_plus = self.width() - btn_size - 1
        x_minus = x_plus - gap - btn_size
        self._plus_btn.setGeometry(x_plus, 2, btn_size, btn_size)
        self._minus_btn.setGeometry(x_minus, 2, btn_size, btn_size)

        # Compute the right text margin from measured positions so that the
        # margin is exact regardless of platform-specific frame offsets.  The
        # QLineEdit (in its own coordinate space) must reserve the horizontal
        # distance from its right edge back to the left edge of the minus
        # button, plus 2 px breathing room.
        le = self.lineEdit()
        le_right_in_spinbox = le.x() + le.width()
        right_margin = max(0, le_right_in_spinbox - x_minus + 2)
        le.setTextMargins(0, 0, right_margin, 0)
