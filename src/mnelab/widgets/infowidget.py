# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
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

dev_label = (
    '<p align="right"><font color="red"><small>Development Version</small></font></p>'
)


def _make_shortcuts_table(actions):
    dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    text_color = "#999" if dark else "#777"
    kbd_bg = "#3a3a3a" if dark else "#e2e2e2"
    font_family = monospace_font().family()
    kbd_font = f'"{font_family}", ' if font_family != "monospace" else ""
    html = f"""<!DOCTYPE html>
    <html>
      <head>
        <style>
          html {{ font-size: 16px; }}
          body {{ margin-left: 8px; margin-right: 8px; }}
          span {{
            font-family: {kbd_font}monospace;
            font-size: 0.8em;
            font-weight: 600;
            color: {text_color};
            background-color: {kbd_bg};
          }}
          table {{ color: {text_color}; }}
        </style>
      </head>
      <body>
        <table>
          <tbody>"""
    for action in actions:
        name = action.text().replace("&", "").replace(".", "")
        shortcut = action.shortcut().toString(
            format=QKeySequence.SequenceFormat.NativeText
        )
        modifier, key = shortcut[:-1].strip(), shortcut[-1]
        html += f'\n            <tr><td align="right" width="50%">{name} </td>'
        if modifier[-1] == "+":
            html += f"<td><span>&nbsp;{modifier[:-1]}&nbsp;</span>+"
        else:
            html += f"<td><span>&nbsp;{modifier}&nbsp;</span> "
        html += f"<span>&nbsp;{key}&nbsp;</span></td></tr>"
    html += """\n          </tbody>
        </table>
      </body>
    </html>"""
    return html


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

    def _update_hover_from_cursor(self):
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
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class EmptyWidget(QWidget):
    def __init__(self, actions):
        from mnelab import IS_DEV_VERSION

        super().__init__()
        self._actions = actions
        self._label = QLabel(_make_shortcuts_table(actions))
        vbox = QVBoxLayout(self)
        vbox.addStretch()
        vbox.addWidget(self._label)
        vbox.addStretch()
        if IS_DEV_VERSION:
            vbox.addWidget(QLabel(dev_label))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._label.setText(_make_shortcuts_table(self._actions))
        super().changeEvent(event)
