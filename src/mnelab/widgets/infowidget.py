# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

dev_label = (
    '<p align="right"><font color="red"><small>Development Version</small></font></p>'
)


def _make_shortcuts_table(actions):
    text_color = "#777"
    html = f"""<!DOCTYPE html>
    <html>
      <head>
        <style>
          html {{ font-size: 16px; }}
          kbd {{
            font-weight: 600;
            color: {text_color};
          }}
          table {{ color: {text_color}; }}
        </style>
      </head>
      <body>
        <table>
          <tbody>"""
    for action in actions:
        name = action.text().replace("&", "").replace(".", "")
        shortcut = action.shortcut().toString(format=QKeySequence.NativeText)
        modifier, key = shortcut[:-1].strip(), shortcut[-1]
        html += f'\n            <tr><td align="right" width="50%">{name} </td>'
        if modifier[-1] == "+":
            html += f"<td><kbd>{modifier[:-1]}</kbd>+"
        else:
            html += f"<td><kbd>{modifier}</kbd> "
        html += f"<kbd>{key}</kbd></td></tr>"
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

    def __init__(self, values=None):
        from .. import __version__

        super().__init__()
        self._copy_btn = None
        self._hovered = False
        self._copy_icon = QIcon.fromTheme("copy-path")
        self._check_icon = QIcon.fromTheme("copy-done")
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(50)
        self._hide_timer.timeout.connect(self._hide_copy_btn)
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.setInterval(1500)
        self._restore_timer.timeout.connect(self._restore_copy_icon)
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)
        if __version__.split(".")[-1].startswith("dev"):
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
                left = QLabel(str(key) + ":")
                right = QLabel(str(value))
                right.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
                self.grid.addWidget(left, row, 0)
                self.grid.addWidget(right, row, 1)
                if key == "File name" and value != "-":
                    right.setText(Path(str(value)).name)
                    btn = QToolButton()
                    btn.setMaximumHeight(left.sizeHint().height())
                    btn.setIcon(QIcon())  # empty until hovered
                    btn.setAutoRaise(True)
                    btn.setStyleSheet("""
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
                    btn.setToolTip("Copy path to clipboard")
                    btn.clicked.connect(
                        lambda checked=False, v=str(value): self._on_copy(v)
                    )
                    right.installEventFilter(self)
                    btn.installEventFilter(self)
                    self._copy_btn = btn
                    self.grid.addWidget(btn, row, 2)

    def _on_copy(self, path):
        QGuiApplication.clipboard().setText(path)
        if self._copy_btn:
            self._restore_timer.stop()
            self._copy_btn.setIcon(self._check_icon)
            self._restore_timer.start()

    def _restore_copy_icon(self):
        if self._copy_btn:
            self._copy_btn.setIcon(self._copy_icon if self._hovered else QIcon())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self._hovered = True
            self._hide_timer.stop()
            if self._copy_btn and not self._restore_timer.isActive():
                self._copy_btn.setIcon(self._copy_icon)
        elif event.type() == QEvent.Leave:
            self._hovered = False
            self._hide_timer.start()
        return super().eventFilter(obj, event)

    def _hide_copy_btn(self):
        if self._copy_btn and not self._restore_timer.isActive():
            self._copy_btn.setIcon(QIcon())

    def clear(self):
        """Clear all values."""
        self._copy_btn = None
        item = self.grid.takeAt(0)
        while item:
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class EmptyWidget(QWidget):
    def __init__(self, actions):
        from .. import __version__

        super().__init__()
        text = QLabel(_make_shortcuts_table(actions))
        vbox = QVBoxLayout(self)
        vbox.addStretch()
        vbox.addWidget(text)
        vbox.addStretch()
        if __version__.split(".")[-1].startswith("dev"):
            vbox.addWidget(QLabel(dev_label))
