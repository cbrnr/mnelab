from PyQt5.QtWidgets import (QDialog, QTableWidget, QTableWidgetItem,
                            QComboBox, QStyle, QCheckBox, QAbstractItemView)
from collections import OrderedDict
from mne.channels.channels import channel_type

from .ui_channeldialog import Ui_Dialog

class ChannelDialog(QDialog):
    def __init__(self, parent, raw=None):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.raw = raw

        self.CHANNEL_TYPES = ['grad', 'mag', 'eeg', 'stim', 'eog', 'emg', 'ecg', 'ref_meg', 'resp', 'exci', 'ias', 'syst', 'misc', 'seeg', 'bio', 'chpi', 'dipole', 'gof', 'ecog', 'hbo', 'hbr']
        self.NAME_INDEX, self.TYPE_INDEX, self.BAD_INDEX = 0, 1, 2

        self.ui.tableWidget.setColumnCount(3)
        self.ui.tableWidget.setRowCount(len(self.raw.ch_names))
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.ui.tableWidget.cellChanged.connect(self.typeItemChanged)
        # What we're going to do is make two dicts
        # (1) {              widget -> channel name of that row}
        # (2) { channel name string -> QTableWidgetItem object holding that 
        #                              string in the zeroth column}
        # This is necessary because (1) there is no way to get the location of
        # any given widget, but (2) there IS a way to get the location of a 
        # QTableWidgetItem.  So if we want the location of a widget, we need to
        # look up the channel name of that row, and then use that channel name 
        # to look up the QTableWidgetItem holding that string, and finally look
        # up the row of that QTWI.
        self.widget_to_channel_name = dict()
        self.channel_name_to_qtwi = dict()
        for index, channel in enumerate(self.raw.info['chs']):
            qtwi = QTableWidgetItem(channel['ch_name'])
            self.ui.tableWidget.setItem(index, self.NAME_INDEX, qtwi)
            self.channel_name_to_qtwi[channel['ch_name']] = qtwi
            combo = QComboBox()
            combo.setStyleSheet("""
                /* remove borders and padding */
                QComboBox {
                    border: 0px;
                    padding: 0px;
                }

                /* remove dropdown arrow */
                QComboBox::drop-down {
                    width: 0px;
                    border-width: 0px;
                }
                """
               )
            for t in self.CHANNEL_TYPES:
                combo.addItem(t.upper())
            combo.setCurrentText(channel_type(self.raw.info, index).upper())
            self.widget_to_channel_name[combo] = channel['ch_name']
            combo.currentTextChanged.connect(self.channelTypeChanged)
            self.ui.tableWidget.setCellWidget(index, self.TYPE_INDEX, combo)
            checkbox = QCheckBox()
            checkbox.setTristate(False)
            if channel['ch_name'] in self.raw.info['bads']:
                checkbox.setChecked(True)
            self.widget_to_channel_name[checkbox] = channel['ch_name']
            self.ui.tableWidget.setCellWidget(index, self.BAD_INDEX, checkbox)
            checkbox.toggled.connect(self.badCheckboxToggled)


    def badCheckboxToggled(self, value):
        """
        If a channel is set to bad, check to see if this channel is one of the
        highlighted channels.  If it is, change the other highlighted channels to 
        the same selection.  If not, do nothing.
        """
        rows = self.selectedRows()
        selected_channel_names = [self.ui.tableWidget.item(row, self.NAME_INDEX).text() for row in rows]
        channel_changed = self.widget_to_channel_name[self.sender()]
        if channel_changed in selected_channel_names:
            for row in rows:
                self.ui.tableWidget.cellWidget(row, self.BAD_INDEX).setChecked(value)
            else:
                pass

    
    def channelTypeChanged(self, value):
        """
        If a channel type is changed, check to see if this channel is one of the
        highlighted channels.  If it is, change the other highlighted channels to 
        the same selection. If not, do nothing.
        """
        selectedList = self.ui.tableWidget.selectedIndexes()
        rows = [item.row() for item in selectedList]
        # clean duplicates out of rows list
        rows = list(OrderedDict.fromkeys(rows))
        selected_channel_names = [self.ui.tableWidget.item(row, self.NAME_INDEX).text() for row in rows]
        channel_changed = self.widget_to_channel_name[self.sender()]
        if channel_changed in selected_channel_names:
            for row in rows:
                self.ui.tableWidget.cellWidget(row, self.TYPE_INDEX).setCurrentText(value)
        else:
            pass

    def selectedRows(self):
        """
        Return a de-duplicated list of currently selected rows.
        """
        selectedList = self.ui.tableWidget.selectedIndexes()
        rows = [item.row() for item in selectedList]
        # clean duplicates out of rows list
        return list(OrderedDict.fromkeys(rows))

    def getRowFromChannelName(self, ch_name):
        """
        Function to return the current row of a channel in the tableWidget.
        This is necessary because the row will change depending on how the user sorts the rows.
        """
        return self.ui.tableWidget.row(self.channel_name_to_qtwi[ch_name])