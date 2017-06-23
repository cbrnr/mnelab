import sys
from collections import Counter
from os.path import getsize, split, splitext
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout, QLabel,
                             QVBoxLayout, QFileDialog, QWidget, QSplitter,
                             QListWidget, QListWidgetItem, QMessageBox, QListView)
from PyQt5.QtCore import QStringListModel

import mne
from mne.io.pick import channel_type


class InfoWidget(QWidget):
    def __init__(self, info={}, title=""):
        super().__init__()

        self.title = QLabel()
        self.set_title(title)

        self.vbox = QVBoxLayout(self)
        self.vbox.addWidget(self.title)
        self.vbox.addSpacing(10)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        self.vbox.addLayout(self.grid)
        self.vbox.addStretch(1)

        self.set_values(info)

    def set_title(self, title=""):
        self.title.setText("<b>{}</b>".format(title))

    def set_values(self, info={}):
        self.clear()

        # add new items to the grid
        for row, (k, v) in enumerate(info.items()):
            col0 = QLabel(str(k) + ":")
            col1 = QLabel(str(v))
            col1.setSizePolicy(1, 0)
            self.grid.addWidget(col0, row, 0)
            self.grid.addWidget(col1, row, 1)

    def clear(self):
        # delete all items in the grid
        item = self.grid.takeAt(0)
        while item:
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class FileListView(QListView):
    pass

class FileListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(0)
        self.setFrameStyle(0)

    def removeItem(self, index):
        item = self.takeItem(index)
        del item  # TODO: does this completely free memory?


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.data = []  # list of currently open data sets
        self.current = None  # currently active data set

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("MNELAB")

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self.open_file_action = file_menu.addAction("&Open file...",
                                                    self.open_file, "Ctrl+O")
        self.close_file_action = file_menu.addAction("&Close", self.close_file)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")

        plot_menu = menubar.addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...")
        self.run_ica_action = tools_menu.addAction("Run &ICA...")
        self.import_ica_action = tools_menu.addAction("Import ICA &solution...", self.import_ica)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        help_menu.addAction("About &Qt", self.show_about_qt)

        main = QSplitter()
        self.list_widget = FileListWidget()
        self.list_widget.currentRowChanged.connect(self.activate_data)
        main.addWidget(self.list_widget)
        self.info_widget = InfoWidget()
        main.addWidget(self.info_widget)
        splitter_width = main.size().width()
        main.setSizes((splitter_width / 4, 3 * splitter_width / 4))
        self.setCentralWidget(main)

        self._activate_actions(False)
        self.show()

    def open_file(self):
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter="*.bdf *.edf")
        if fname[0]:
            if self.current is None:  # no data set currently open
                self.current = 0
            else:
                self.current += 1

            self.data.append({})

            self.data[self.current]["fname"] = fname[0]
            name, _ = splitext(split(self.data[self.current]["fname"])[-1])
            self.data[self.current]["name"] = name

            raw = mne.io.read_raw_edf(self.data[self.current]["fname"],
                                      stim_channel=None, preload=True)

            self.data[self.current]["events"] = None # mne.find_events(raw)
            self.data[self.current]["raw"] = raw

            self.info_widget.set_values(self.get_info())

            self.list_widget.addItem(QListWidgetItem(name))
            self.list_widget.setCurrentRow(self.current)
            self.info_widget.set_title(name)
            self._activate_actions()

    def close_file(self):
        if len(self.data) == 1:  # only one entry in list
            self.list_widget.removeItem(self.current)
            self.data.pop(self.current)
            self.current = None
            self._activate_actions(False)
            self.info_widget.set_title("")
            self.info_widget.clear()
        else:  # at least two entries in list
            self.list_widget.removeItem(self.current)
            self.data.pop(self.current)
            #self.current -= 1
            self.activate_data(self.current)

    def get_info(self):
        raw = self.data[self.current]["raw"]
        fname = self.data[self.current]["fname"]

        nchan = raw.info["nchan"]
        chans = Counter([channel_type(raw.info, i) for i in range(nchan)])

        return {"File name": fname,
                "Number of channels": raw.info["nchan"],
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans.items()]),
                "Samples": raw.n_times,
                "Sampling frequency": str(raw.info["sfreq"]) + " Hz",
                "Length": str(raw.n_times / raw.info["sfreq"]) + " s",
                "Size in memory": "{:.2f} MB".format(
                    raw._data.nbytes / 1024 ** 2),
                "Size on disk": "{:.2f} MB".format(
                    getsize(fname) / 1024 ** 2)}

    def activate_data(self, index):
        self.current = index
        self.info_widget.set_values(self.get_info())
        self.info_widget.set_title(self.data[self.current]["name"])

    def plot_raw(self):
        events = self.data[self.current]["events"]
        self.data[self.current]["raw"].plot(events=events)

    def import_ica(self):
        fname = QFileDialog.getOpenFileName(self, "Import ICA solution",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def show_about(self):
        QMessageBox.about(self, "About MNELAB",
                          "Licensed under the BSD 3-clause license.\n"
                          "Copyright 2017 by Clemens Brunner.")

    def show_about_qt(self):
        QMessageBox.aboutQt(self, "About Qt")

    def _activate_actions(self, activate=True):
        self.close_file_action.setEnabled(activate)
        self.plot_raw_action.setEnabled(activate)
        self.filter_action.setEnabled(activate)
        self.run_ica_action.setEnabled(activate)
        self.import_ica_action.setEnabled(activate)


app = QApplication(sys.argv)
main = MainWindow()
sys.exit(app.exec_())
