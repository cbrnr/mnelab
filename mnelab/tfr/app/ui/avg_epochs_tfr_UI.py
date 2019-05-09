# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'avg_epochs_tfr.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_AvgTFRWindow(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1308, 1000)
        font = QtGui.QFont()
        font.setPointSize(10)
        Dialog.setFont(font)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.matplotlibLayout = QtWidgets.QVBoxLayout()
        self.matplotlibLayout.setObjectName("matplotlibLayout")
        self.verticalLayout_2.addLayout(self.matplotlibLayout)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(300, 20, 300, -1)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.frame = QtWidgets.QFrame(Dialog)
        self.frame.setEnabled(True)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setObjectName("frame")
        self.bottomLayout = QtWidgets.QVBoxLayout(self.frame)
        self.bottomLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.bottomLayout.setSpacing(10)
        self.bottomLayout.setObjectName("bottomLayout")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(10)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.Display = QtWidgets.QLabel(self.frame)
        self.Display.setMinimumSize(QtCore.QSize(180, 25))
        self.Display.setMaximumSize(QtCore.QSize(180, 25))
        self.Display.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.Display.setAlignment(QtCore.Qt.AlignCenter)
        self.Display.setObjectName("Display")
        self.horizontalLayout_3.addWidget(self.Display)
        self.displayBox = QtWidgets.QComboBox(self.frame)
        self.displayBox.setMinimumSize(QtCore.QSize(0, 25))
        self.displayBox.setMaximumSize(QtCore.QSize(16777215, 25))
        self.displayBox.setObjectName("displayBox")
        self.horizontalLayout_3.addWidget(self.displayBox)
        self.horizontalLayout_3.setStretch(0, 1)
        self.horizontalLayout_3.setStretch(1, 2)
        self.bottomLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(0, -1, 0, -1)
        self.horizontalLayout_2.setSpacing(10)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setMinimumSize(QtCore.QSize(180, 25))
        self.label.setMaximumSize(QtCore.QSize(180, 25))
        self.label.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(10)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.vmin = QtWidgets.QLineEdit(self.frame)
        self.vmin.setObjectName("vmin")
        self.horizontalLayout_5.addWidget(self.vmin)
        self.vmax = QtWidgets.QLineEdit(self.frame)
        self.vmax.setMinimumSize(QtCore.QSize(0, 0))
        self.vmax.setMaximumSize(QtCore.QSize(300, 16777215))
        self.vmax.setObjectName("vmax")
        self.horizontalLayout_5.addWidget(self.vmax)
        self.log = QtWidgets.QCheckBox(self.frame)
        self.log.setObjectName("log")
        self.horizontalLayout_5.addWidget(self.log)
        self.horizontalLayout_2.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_2.setStretch(0, 1)
        self.horizontalLayout_2.setStretch(1, 2)
        self.bottomLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.mainLabel = QtWidgets.QLabel(self.frame)
        self.mainLabel.setMinimumSize(QtCore.QSize(180, 25))
        self.mainLabel.setMaximumSize(QtCore.QSize(180, 25))
        self.mainLabel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.mainLabel.setText("")
        self.mainLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.mainLabel.setObjectName("mainLabel")
        self.horizontalLayout.addWidget(self.mainLabel)
        self.mainSlider = QtWidgets.QSlider(self.frame)
        self.mainSlider.setMinimumSize(QtCore.QSize(0, 25))
        self.mainSlider.setMaximumSize(QtCore.QSize(16777215, 25))
        self.mainSlider.setOrientation(QtCore.Qt.Horizontal)
        self.mainSlider.setObjectName("mainSlider")
        self.horizontalLayout.addWidget(self.mainSlider)
        self.channelName = QtWidgets.QLineEdit(self.frame)
        self.channelName.setObjectName("channelName")
        self.horizontalLayout.addWidget(self.channelName)
        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 2)
        self.bottomLayout.addLayout(self.horizontalLayout)
        self.bottomLayout.setStretch(0, 1)
        self.bottomLayout.setStretch(1, 1)
        self.bottomLayout.setStretch(2, 1)
        self.horizontalLayout_4.addWidget(self.frame)
        self.topoFrame = QtWidgets.QFrame(Dialog)
        self.topoFrame.setEnabled(True)
        self.topoFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.topoFrame.setObjectName("topoFrame")
        self.topomapFrame = QtWidgets.QVBoxLayout(self.topoFrame)
        self.topomapFrame.setContentsMargins(9, 9, 9, 9)
        self.topomapFrame.setObjectName("topomapFrame")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_2 = QtWidgets.QLabel(self.topoFrame)
        self.label_2.setMinimumSize(QtCore.QSize(180, 0))
        self.label_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_6.addWidget(self.label_2)
        self.tmin = QtWidgets.QLineEdit(self.topoFrame)
        self.tmin.setObjectName("tmin")
        self.horizontalLayout_6.addWidget(self.tmin)
        self.tmax = QtWidgets.QLineEdit(self.topoFrame)
        self.tmax.setObjectName("tmax")
        self.horizontalLayout_6.addWidget(self.tmax)
        self.topomapFrame.addLayout(self.horizontalLayout_6)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.tSlider = QtWidgets.QSlider(self.topoFrame)
        self.tSlider.setOrientation(QtCore.Qt.Horizontal)
        self.tSlider.setObjectName("tSlider")
        self.verticalLayout_4.addWidget(self.tSlider)
        self.topomapFrame.addLayout(self.verticalLayout_4)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_3 = QtWidgets.QLabel(self.topoFrame)
        self.label_3.setMinimumSize(QtCore.QSize(180, 0))
        self.label_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_7.addWidget(self.label_3)
        self.fmin = QtWidgets.QLineEdit(self.topoFrame)
        self.fmin.setObjectName("fmin")
        self.horizontalLayout_7.addWidget(self.fmin)
        self.fmax = QtWidgets.QLineEdit(self.topoFrame)
        self.fmax.setObjectName("fmax")
        self.horizontalLayout_7.addWidget(self.fmax)
        self.topomapFrame.addLayout(self.horizontalLayout_7)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.fSlider = QtWidgets.QSlider(self.topoFrame)
        self.fSlider.setOrientation(QtCore.Qt.Horizontal)
        self.fSlider.setObjectName("fSlider")
        self.verticalLayout_3.addWidget(self.fSlider)
        self.topomapFrame.addLayout(self.verticalLayout_3)
        self.horizontalLayout_4.addWidget(self.topoFrame)
        self.horizontalLayout_4.setStretch(0, 1)
        self.horizontalLayout_4.setStretch(1, 1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.verticalLayout_2.setStretch(0, 1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.Display.setText(_translate("Dialog", "Display"))
        self.label.setText(_translate("Dialog", "Scaling"))
        self.log.setText(_translate("Dialog", "log"))
        self.label_2.setText(_translate("Dialog", "Time range"))
        self.label_3.setText(_translate("Dialog", "Frequency range"))
