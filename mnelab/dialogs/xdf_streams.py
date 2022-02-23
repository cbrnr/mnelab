# © MNELAB developers
#
# License: BSD (3-clause)

from collections import defaultdict

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .events import IntTableWidgetItem


class AlwaysSelectedTableWidget(QTableWidget):
    # to avoid deselection when clicking in an empty region of the table, filter mouseclicks
    def mousePressEvent(self, event):
        if self.indexAt(event.position().toPoint()).isValid():
            QTableWidget.mousePressEvent(self, event)


class XDFStreamsDialog(QDialog):
    def __init__(self, parent, rows, fname, selected=None, disabled=None):
        super().__init__(parent)
        self.setWindowTitle("Select XDF Stream")
        self.fname = fname

        self.view = AlwaysSelectedTableWidget(len(rows), 6)
        for i, row in enumerate(rows):
            self.view.setItem(i, 0, IntTableWidgetItem(row[0]))
            self.view.setItem(i, 1, QTableWidgetItem(row[1]))
            self.view.setItem(i, 2, QTableWidgetItem(row[2]))
            self.view.setItem(i, 3, IntTableWidgetItem(row[3]))
            self.view.setItem(i, 4, QTableWidgetItem(row[4]))
            self.view.setItem(i, 5, IntTableWidgetItem(row[5]))
            if i in disabled:
                for col in range(6):
                    self.view.item(i, col).setFlags(Qt.NoItemFlags)
        self.view.setHorizontalHeaderLabels([
            "ID",
            "Name",
            "Type",
            "Channels",
            "Format",
            "Sampling Rate",
        ])

        self.view.setEditTriggers(QTableWidget.NoEditTriggers)
        self.view.setSelectionBehavior(QTableWidget.SelectRows)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setShowGrid(False)
        if selected is not None:
            self.view.selectRow(selected)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)

        self.view.itemSelectionChanged.connect(self._set_suggested_fs)
        self.view.itemSelectionChanged.connect(self._toggle_resample)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)
        hbox1 = QHBoxLayout()
        self._effective_srate = QCheckBox("Use effective sampling rate")
        self._effective_srate.setChecked(True)
        hbox1.addWidget(self._effective_srate)
        self._prefix_markers = QCheckBox("Prefix markers with stream ID")
        self._prefix_markers.setChecked(False)
        if len(disabled) < 2:
            self._prefix_markers.setEnabled(False)
        hbox1.addStretch()
        hbox1.addWidget(self._prefix_markers)

        hbox_resample = QHBoxLayout()
        self.resample = QCheckBox()
        hbox_resample.addWidget(self.resample)
        self.resample_label = QLabel("Resample to:")
        hbox_resample.addWidget(self.resample_label)

        self.fs_new = QDoubleSpinBox()
        self.fs_new.setRange(1,  max(r[5] for r in rows))
        self.fs_new.setValue(1)
        self.fs_new.setDecimals(1)
        self.fs_new.setSuffix(" Hz")
        hbox_resample.addWidget(self.fs_new)
        hbox1.addStretch()
        hbox1.addLayout(hbox_resample)
        vbox.addLayout(hbox1)

        hbox2 = QHBoxLayout()
        self.details_button = QPushButton("Details")
        self.details_button.clicked.connect(self.details)
        hbox2.addWidget(self.details_button)
        hbox2.addStretch()
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox2.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.addLayout(hbox2)

        self._set_suggested_fs()
        self._toggle_resample()
        self.resize(775, 650)
        self.view.setColumnWidth(0, 90)
        self.view.setColumnWidth(1, 200)
        self.view.setColumnWidth(2, 140)

    @property
    def effective_srate(self):
        return self._effective_srate.isChecked()

    @property
    def prefix_markers(self):
        return self._prefix_markers.isChecked()

    def details(self):
        self.parent().xdf_metadata(self.fname)

    @Slot()
    def _set_suggested_fs(self):
        # Like in SigViewer, the most common sampling rate is suggested.
        channel_counts = []
        sampling_rates = []
        row_indices = {r.row() for r in self.view.selectedIndexes()}
        for row in row_indices:
            channel_counts.append(self.view.item(row, 3).value())
            sampling_rates.append(self.view.item(row, 5).value())

        counts = defaultdict(int)
        for channel_count, sampling_rate in zip(channel_counts, sampling_rates):
            if sampling_rate != 0:
                counts[sampling_rate] += channel_count

        suggested_fs = max(counts, key=counts.get)
        self.fs_new.setValue(suggested_fs)

    @Slot()
    def _toggle_resample(self):
        if len(self.view.selectionModel().selectedRows()) > 1:
            self.resample.setChecked(True)
            self.resample.setEnabled(False)
        else:
            self.resample.setChecked(False)
            self.resample.setEnabled(True)
