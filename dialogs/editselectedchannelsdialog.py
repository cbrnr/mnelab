from PyQt5.QtWidgets import (QDialog, QTableWidget, QTableWidgetItem,
							 QComboBox, QStyle, QCheckBox, QRadioButton)

from .ui_editselectedchannelsdialog import Ui_Dialog

class EditSelectedChannelsDialog(QDialog):
	def __init__(self, parent, channel_names=None, channel_types=None, channel_bads=None):
		if channel_names:
			self.channel_names = channel_names
		else:
			self.channel_names = []
		self.orig_values = dict(zip(channel_names, zip(channel_types, channel_bads)))
		# Now that we've created the orig_values structure, clean any duplicates
		# out of the channel_names
		# This is the fastest way according to Raymond Hettinger in Python 3.6
		# https://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-whilst-preserving-order/39835527#39835527
		from collections import OrderedDict
		self.channel_names = list(OrderedDict.fromkeys(self.channel_names))
		super().__init__()
		self.ui = Ui_Dialog()
		self.ui.setupUi(self)

		self.CHANNEL_TYPES = ['grad', 'mag', 'eeg', 'stim', 'eog', 'emg', 'ecg', 'ref_meg', 'resp', 'exci', 'ias', 'syst', 'misc', 'seeg', 'bio', 'chpi', 'dipole', 'gof', 'ecog', 'hbo', 'hbr']
		self.NAME_INDEX, self.TYPE_INDEX, self.BAD_INDEX = 0, 1, 2

		self.ui.tableWidget.setColumnCount(3)
		self.ui.tableWidget.setRowCount(len(self.channel_names))
		for index, name in enumerate(self.channel_names):
			self.ui.tableWidget.setItem(index, self.NAME_INDEX, QTableWidgetItem(name))
			combo = QComboBox()
			for t in self.CHANNEL_TYPES:
				combo.addItem(t.upper())
			combo.setCurrentText(self.orig_values[name][0])
			self.ui.tableWidget.setCellWidget(index, self.TYPE_INDEX, combo)
			checkbox = QCheckBox()
			checkbox.setTristate(False)
			checkbox.setChecked(self.orig_values[name][1])
			self.ui.tableWidget.setCellWidget(index, self.BAD_INDEX, checkbox)

		for t in self.CHANNEL_TYPES:
			self.ui.channelTypeComboBox.addItem(t.upper())

		self.ui.channelTypeComboBox.currentTextChanged.connect(self.setAllChannelTypes)
		self.ui.channelTypeGroupBox.toggled.connect(self.channelTypeGroupBoxToggled)
		self.ui.setBadButton.toggled.connect(self.setAllChannelsBad)
		self.ui.badChannelGroupBox.toggled.connect(self.badChannelGroupBoxToggled)


	def setAllChannelTypes(self, newChannelType):
		""" If the lower combobox is used to select a channel type,
		change all channel types to this type.
		"""
		for index, name in enumerate(self.channel_names):
			self.ui.tableWidget.cellWidget(index, self.TYPE_INDEX).setCurrentText(self.ui.channelTypeComboBox.currentText())

	def channelTypeGroupBoxToggled(self, value):
		""" If the channel type groupbox becomes untoggled, set the channels
		back to their original types.
		"""
		if value:
			pass
		else:
			for index, name in enumerate(self.channel_names):
				self.ui.tableWidget.cellWidget(index, self.TYPE_INDEX).setCurrentText(self.orig_values[name][0])

	def setAllChannelsBad(self, value):
		""" Sends True when 'Set as Bad' is checked, and False when
		'Unset as bad' is checked.
		When True, check the 'Bad' box on all channels in this dialog.
		"""
		for index, name in enumerate(self.channel_names):
			self.ui.tableWidget.cellWidget(index, self.BAD_INDEX).setChecked(value)

	def badChannelGroupBoxToggled(self, value):
		""" If the bad channel groupbox becomes untoggled, set the channels
		back to their original 'bad' settings.
		"""
		if value:
			pass
		else:
			for index, name in enumerate(self.channel_names):
				self.ui.tableWidget.cellWidget(index, self.BAD_INDEX).setChecked(self.orig_values[name][1])