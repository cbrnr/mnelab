# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mnelab.utils import monospace_font

_HOVER_BTN_STYLE = """
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
    }"""

# maps info row key → icon shown to the left of the key label
_ICON_MAP = {
    "File Name": "file",
    "Channels": "chan-props",
    "Events": "events",
    "Annotations": "annotations",
    "Montage": "plot-locations",
    "Reference": "change-reference",
}

# vertical space (in pixels) between a heading and the entries below it
HEADING_SPACING = 6

# vertical space (in pixels) above the first heading and between sections
SECTION_SPACING = 30

# maximum number of recent files shown in the empty widget
MAX_RECENT_LINKS = 5

dev_label = (
    '<p align="right"><font color="red"><small>Development Version</small></font></p>'
)


def _gray():
    """Return the color used for headings and key badges."""
    dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return "#999" if dark else "#777"


def _make_heading(text):
    heading = QLabel(text)
    font = heading.font()
    font.setBold(True)
    font.setPointSizeF(font.pointSizeF() * 1.15)
    heading.setFont(font)
    heading.setStyleSheet(f"color: {_gray()};")
    return heading


def _make_key(text):
    """Return a label that displays `text` as a key on a rounded rectangle."""
    dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    key = QLabel(text)
    font = monospace_font()
    font.setBold(True)
    font.setPointSizeF(QApplication.font().pointSizeF() * 0.9)
    key.setFont(font)
    key.setAlignment(Qt.AlignmentFlag.AlignCenter)
    key.setMinimumWidth(24)
    key.setStyleSheet(
        f"color: {_gray()}; background-color: {'#3a3a3a' if dark else '#e2e2e2'};"
        "border-radius: 4px; padding: 1px 4px;"
    )
    return key


def _make_shortcuts(actions):
    """Return a widget that lists the shortcuts of `actions`."""
    widget = QWidget()
    grid = QGridLayout(widget)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setVerticalSpacing(2)
    grid.setHorizontalSpacing(12)
    grid.setColumnStretch(2, 1)
    for row, action in enumerate(actions):
        name = action.text().replace("&", "").replace(".", "")
        shortcut = action.shortcut().toString(
            format=QKeySequence.SequenceFormat.NativeText
        )
        modifier, key = shortcut[:-1].strip(), shortcut[-1:]
        sep = modifier.endswith("+")  # modifiers are joined by "+" on Windows/Linux
        keys = QHBoxLayout()
        keys.setSpacing(3)
        keys.addWidget(_make_key(modifier.rstrip("+")))
        if sep:
            keys.addWidget(QLabel("+"))
        keys.addWidget(_make_key(key))
        keys.addStretch(1)
        label = _LinkLabel(name)
        label.clicked.connect(action.trigger)
        label.setMinimumHeight(20)  # same row height as the recent files
        grid.addWidget(label, row, 0)
        grid.addLayout(keys, row, 1)
    return widget


def _clear_layout(layout):
    while (item := layout.takeAt(0)) is not None:
        # hide immediately because deferred deletion does not happen while a nested
        # event loop (such as a modal message box) is running
        if (widget := item.widget()) is not None:  # spacers have no widget
            widget.hide()
            widget.deleteLater()


class _LinkLabel(QLabel):
    """Label that behaves like a link (pointing hand, link color on hover)."""

    clicked = Signal()

    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QLabel:hover { color: palette(link); }")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _RecentRow(QWidget):
    """Row with a clickable file name and a remove button shown on hover."""

    clicked = Signal()
    removed = Signal()

    def __init__(self, fname):
        super().__init__()
        self.label = _LinkLabel(Path(fname).name)
        self.label.setToolTip(fname)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.label.clicked.connect(self.clicked.emit)
        self._icon = QIcon.fromTheme("close-data")
        self.button = QToolButton()
        self.button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.button.setFixedSize(20, 20)
        self.button.setAutoRaise(True)
        self.button.setStyleSheet(_HOVER_BTN_STYLE)
        self.button.setToolTip("Remove from Recent Files")
        self.button.clicked.connect(self.removed.emit)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.button)

    def enterEvent(self, event):
        self.button.setIcon(self._icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.button.setIcon(QIcon())
        super().leaveEvent(event)


class InfoWidget(QWidget):
    """Display basic file information in a table (two columns).

    Parameters
    ----------
    values : dict
        Each key/value pair in this dict is displayed in a row separated by a colon.
    """

    channels_clicked = Signal()
    events_clicked = Signal()
    annotations_clicked = Signal()
    montage_clicked = Signal()
    reference_clicked = Signal()

    def __init__(self, values=None):
        from mnelab import IS_DEV_VERSION

        super().__init__()
        QApplication.instance().installEventFilter(self)
        self._hover_entries = []  # list of {row_widget, btn, icon}
        self._copy_entry = None  # ref to the file name entry for restore logic
        self._check_icon = QIcon.fromTheme("copy-done")
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.setInterval(1500)
        self._restore_timer.timeout.connect(self._restore_copy_icon)
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(2, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)
        if IS_DEV_VERSION:
            vbox.addStretch()
            vbox.addWidget(QLabel(dev_label))

    def set_values(self, values=None):
        """Set values (and overwrite existing values).

        Parameters
        ----------
        values : dict
            Each key/value pair in this dict is displayed in a row separated by a colon.
        """
        self.clear()
        if values:
            for row, (key, value) in enumerate(values.items()):
                icon_name = _ICON_MAP.get(str(key), "placeholder")
                icon_label = QLabel()
                icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16, 16))
                icon_label.setFixedWidth(20)
                self.grid.addWidget(icon_label, row, 0)
                left = QLabel(str(key) + ":")
                right = QLabel(str(value))
                right.setSizePolicy(
                    QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
                )
                self.grid.addWidget(left, row, 1)
                self.grid.addWidget(right, row, 2)
                if key == "File Name" and value != "–":
                    right.setText(Path(str(value)).name)  # filename only, not full path
                    self._copy_entry = self._add_hover_entry(
                        row,
                        right,
                        "copy-path",
                        "Copy Path to Clipboard",
                        lambda checked=False, v=str(value): self._on_copy(v),
                    )
                elif key == "Channels":
                    self._add_hover_entry(
                        row,
                        right,
                        "edit",
                        "Channel Properties",
                        self.channels_clicked.emit,
                    )
                elif key == "Events":
                    self._add_hover_entry(
                        row, right, "edit", "Edit Events", self.events_clicked.emit
                    )
                elif key == "Annotations":
                    self._add_hover_entry(
                        row,
                        right,
                        "edit",
                        "Edit Annotations",
                        self.annotations_clicked.emit,
                    )
                elif key == "Montage":
                    self._add_hover_entry(
                        row, right, "edit", "Set Montage", self.montage_clicked.emit
                    )
                elif key == "Reference":
                    self._add_hover_entry(
                        row,
                        right,
                        "edit",
                        "Change Reference",
                        self.reference_clicked.emit,
                    )

    def _add_hover_entry(self, row, label_widget, icon_name, tooltip, on_click):
        """Create a hover-triggered action button and register it."""
        btn = QToolButton()
        btn.setMaximumHeight(label_widget.sizeHint().height())
        btn.setIcon(QIcon())  # hidden until hovered
        btn.setAutoRaise(True)
        btn.setStyleSheet(_HOVER_BTN_STYLE)
        btn.setToolTip(tooltip)
        btn.clicked.connect(on_click)
        entry = {
            "row_widget": label_widget,  # any widget in the row, used for Y detection
            "btn": btn,
            "icon": QIcon.fromTheme(icon_name),
        }
        self._hover_entries.append(entry)
        self.grid.addWidget(btn, row, 3)
        return entry

    def leaveEvent(self, event):
        for entry in self._hover_entries:
            if entry is not self._copy_entry or not self._restore_timer.isActive():
                entry["btn"].setIcon(QIcon())
        super().leaveEvent(event)

    def clear_hover(self):
        """Hide all hover actions, including the temporary copy confirmation."""
        self._restore_timer.stop()
        for entry in self._hover_entries:
            entry["btn"].setIcon(QIcon())

    def _update_hover_from_cursor(self):
        if QApplication.activeModalWidget() is not None:
            self.clear_hover()
            return
        cursor_local = self.mapFromGlobal(QCursor.pos())
        for entry in self._hover_entries:
            if self.rect().contains(cursor_local):
                ref = entry["row_widget"]
                top = ref.mapTo(self, QPoint(0, 0)).y()
                in_row = top <= cursor_local.y() < top + ref.height()
            else:
                in_row = False
            if not (entry is self._copy_entry and self._restore_timer.isActive()):
                entry["btn"].setIcon(entry["icon"] if in_row else QIcon())

    def _on_copy(self, path):
        QGuiApplication.clipboard().setText(path)
        if self._copy_entry:
            self._restore_timer.stop()
            self._copy_entry["btn"].setIcon(self._check_icon)
            self._restore_timer.start()

    def _restore_copy_icon(self):
        if QApplication.activeModalWidget() is not None:
            self.clear_hover()
            return
        if self._copy_entry:
            entry = self._copy_entry
            cursor_local = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(cursor_local):
                ref = entry["row_widget"]
                top = ref.mapTo(self, QPoint(0, 0)).y()
                in_row = top <= cursor_local.y() < top + ref.height()
            else:
                in_row = False
            entry["btn"].setIcon(entry["icon"] if in_row else QIcon())

    def eventFilter(self, obj, event):
        if self._hover_entries and event.type() == QEvent.Type.MouseMove:
            self._update_hover_from_cursor()
        return super().eventFilter(obj, event)

    def clear(self):
        """Clear all values."""
        self._hover_entries = []
        self._copy_entry = None
        item = self.grid.takeAt(0)
        while item:
            # hide immediately because deferred deletion does not happen while a
            # nested event loop (such as a modal message box) is running
            item.widget().hide()
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class EmptyWidget(QWidget):
    """Display keyboard shortcuts (left) and recent files (right).

    Parameters
    ----------
    actions : list of PySide6.QtGui.QAction
        Actions whose shortcuts are shown.
    recent : list of str
        Paths of recent files.
    documentation_url : str, optional
        URL of the documentation. If given, a link to it is shown below the shortcuts.
    """

    recent_clicked = Signal(str)
    recent_removed = Signal(str)
    documentation_clicked = Signal()

    def __init__(self, actions, recent=None, documentation_url=None):
        from mnelab import IS_DEV_VERSION

        super().__init__()
        self._actions = actions
        self._documentation_url = documentation_url
        self._recent = []
        self._shortcuts_widget = QWidget()
        self._shortcuts_layout = QVBoxLayout(self._shortcuts_widget)
        self._shortcuts_layout.setContentsMargins(8, 0, 8, 0)
        self._shortcuts_layout.setSpacing(2)
        self._recent_widget = QWidget()
        self._recent_layout = QVBoxLayout(self._recent_widget)
        self._recent_layout.setContentsMargins(8, 0, 8, 0)
        self._recent_layout.setSpacing(2)
        hbox = QHBoxLayout()
        hbox.addWidget(self._shortcuts_widget, 1, Qt.AlignmentFlag.AlignTop)
        hbox.addWidget(self._recent_widget, 1, Qt.AlignmentFlag.AlignTop)
        vbox = QVBoxLayout(self)
        vbox.addSpacing(SECTION_SPACING)
        vbox.addLayout(hbox)
        vbox.addStretch()
        if IS_DEV_VERSION:
            vbox.addWidget(QLabel(dev_label))
        self._set_shortcuts()
        self.set_recent(recent)

    def _set_shortcuts(self):
        _clear_layout(self._shortcuts_layout)
        self._shortcuts_layout.addWidget(_make_heading("Keyboard Shortcuts"))
        self._shortcuts_layout.addSpacing(HEADING_SPACING)
        self._shortcuts_layout.addWidget(_make_shortcuts(self._actions))
        if self._documentation_url:
            self._shortcuts_layout.addSpacing(SECTION_SPACING)
            self._shortcuts_layout.addWidget(_make_heading("Documentation"))
            self._shortcuts_layout.addSpacing(HEADING_SPACING)
            link = _LinkLabel(urlparse(self._documentation_url).netloc)
            link.setToolTip(self._documentation_url)
            link.clicked.connect(self.documentation_clicked)
            self._shortcuts_layout.addWidget(link)

    def set_recent(self, recent):
        """Set the recent files (and overwrite existing ones).

        Parameters
        ----------
        recent : list of str
            Paths of recent files.
        """
        recent = [fname for fname in recent or [] if fname is not None]
        self._recent = recent[:MAX_RECENT_LINKS]
        _clear_layout(self._recent_layout)
        self._recent_widget.setVisible(bool(self._recent))
        if not self._recent:
            return
        self._recent_layout.addWidget(_make_heading("Recent Files"))
        self._recent_layout.addSpacing(HEADING_SPACING)
        for fname in self._recent:
            row = _RecentRow(fname)
            row.clicked.connect(lambda f=fname: self.recent_clicked.emit(f))
            row.removed.connect(lambda f=fname: self.recent_removed.emit(f))
            self._recent_layout.addWidget(row)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._set_shortcuts()
            self.set_recent(self._recent)
        super().changeEvent(event)
