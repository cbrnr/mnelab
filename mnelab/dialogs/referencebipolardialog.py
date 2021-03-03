
# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QDialog, QVBoxLayout, QListWidget,
                            QDialogButtonBox, QPushButton, QLabel,
                            QGridLayout, QGroupBox, QFileDialog)
from qtpy.QtCore import Slot
import json


class ReferenceBipolarDialog(QDialog):
    def __init__(self, parent, channels, selected=None, title="Pick channels"):
        super().__init__(parent)
        self.setWindowTitle(title)
        if(selected is None):
            selected = []
        self.initial_selection = selected
        vbox = QVBoxLayout(self)
        vbox2 = QVBoxLayout(self)
        gbox = QGroupBox()
        grid = QGridLayout()

        grid.addWidget(QLabel("Channels (select by pair)"), 0, 0)
        self.channels = QListWidget()
        self.channels.insertItems(0, channels)
        self.channels.setSelectionMode(QListWidget.ExtendedSelection)
        grid.addWidget(self.channels, 1, 0)

        grid.addWidget(QLabel("Bipolar channels: "), 0, 2)
        self.selected = QListWidget()
        if(len(selected)):
            self.selected.insertItem(0, str(selected))
        grid.addWidget(self.selected, 1, 2)

        self.pushbutton_add = QPushButton("Add")
        vbox2.addWidget(self.pushbutton_add)
        self.pushbutton_add.pressed.connect(self.add_buttons)
        self.pushbutton_add.pressed.connect(self.toggle_buttons)

        self.pushbutton_rm = QPushButton("Remove")
        vbox2.addWidget(self.pushbutton_rm)
        self.pushbutton_rm.pressed.connect(self.rm_buttons)
        self.pushbutton_rm.pressed.connect(self.toggle_buttons)

        self.pushbutton_open = QPushButton("Open")
        vbox2.addWidget(self.pushbutton_open)
        self.pushbutton_open.pressed.connect(self.open_buttons)
        self.pushbutton_open.pressed.connect(self.toggle_buttons)

        self.pushbutton_save = QPushButton("Save")
        vbox2.addWidget(self.pushbutton_save)
        self.pushbutton_save.pressed.connect(self.save_buttons)
        self.pushbutton_save.pressed.connect(self.toggle_buttons)

        vbox2.addStretch(1)
        gbox.setLayout(vbox2)
        grid.addWidget(gbox, 1, 1)
        vbox.addLayout(grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.selected.itemSelectionChanged.connect(self.toggle_buttons)
        self.toggle_buttons()  # initialize OK button state

    @Slot()
    def toggle_buttons(self):
        """slot TOGGLE buttons.
        """
        if(self.selected.count()):
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
            self.pushbutton_save.setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.pushbutton_save.setEnabled(False)

    @Slot()
    def add_buttons(self):
        """slot ADD button.
        """
        if(len(self.channels.selectedItems()) == 2):
            pair = [item.data(0) for item in self.channels.selectedItems()]
            self.selected.insertItem(0, str(pair))

    @Slot()
    def rm_buttons(self):
        """slot RM button.
        """
        selected = self.selected.selectedItems()
        if(not selected):
            return
        for item in selected:
            self.selected.takeItem(self.selected.row(item))

    @Slot()
    def open_buttons(self):
        """open saved bipolar channels
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        if dialog.exec_():
            fnames = dialog.selectedFiles()
            fname = fnames.pop(0)
            with open(fname) as file:
                bichan = json.loads(file.read())
                for i in bichan:
                    self.selected.insertItem(0, str(i))

    @Slot()
    def save_buttons(self):
        """saved bipolar channels
        """
        dialog = QFileDialog()
        fd = dialog.getSaveFileName()
        fname = fd[0]
        print("Saving bipolar reference profile: ", fname)
        with open(fname, 'w') as file:
            sel = [self.selected.item(i).text()
                   for i in range(self.selected.count())]
            sell = [[i.strip("'").strip('"')
                     for i in j[1:-1].split(", ")] for j in sel]
            file.write(json.dumps(sell))
            print("Profile saved!")
