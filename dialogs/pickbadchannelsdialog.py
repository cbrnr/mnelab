from PyQt5.QtWidgets import QDialog, QListWidget, QStyle

from .ui_pickbadchannelsdialog import Ui_Dialog


class PickBadChannelsDialog(QDialog):
    def __init__(self, parent, channels, bads=None):
        super().__init__()
        self.channels = channels
        if not bads:
            self.bads = []
        else:
            self.bads = bads
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # populate lists
        self.ui.goodListWidget.setSelectionMode(QListWidget.ExtendedSelection)
        self.ui.badListWidget.setSelectionMode(QListWidget.ExtendedSelection)
        self.ui.goodListWidget.insertItems(0, [chan for chan in channels if chan not in bads])
        self.ui.badListWidget.insertItems(0, bads)

        # icons
        self.ui.moveToBadButton.setIcon(
            self.style().standardIcon(QStyle.SP_ArrowRight))
        self.ui.moveToGoodButton.setIcon(
            self.style().standardIcon(QStyle.SP_ArrowLeft))

        # connect buttons
        self.ui.moveToBadButton.clicked.connect(self.moveToBads)
        self.ui.moveToGoodButton.clicked.connect(self.moveToGoods)

    def moveToBads(self):
        indexes = self.ui.goodListWidget.selectedIndexes()
        # record which rows are selected in reverse order, so popping them
        # doesn't shift the indices downstream
        rows = sorted((index.row() for index in indexes), reverse=True)
        # pop the item in each of those rows
        items_to_move = [self.ui.goodListWidget.takeItem(row) for row in rows]
        # add the items back in re-reversed order so they show up in the order
        # they appeared originally
        self.ui.badListWidget.addItems(
            reversed([item.text() for item in items_to_move]))

    def moveToGoods(self):
        indexes = self.ui.badListWidget.selectedIndexes()
        rows = sorted((index.row() for index in indexes), reverse=True)
        items_to_move = [self.ui.badListWidget.takeItem(row) for row in rows]
        self.ui.goodListWidget.addItems(
            reversed([item.text() for item in items_to_move]))
