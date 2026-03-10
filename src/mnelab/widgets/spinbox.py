# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QSpinBox, QWidget


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
        if self.parent().isEnabled():
            self._hovered = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._hovered:
            self._hovered = False
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent().isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._hovered and self.parent().isEnabled():
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


class _FlatSpinBoxMixin:
    """Mixin that replaces the native spin-box arrows with inline − / + buttons."""

    def _init_buttons(self):
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self._minus_btn = _StepButton("−", self)
        self._plus_btn = _StepButton("+", self)
        self._minus_btn.clicked.connect(self.stepDown)
        self._plus_btn.clicked.connect(self.stepUp)

    def minimumSizeHint(self):
        msh = super().minimumSizeHint()
        h = msh.height()
        # reserve space for two buttons (h-4 each), one gap pixel, and one right-edge
        # pixel (matching _reposition_buttons)
        return QSize(msh.width() + (h - 4) * 2 + 2, h)

    def sizeHint(self):
        sh = super().sizeHint()
        h = sh.height()
        return QSize(sh.width() + (h - 4) * 2 + 2, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition_buttons()

    def _reposition_buttons(self):
        h = self.height()
        btn_size = h - 4
        gap = 1
        x_plus = self.width() - btn_size - 1
        x_minus = x_plus - gap - btn_size
        self._plus_btn.setGeometry(x_plus, 2, btn_size, btn_size)
        self._minus_btn.setGeometry(x_minus, 2, btn_size, btn_size)
        le = self.lineEdit()
        le_right_in_spinbox = le.x() + le.width()
        right_margin = max(0, le_right_in_spinbox - x_minus + 2)
        le.setTextMargins(0, 0, right_margin, 0)


class FlatDoubleSpinBox(_FlatSpinBoxMixin, QDoubleSpinBox):
    """QDoubleSpinBox with inline − / + step buttons instead of up/down arrows.

    The buttons are rendered as plain symbols (no button chrome) inside the right edge
    of the input field.  Hovering highlights them with a subtle rounded background.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_buttons()


class FlatSpinBox(_FlatSpinBoxMixin, QSpinBox):
    """QSpinBox with inline − / + step buttons instead of up/down arrows.

    The buttons are rendered as plain symbols (no button chrome) inside the right edge
    of the input field.  Hovering highlights them with a subtle rounded background.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_buttons()
