# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Resources/UI/pickbadchannelsdialog.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(636, 510)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 1, 1, 2)
        self.goodListWidget = QtWidgets.QListWidget(Dialog)
        self.goodListWidget.setObjectName("goodListWidget")
        self.gridLayout.addWidget(self.goodListWidget, 1, 0, 1, 2)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.moveToBadButton = QtWidgets.QPushButton(Dialog)
        self.moveToBadButton.setText("")
        self.moveToBadButton.setObjectName("moveToBadButton")
        self.verticalLayout.addWidget(self.moveToBadButton)
        self.moveToGoodButton = QtWidgets.QPushButton(Dialog)
        self.moveToGoodButton.setText("")
        self.moveToGoodButton.setObjectName("moveToGoodButton")
        self.verticalLayout.addWidget(self.moveToGoodButton)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.gridLayout.addLayout(self.verticalLayout, 1, 2, 1, 1)
        self.badListWidget = QtWidgets.QListWidget(Dialog)
        self.badListWidget.setObjectName("badListWidget")
        self.gridLayout.addWidget(self.badListWidget, 1, 3, 1, 1)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 3, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 3, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Bad Channel Picker Dialog"))
        self.label.setText(_translate("Dialog", "Good Channels"))
        self.label_2.setText(_translate("Dialog", "Bad Channels"))

