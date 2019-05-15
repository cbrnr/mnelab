# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'batch_psd.ui'
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
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.methodLabel = QtWidgets.QLabel(self.verticalWidget)
        self.methodLabel.setMinimumSize(QtCore.QSize(0, 25))
        self.methodLabel.setMaximumSize(QtCore.QSize(65641, 25))
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
        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 1)
        self.tabLayout1.addLayout(self.horizontalLayout)
        self.line = QtWidgets.QFrame(self.verticalWidget)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.tabLayout1.addWidget(self.line)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.labels = QtWidgets.QVBoxLayout()
        self.labels.setObjectName("labels")
        self.horizontalLayout_2.addLayout(self.labels)
        self.lines = QtWidgets.QVBoxLayout()
        self.lines.setObjectName("lines")
        self.horizontalLayout_2.addLayout(self.lines)
        self.horizontalLayout_2.setStretch(0, 1)
        self.horizontalLayout_2.setStretch(1, 1)
        self.tabLayout1.addLayout(self.horizontalLayout_2)
        self.verticalLayout.addWidget(self.verticalWidget)
        self.buttonBox = QtWidgets.QDialogButtonBox(TimeFreq)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(TimeFreq)
        QtCore.QMetaObject.connectSlotsByName(TimeFreq)

    def retranslateUi(self, TimeFreq):
        _translate = QtCore.QCoreApplication.translate
        TimeFreq.setWindowTitle(_translate("TimeFreq", "Dialog"))
        self.methodLabel.setText(_translate("TimeFreq", "Method"))
