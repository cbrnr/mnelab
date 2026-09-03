# © MNELAB developers
#
# License: BSD (3-clause)


def set_tooltip(tooltip, *widgets):
    """Set the same tooltip on related widgets."""
    for widget in widgets:
        widget.setToolTip(tooltip)
