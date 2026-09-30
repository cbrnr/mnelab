# © MNELAB developers
#
# License: BSD (3-clause)

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

import mnelab.widgets.infowidget as infowidget_module
from mnelab.mainwindow import MainWindow
from mnelab.model import Model


def test_modal_dialog_hides_main_window_hover_controls(qtbot, monkeypatch):
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    view.show()
    view.infowidget.setCurrentIndex(0)

    info = view.infowidget.widget(0)
    info.set_values({"Channels": "4"})
    QApplication.processEvents()
    entry = info._hover_entries[0]
    assert entry["row_widget"].isVisible()
    cursor_pos = entry["row_widget"].mapToGlobal(entry["row_widget"].rect().center())
    monkeypatch.setattr(
        infowidget_module, "QCursor", SimpleNamespace(pos=lambda: cursor_pos)
    )
    info._update_hover_from_cursor()
    assert not entry["btn"].icon().isNull()

    item = view.sidebar.make_item("data", "data-id")
    view.sidebar.addTopLevelItem(item)
    view.sidebar_container.show()
    view.sidebar.showCloseButton(item)
    view.sidebar_container._collapse_btn.show()
    assert view.sidebar.itemWidget(item, 2) is not None
    assert not view.sidebar_container._collapse_btn.isHidden()

    dialog = QDialog(view)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(lambda: QApplication.activeModalWidget() is dialog)

    qtbot.waitUntil(lambda: entry["btn"].icon().isNull())
    assert view.sidebar.itemWidget(item, 2) is None
    assert view.sidebar_container._collapse_btn.isHidden()

    info._update_hover_from_cursor()
    view.sidebar.showCloseButton(item)
    assert entry["btn"].icon().isNull()
    assert view.sidebar.itemWidget(item, 2) is None

    dialog.close()
    qtbot.waitUntil(lambda: QApplication.activeModalWidget() is None)
    info._update_hover_from_cursor()
    view.sidebar.showCloseButton(item)
    assert not entry["btn"].icon().isNull()
    assert view.sidebar.itemWidget(item, 2) is not None
