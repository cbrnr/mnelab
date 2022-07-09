# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


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
        html += (
            f'\n            <tr><td align="right" width="50%">{name} </td>'
        )
        if modifier[-1] == "+":
            html += f'<td><kbd>{modifier[:-1]}</kbd>+'
        else:
            html += f'<td><kbd>{modifier}</kbd> '
        html += f'<kbd>{key}</kbd></td></tr>'
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
        Each key/value pair in this dict will be displayed in a row, separated by a colon.
    """
    def __init__(self, values=None):
        super().__init__()
        vbox = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)

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

    def clear(self):
        """Clear all values."""
        item = self.grid.takeAt(0)
        while item:
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class EmptyWidget(QWidget):
    def __init__(self, actions):
        super().__init__()
        text = QLabel(_make_shortcuts_table(actions))
        vbox = QVBoxLayout(self)
        vbox.addStretch()
        vbox.addWidget(text)
        vbox.addStretch()
