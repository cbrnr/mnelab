# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'psd_mnelab.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_PSD(object):
    def setupUi(self, TimeFreq):
        TimeFreq.setObjectName("TimeFreq")
        TimeFreq.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(TimeFreq)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalWidget = QtWidgets.QWidget(TimeFreq)
        self.verticalWidget.setObjectName("verticalWidget")
        self.tabLayout1 = QtWidgets.QVBoxLayout(self.verticalWidget)
        self.tabLayout1.setContentsMargins(0, 0, 0, 0)
        self.tabLayout1.setSpacing(6)
        self.tabLayout1.setObjectName("tabLayout1")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.methodLabel = QtWidgets.QLabel(self.verticalWidget)
        self.methodLabel.setMinimumSize(QtCore.QSize(100, 25))
        self.methodLabel.setMaximumSize(QtCore.QSize(100, 25))
        font = QtGui.QFont()
        font.setItalic(True)
        self.methodLabel.setFont(font)
        self.methodLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.methodLabel.setObjectName("methodLabel")
        self.horizontalLayout.addWidget(self.methodLabel)
        self.psdMethod = QtWidgets.QComboBox(self.verticalWidget)
        self.psdMethod.setMinimumSize(QtCore.QSize(50, 25))
        self.psdMethod.setMaximumSize(QtCore.QSize(16777215, 25))
        self.psdMethod.setAccessibleName("")
        self.psdMethod.setCurrentText("")
        self.psdMethod.setFrame(False)
        self.psdMethod.setObjectName("psdMethod")
        self.horizontalLayout.addWidget(self.psdMethod)
        self.horizontalLayout.setStretch(0, 3)
        self.horizontalLayout.setStretch(1, 1)
        self.tabLayout1.addLayout(self.horizontalLayout)
        self.paramLayout = QtWidgets.QVBoxLayout()
        self.paramLayout.setObjectName("paramLayout")
        self.tabLayout1.addLayout(self.paramLayout)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(4)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.psdButton = QtWidgets.QPushButton(self.verticalWidget)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.psdButton.setFont(font)
        self.psdButton.setCheckable(False)
        self.psdButton.setObjectName("psdButton")
        self.horizontalLayout_5.addWidget(self.psdButton)
        self.savePsdButton = QtWidgets.QPushButton(self.verticalWidget)
        self.savePsdButton.setObjectName("savePsdButton")
        self.horizontalLayout_5.addWidget(self.savePsdButton)
        self.tabLayout1.addLayout(self.horizontalLayout_5)
        self.verticalLayout.addWidget(self.verticalWidget)

        self.retranslateUi(TimeFreq)
        QtCore.QMetaObject.connectSlotsByName(TimeFreq)

    def retranslateUi(self, TimeFreq):
        _translate = QtCore.QCoreApplication.translate
        TimeFreq.setWindowTitle(_translate("TimeFreq", "Dialog"))
        self.methodLabel.setText(_translate("TimeFreq", "Method"))
        self.psdButton.setText(_translate("TimeFreq", "Open Interactive PSD"))
        self.savePsdButton.setText(_translate("TimeFreq", "Save PSD"))
