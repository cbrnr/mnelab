# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QLabel

from mnelab.widgets.infowidget import EmptyWidget, InfoWidget, _LinkLabel, _RecentRow


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


def test_empty_widget_recent_files(qtbot):
    """Test that recent files can be opened and removed from the empty widget."""
    widget = EmptyWidget([], ["/path/to/a.fif", "/path/to/b.xdf"])
    qtbot.addWidget(widget)
    rows = widget.findChildren(_RecentRow)
    assert [row.label.text() for row in rows] == ["a.fif", "b.xdf"]
    with qtbot.waitSignal(widget.recent_clicked) as blocker:
        rows[1].clicked.emit()
    assert blocker.args == ["/path/to/b.xdf"]
    with qtbot.waitSignal(widget.recent_removed) as blocker:
        rows[0].button.click()
    assert blocker.args == ["/path/to/a.fif"]

    widget.set_recent([])
    assert widget._recent_widget.isHidden()
    assert all(row.isHidden() for row in rows)


def test_empty_widget_shortcut_links(qtbot):
    """Test that clicking a shortcut name triggers its action."""
    action = QAction("Open File...")
    action.setShortcut(QKeySequence("Ctrl+O"))
    widget = EmptyWidget([action])
    qtbot.addWidget(widget)
    labels = {label.text(): label for label in widget.findChildren(_LinkLabel)}
    with qtbot.waitSignal(action.triggered):
        labels["Open File"].clicked.emit()


def test_empty_widget_documentation_link(qtbot):
    """Test that the documentation link shows its URL and emits a signal."""
    url = "https://mnelab.readthedocs.io/en/stable/"
    widget = EmptyWidget([], documentation_url=url)
    qtbot.addWidget(widget)
    labels = {label.text(): label for label in widget.findChildren(_LinkLabel)}
    link = labels["mnelab.readthedocs.io"]
    assert link.toolTip() == url
    with qtbot.waitSignal(widget.documentation_clicked):
        link.clicked.emit()
