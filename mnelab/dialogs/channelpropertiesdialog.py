from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox,
                             QAbstractItemView, QTableView, QHeaderView,
                             QStyledItemDelegate, QComboBox)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QSortFilterProxyModel

from mne.io.pick import channel_type


class ChannelPropertiesDialog(QDialog):
    def __init__(self, parent, info, title="Channel Properties"):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.model = QStandardItemModel(info["nchan"], 4)
        self.model.setHorizontalHeaderLabels(["#", "Label", "Type", "Bad"])
        for index, ch in enumerate(info["chs"]):
            item = QStandardItem()
            item.setData(index, Qt.DisplayRole)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.model.setItem(index, 0, item)
            self.model.setItem(index, 1, QStandardItem(ch["ch_name"]))
            kind = channel_type(info, index).upper()
            self.model.setItem(index, 2, QStandardItem(str(kind)))
            bad = QStandardItem()
            bad.setData(ch["ch_name"] in info["bads"], Qt.UserRole)
            bad.setCheckable(True)
            bad.setEditable(False)
            checked = ch["ch_name"] in info["bads"]
            bad.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.model.setItem(index, 3, bad)

        self.proxymodel = MySortFilterProxyModel()
        self.proxymodel.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxymodel)
        self.view.setItemDelegateForColumn(2, ComboBoxDelegate(self.view))
        self.view.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.resizeColumnsToContents()
        # for i in range(self.model.rowCount()):
        #         self.view.openPersistentEditor(self.model.index(i, 2))

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.resize(400, 650)


class MySortFilterProxyModel(QSortFilterProxyModel):
    """Add ability to filter on Qt.UserRole if Qt.DisplayRole is None.

    This is useful for the 'Bad' column, which stores its data (True/False) as
    Qt.UserRole instead of the default Qt.DisplayRole.
    """
    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)
        if left_data is None:
            left_data = self.sourceModel().data(left, Qt.UserRole)
        if right_data is None:
            right_data = self.sourceModel().data(right, Qt.UserRole)

        return left_data < right_data


class ComboBoxDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(["EEG", "EMG", "EOG", "ECG", "MEG"])
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentIndex(editor.findText(value))
        editor.showPopup()

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
