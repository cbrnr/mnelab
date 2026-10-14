# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import QApplication, QLabel

from mnelab.widgets.infowidget import InfoWidget


def test_set_values_hides_old_widgets(qtbot):
    """Test that replaced values are hidden before they are deleted.

    Deferred deletion does not happen while a nested event loop (such as a modal
    message box) is running, so old values would otherwise overlap the new ones.
    """
    widget = InfoWidget()
    qtbot.addWidget(widget)
    widget.show()
    values = {"File Name": "/path/to/data.xdf", "Channels": "4", "Events": "–"}
    for _ in range(3):
        widget.set_values(values)
        QApplication.processEvents()  # does not process deferred deletions

    visible = [
        label.text()
        for label in widget.findChildren(QLabel)
        if label.isVisible() and label.text()
    ]
    assert visible.count("Channels:") == 1
    assert visible.count("data.xdf") == 1
