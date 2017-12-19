# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialogs/editselectedchannelsdialog.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(410, 421)
        self.gridLayout_3 = QtWidgets.QGridLayout(Dialog)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableWidget = QtWidgets.QTableWidget(Dialog)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        self.verticalLayout.addWidget(self.tableWidget)
        self.channelTypeGroupBox = QtWidgets.QGroupBox(Dialog)
        self.channelTypeGroupBox.setCheckable(True)
        self.channelTypeGroupBox.setChecked(False)
        self.channelTypeGroupBox.setObjectName("channelTypeGroupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.channelTypeGroupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.channelTypeGroupBox)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.channelTypeComboBox = QtWidgets.QComboBox(self.channelTypeGroupBox)
        self.channelTypeComboBox.setObjectName("channelTypeComboBox")
        self.horizontalLayout.addWidget(self.channelTypeComboBox)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.channelTypeGroupBox)
        self.badChannelGroupBox = QtWidgets.QGroupBox(Dialog)
        self.badChannelGroupBox.setCheckable(True)
        self.badChannelGroupBox.setChecked(False)
        self.badChannelGroupBox.setObjectName("badChannelGroupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.badChannelGroupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.setBadButton = QtWidgets.QRadioButton(self.badChannelGroupBox)
        self.setBadButton.setObjectName("setBadButton")
        self.gridLayout_2.addWidget(self.setBadButton, 0, 0, 1, 1)
        self.setNotBadButton = QtWidgets.QRadioButton(self.badChannelGroupBox)
        self.setNotBadButton.setObjectName("setNotBadButton")
        self.gridLayout_2.addWidget(self.setNotBadButton, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.badChannelGroupBox)
        self.gridLayout_3.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout_3.addWidget(self.buttonBox, 0, 1, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("Dialog", "Channel Name"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("Dialog", "Type"))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("Dialog", "Bad"))
        self.channelTypeGroupBox.setTitle(_translate("Dialog", "Channel Type"))
        self.label.setText(_translate("Dialog", "Change Type: "))
        self.badChannelGroupBox.setTitle(_translate("Dialog", "Bad Channels"))
        self.setBadButton.setText(_translate("Dialog", "Set as Bad"))
        self.setNotBadButton.setText(_translate("Dialog", "Unset as Bad"))

