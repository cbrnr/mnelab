from PyQt5.QtWidgets import (QDialog, QTableWidget, QTableWidgetItem,
                            QComboBox, QStyle, QCheckBox)
from mne.channels.channels import channel_type
from .editselectedchannelsdialog import EditSelectedChannelsDialog

from .ui_channeldialog import Ui_Dialog

class ChannelDialog(QDialog):
    def __init__(self, parent, raw=None):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.raw = raw

        self.CHANNEL_TYPES = ['grad', 'mag', 'eeg', 'stim', 'eog', 'emg', 'ecg', 'ref_meg', 'resp', 'exci', 'ias', 'syst', 'misc', 'seeg', 'bio', 'chpi', 'dipole', 'gof', 'ecog', 'hbo', 'hbr']
        self.NAME_INDEX, self.TYPE_INDEX, self.BAD_INDEX = 0, 1, 2

        # connect buttons
        self.ui.editSelectedButton.clicked.connect(self.edit_selected_channels_dialog)

        self.ui.tableWidget.setColumnCount(3)
        self.ui.tableWidget.setRowCount(len(self.raw.ch_names))
        for index, channel in enumerate(self.raw.info['chs']):
            self.ui.tableWidget.setItem(index, self.NAME_INDEX, QTableWidgetItem(channel['ch_name']))
            combo = QComboBox()
            for t in self.CHANNEL_TYPES:
                combo.addItem(t.upper())
            combo.setCurrentText(channel_type(self.raw.info, index).upper())
            self.ui.tableWidget.setCellWidget(index, self.TYPE_INDEX, combo)
            checkbox = QCheckBox()
            checkbox.setTristate(False)
            if channel['ch_name'] in self.raw.info['bads']:
                checkbox.setChecked(True)
            self.ui.tableWidget.setCellWidget(index, self.BAD_INDEX, checkbox)

    def edit_selected_channels_dialog(self):
        selectedList = self.ui.tableWidget.selectedIndexes()
        rows = [item.row() for item in selectedList]
        channel_names = [self.ui.tableWidget.item(row, self.NAME_INDEX).text() for row in rows]
        channel_types = [self.ui.tableWidget.cellWidget(row, self.TYPE_INDEX).currentText() for row in rows]
        channel_bads = [self.ui.tableWidget.cellWidget(row, self.BAD_INDEX).checkState() for row in rows]
        dialog = EditSelectedChannelsDialog(self, channel_names=channel_names, channel_types=channel_types, channel_bads=channel_bads)
        if dialog.exec_():
            # TODO: Change the parent dialog here
            print("test")

