# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'batch_tfr.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TimeFreq(object):
    def setupUi(self, TimeFreq):
        TimeFreq.setObjectName("TimeFreq")
        TimeFreq.resize(360, 204)
        self.verticalLayout = QtWidgets.QVBoxLayout(TimeFreq)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(10)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.methodLabel_3 = QtWidgets.QLabel(TimeFreq)
        self.methodLabel_3.setMinimumSize(QtCore.QSize(100, 25))
        self.methodLabel_3.setMaximumSize(QtCore.QSize(68468, 25))
        font = QtGui.QFont()
        font.setItalic(True)
        self.methodLabel_3.setFont(font)
        self.methodLabel_3.setAlignment(QtCore.Qt.AlignCenter)
        self.methodLabel_3.setObjectName("methodLabel_3")
        self.horizontalLayout_3.addWidget(self.methodLabel_3)
        self.tfrMethodBox = QtWidgets.QComboBox(TimeFreq)
        self.tfrMethodBox.setMinimumSize(QtCore.QSize(100, 25))
        self.tfrMethodBox.setMaximumSize(QtCore.QSize(16777215, 25))
        self.tfrMethodBox.setAccessibleName("")
        self.tfrMethodBox.setCurrentText("")
        self.tfrMethodBox.setObjectName("tfrMethodBox")
        self.horizontalLayout_3.addWidget(self.tfrMethodBox)
        self.horizontalLayout_3.setStretch(0, 1)
        self.horizontalLayout_3.setStretch(1, 1)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.line = QtWidgets.QFrame(TimeFreq)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.labels = QtWidgets.QVBoxLayout()
        self.labels.setObjectName("labels")
        self.horizontalLayout.addLayout(self.labels)
        self.lines = QtWidgets.QVBoxLayout()
        self.lines.setObjectName("lines")
        self.horizontalLayout.addLayout(self.lines)
        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(TimeFreq)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(TimeFreq)
        QtCore.QMetaObject.connectSlotsByName(TimeFreq)

    def retranslateUi(self, TimeFreq):
        _translate = QtCore.QCoreApplication.translate
        TimeFreq.setWindowTitle(_translate("TimeFreq", "Dialog"))
        self.methodLabel_3.setText(_translate("TimeFreq", "Method"))
