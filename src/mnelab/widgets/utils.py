# © MNELAB developers
#
# License: BSD (3-clause)

import sys

selection_key = "Command" if sys.platform == "darwin" else "Ctrl"


def set_tooltip(tooltip, *widgets):
    """Set the same tooltip on related widgets."""
    for widget in widgets:
        widget.setToolTip(tooltip)
