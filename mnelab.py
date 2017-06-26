import sys
from collections import Counter
from os.path import getsize, split, splitext
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout, QLabel,
                             QVBoxLayout, QFileDialog, QWidget, QSplitter,
                             QMessageBox, QListView, QSizePolicy)
from PyQt5.QtCore import QStringListModel, pyqtSlot, QModelIndex

import mne
from mne.io.pick import channel_type


class InfoWidget(QWidget):
    """Display basic file information.

    Parameters
    ----------
    values : dict
        Each key/value pair in this dict will be displayed in a row, separated
        by a colon.
    title : str
        Title (displayed in boldface).
    """
    def __init__(self, values={}, title=""):
        super().__init__()
        self.title = QLabel()
        self.set_title(title)
        vbox = QVBoxLayout(self)
        vbox.addWidget(self.title)
        vbox.addSpacing(10)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        vbox.addLayout(self.grid)
        vbox.addStretch(1)
        self.set_values(values)

    def set_title(self, title=""):
        """Set title of the widget.

        Parameters
        ----------
        title : str
            Title (displayed in boldface).
        """
        self.title.setText("<b>{}</b>".format(title))

    def set_values(self, values={}):
        """Set values (and overwrite existing values).

        Parameters
        ----------
        values : dict
            Each key/value pair in this dict will be displayed in a row,
            separated by a colon.
        """
        self.clear()
        for row, (k, v) in enumerate(values.items()):
            col0 = QLabel(str(k) + ":")
            col1 = QLabel(str(v))
            col1.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            self.grid.addWidget(col0, row, 0)
            self.grid.addWidget(col1, row, 1)

    def clear(self):
        """Clear all values.
        """
        item = self.grid.takeAt(0)
        while item:
            item.widget().deleteLater()
            del item
            item = self.grid.takeAt(0)


class MainWindow(QMainWindow):
    """MNELAB main window.
    """
    def __init__(self):
        super().__init__()

        self.data = []  # list of loaded data sets
        self.names = QStringListModel()
        self.index = -1  # currently active data set

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("MNELAB")

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self.open_file_action = file_menu.addAction("&Open...", self.open_file,
                                                    "Ctrl+O")
        self.close_file_action = file_menu.addAction("&Close", self.close_file)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")

        plot_menu = menubar.addMenu("&Plot")
        self.plot_raw_action = plot_menu.addAction("&Raw data", self.plot_raw)

        tools_menu = menubar.addMenu("&Tools")
        self.filter_action = tools_menu.addAction("&Filter data...")
        self.run_ica_action = tools_menu.addAction("&Run ICA...")
        self.import_ica_action = tools_menu.addAction("&Load ICA...",
                                                      self.load_ica)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        help_menu.addAction("About &Qt", self.show_about_qt)

        main = QSplitter()
        self.listview = QListView()
        self.listview.setFocusPolicy(0)
        self.listview.setFrameStyle(0)
        self.listview.setModel(self.names)
        self.listview.clicked.connect(self.activate_data)
        main.addWidget(self.listview)
        self.infowidget = InfoWidget()
        main.addWidget(self.infowidget)
        width = main.size().width()
        main.setSizes((width * 0.25, width * 0.75))
        self.setCentralWidget(main)

        self._toggle_actions(False)
        self.show()

    def open_file(self):
        """Open file.
        """
        fname = QFileDialog.getOpenFileName(self, "Open file",
                                            filter="*.bdf *.edf")[0]
        if fname:
            self.index += 1

            self.data.insert(self.index, {})

            name, _ = splitext(split(fname)[-1])
            self.names.insertRows(self.index, 1)
            self.names.setData(self.names.index(self.index), name)

            raw = mne.io.read_raw_edf(fname, stim_channel=None, preload=True)

            self.data[self.index]["fname"] = fname
            self.data[self.index]["raw"] = raw
            self.data[self.index]["events"] = None

            self.infowidget.set_values(self.get_info())

            self.listview.setCurrentIndex(self.names.index(self.index))
            self.infowidget.set_title(name)
            self._toggle_actions()

    def close_file(self):
        """Close current file.
        """
        self.data.pop(self.index)
        self.names.removeRows(self.index, 1)
        if self.index >= len(self.data):
            self.index = len(self.data) - 1
        if self.index > -1:
            self.infowidget.set_values(self.get_info())
            self.infowidget.set_title(self.names.stringList()[self.index])
        else:
            self.infowidget.set_title("")
            self.infowidget.clear()
            self._toggle_actions(False)

    def get_info(self):
        """Get basic information of current file.
        """
        raw = self.data[self.index]["raw"]
        fname = self.data[self.index]["fname"]

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

    @pyqtSlot(QModelIndex)
    def activate_data(self, current):
        """Update index and information based on the file list.
        """
        self.index = current.row()
        self.infowidget.set_values(self.get_info())
        self.infowidget.set_title(self.names.data(current, 0))

    def plot_raw(self):
        """Plot raw data.
        """
        events = self.data[self.index]["events"]
        self.data[self.index]["raw"].plot(events=events)

    def load_ica(self):
        """Load ICA solution from a file.
        """
        fname = QFileDialog.getOpenFileName(self, "Load ICA",
                                            filter="*.fif *.fif.gz")
        if fname[0]:
            self.state.ica = mne.preprocessing.read_ica(fname[0])

    def show_about(self):
        """Show About dialog.
        """
        QMessageBox.about(self, "About MNELAB",
                          "Licensed under the BSD 3-clause license.\n"
                          "Copyright 2017 by Clemens Brunner.")

    def show_about_qt(self):
        """Show About Qt dialog.
        """
        QMessageBox.aboutQt(self, "About Qt")

    def _toggle_actions(self, enabled=True):
        """Toggle actions.
        """
        self.close_file_action.setEnabled(enabled)
        self.plot_raw_action.setEnabled(enabled)
        self.filter_action.setEnabled(enabled)
        self.run_ica_action.setEnabled(enabled)
        self.import_ica_action.setEnabled(enabled)


app = QApplication(sys.argv)
main = MainWindow()
sys.exit(app.exec_())
