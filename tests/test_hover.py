# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog

from mnelab.mainwindow import MainWindow
from mnelab.model import Model


def test_modal_dialog_hides_main_window_hover_controls(qtbot):
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    view.show()

    info = view.infowidget.widget(0)
    info.set_values({"Channels": "4"})
    entry = info._hover_entries[0]
    QCursor.setPos(entry["row_widget"].mapToGlobal(entry["row_widget"].rect().center()))
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
    dialog.move(QCursor.pos())
    qtbot.addWidget(dialog)
    dialog.show()
    QApplication.processEvents()

    assert QApplication.activeModalWidget() is dialog
    assert entry["btn"].icon().isNull()
    assert view.sidebar.itemWidget(item, 2) is None
    assert view.sidebar_container._collapse_btn.isHidden()

    mouse_move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(0, 0),
        QPointF(QCursor.pos()),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(dialog, mouse_move)
    view.sidebar.showCloseButton(item)
    assert entry["btn"].icon().isNull()
    assert view.sidebar.itemWidget(item, 2) is None

    dialog.close()
    info._update_hover_from_cursor()
    view.sidebar.showCloseButton(item)
    assert not entry["btn"].icon().isNull()
    assert view.sidebar.itemWidget(item, 2) is not None
