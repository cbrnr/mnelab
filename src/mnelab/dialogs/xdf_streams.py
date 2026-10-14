# © MNELAB developers
#
# License: BSD (3-clause)

from mnextend.io.xdf import stream_modes
from PySide6.QtCore import QSignalBlocker, Qt, Slot
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
)

from mnelab.dialogs.utils import (
    FloatTableWidgetItem,
    IntTableWidgetItem,
    set_header_alignments,
)
from mnelab.widgets import CheckTableWidget, FlatDoubleSpinBox, set_tooltip

# modes as in MNEXTEND (shown capitalized)
ANNOTATIONS = "annotations"
CONTINUOUS = "continuous"
DISCRETE = "discrete"
IMPORT_AS_TOOLTIP = (
    "Annotations: Each value becomes an annotation\n"
    "Continuous: Signals are filtered and resampled as usual\n"
    "Discrete: Values are kept unchanged when resampling"
)
FALLBACK_FS = 100.0  # suggested rate if only 0 Hz streams are loaded as channels
COL_ID, COL_IMPORT_AS = 1, 7


class XDFStreamsDialog(QDialog):
    def __init__(self, parent, streams, fname):
        """Select XDF streams and how to import them.

        Parameters
        ----------
        parent : QWidget | None
            Parent widget.
        streams : list[dict]
            Stream information as returned by `resolve_streams(fname)`.
        fname : str
            File name of the XDF file.
        """
        super().__init__(parent)
        self.setWindowTitle("Select XDF Streams")
        self.fname = fname
        self._infos = {s["stream_id"]: s for s in streams}
        self._fs_edited = False  # whether the user changed the rate manually
        self._resample_choice = False  # resample if optional (single stream)

        # the "Import As" column contains combo boxes, which cannot be sorted
        self.view = CheckTableWidget(
            len(streams), 8, "streams", unsortable=(COL_IMPORT_AS,)
        )
        for i, stream in enumerate(streams):
            self.view.set_check_item(i)
            self.view.setItem(i, COL_ID, IntTableWidgetItem(stream["stream_id"]))
            self.view.setItem(i, 2, QTableWidgetItem(stream["name"] or ""))
            self.view.setItem(i, 3, QTableWidgetItem(stream["type"] or ""))
            self.view.setItem(i, 4, IntTableWidgetItem(stream["channel_count"]))
            self.view.setItem(i, 5, QTableWidgetItem(stream["channel_format"]))
            self.view.setItem(i, 6, FloatTableWidgetItem(stream["nominal_srate"]))
            modes = stream_modes(stream)  # the first mode is the default
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, modes[0])
            self.view.setItem(i, COL_IMPORT_AS, item)
            if len(modes) == 1:
                item.setText(modes[0].capitalize())
                item.setToolTip(IMPORT_AS_TOOLTIP)
            else:
                combo = QComboBox()
                for mode in modes:
                    combo.addItem(mode.capitalize(), mode)
                combo.setToolTip(IMPORT_AS_TOOLTIP)
                combo.currentIndexChanged.connect(self.update_controls)
                self.view.setCellWidget(i, COL_IMPORT_AS, combo)

        self.view.set_labels(
            [
                "",
                "ID",
                "Name",
                "Type",
                "Channels",
                "Format",
                "Sampling Rate",
                "Import As",
            ]
        )
        set_header_alignments(self.view, "lrllrlrl")
        self.view.horizontalHeaderItem(COL_IMPORT_AS).setToolTip(IMPORT_AS_TOOLTIP)

        self.view.setSortingEnabled(True)
        self.view.sortByColumn(COL_ID, Qt.SortOrder.AscendingOrder)
        self.view.checks_changed.connect(self.update_controls)

        self.resample = QCheckBox()
        self.resample.clicked.connect(self._resample_clicked)
        self.resample.toggled.connect(self._toggle_resample_controls)
        self.resample_label = QLabel("Resample to")
        self.fs_new = FlatDoubleSpinBox()
        rates = [s["nominal_srate"] for s in streams if s["channel_format"] != "string"]
        self.fs_new.setRange(1, max([FALLBACK_FS, *rates]))
        self.fs_new.setValue(1)
        self.fs_new.setDecimals(1)
        self.fs_new.setSuffix(" Hz")
        self.fs_new.valueChanged.connect(self._fs_changed)
        set_tooltip(
            "Resample streams imported as channels to this sampling frequency",
            self.resample,
            self.resample_label,
            self.fs_new,
        )

        self.gap_threshold_label = QLabel("Detect Gaps Longer than")
        self.gap_threshold_checkbox = QCheckBox()
        self.gap_threshold_checkbox.stateChanged.connect(
            self._toggle_gap_threshold_spinbox
        )
        self.gap_threshold = FlatDoubleSpinBox()
        self.gap_threshold.setRange(0.1, 10)
        self.gap_threshold.setValue(0.1)
        self.gap_threshold.setDecimals(1)
        self.gap_threshold.setSingleStep(0.1)
        self.gap_threshold.setSuffix(" s")
        self.gap_threshold.setEnabled(False)
        set_tooltip(
            "Detect gaps in resampled streams longer than this duration",
            self.gap_threshold_checkbox,
            self.gap_threshold_label,
            self.gap_threshold,
        )

        self._prefix_markers = QCheckBox("Prefix Annotations with Stream ID")
        self._prefix_markers.setChecked(False)
        self._prefix_markers.setToolTip(
            "Prefix annotation descriptions with their stream ID"
        )

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.resample)
        hbox1.addWidget(self.resample_label)
        hbox1.addWidget(self.fs_new)
        hbox1.addSpacing(20)
        hbox1.addWidget(self.gap_threshold_checkbox)
        hbox1.addWidget(self.gap_threshold_label)
        hbox1.addWidget(self.gap_threshold)
        hbox1.addStretch()
        hbox1.addWidget(self._prefix_markers)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.view)
        vbox.addLayout(hbox1)

        hbox2 = QHBoxLayout()
        self.details_button = QPushButton("Details")
        self.details_button.setToolTip("Show XDF metadata")
        self.details_button.clicked.connect(self.details)
        hbox2.addWidget(self.details_button)
        hbox2.addStretch()
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        hbox2.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.addLayout(hbox2)

        self.update_controls()
        self.resize(875, 650)
        self.view.setColumnWidth(COL_ID, 80)
        self.view.setColumnWidth(2, 220)
        self.view.setColumnWidth(3, 105)
        self.view.setColumnWidth(4, 75)
        self.view.setColumnWidth(5, 75)
        self.view.setColumnWidth(6, 100)
        self.setFocus()

    def _stream_id(self, row):
        return self.view.item(row, COL_ID).value()

    def _mode(self, row):
        """Return the mode in which the stream in `row` is imported."""
        combo = self.view.cellWidget(row, COL_IMPORT_AS)
        if combo is not None:
            return combo.currentData()
        return self.view.item(row, COL_IMPORT_AS).data(Qt.ItemDataRole.UserRole)

    @property
    def streams(self):
        """Modes of the checked streams (sorted by ID) as expected by `read_raw()`."""
        modes = {
            self._stream_id(row): self._mode(row)
            for row in range(self.view.rowCount())
            if self.view.is_checked(row)
        }
        return dict(sorted(modes.items()))

    def _checked_streams(self, *modes):
        """Return information of checked streams (sorted by ID) in one of `modes`."""
        return [
            self._infos[stream_id]
            for stream_id, mode in self.streams.items()
            if mode in modes
        ]

    @property
    def prefix_markers(self):
        return self._prefix_markers.isEnabled() and self._prefix_markers.isChecked()

    def details(self):
        self.parent().xdf_metadata(self.fname)

    def suggested_fs(self):
        """Return the suggested sampling frequency for the streams imported as channels.

        The stream with the most channels (ties: the higher rate) among continuous
        streams determines the rate. Without continuous streams, the highest rate of
        regular-rate discrete streams is used to lose as few value changes as possible.
        If only 0 Hz streams are imported as channels, the fallback rate is used.
        """
        continuous = self._checked_streams(CONTINUOUS)
        if continuous:
            main = max(
                continuous, key=lambda s: (s["channel_count"], s["nominal_srate"])
            )
            return main["nominal_srate"]
        rates = [s["nominal_srate"] for s in self._checked_streams(DISCRETE)]
        if any(rates):
            return max(rates)
        return FALLBACK_FS

    @Slot(bool)
    def _resample_clicked(self, checked):
        self._resample_choice = checked

    @Slot()
    def _fs_changed(self):
        self._fs_edited = True

    @Slot()
    def _toggle_resample_controls(self):
        """Enable/disable rate and gap threshold controls based on resampling."""
        channels = self._checked_streams(CONTINUOUS, DISCRETE)
        enabled = self.resample.isChecked() and bool(channels)
        self.resample_label.setEnabled(enabled)
        self.fs_new.setEnabled(enabled)
        self.gap_threshold_checkbox.setEnabled(enabled)
        self.gap_threshold_label.setEnabled(enabled)
        if not enabled:
            self.gap_threshold_checkbox.setChecked(False)

    @Slot()
    def _toggle_gap_threshold_spinbox(self):
        """Enable/disable gap threshold spinbox based on gap threshold checkbox."""
        self.gap_threshold.setEnabled(self.gap_threshold_checkbox.isChecked())

    @Slot()
    def update_controls(self):
        """Update rows and controls after a stream was checked or changed."""
        muted = self.palette().color(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text
        )
        normal = self.palette().color(QPalette.ColorRole.Text)
        with QSignalBlocker(self.view):
            for row in range(self.view.rowCount()):
                checked = self.view.is_checked(row)
                for col in range(self.view.columnCount()):
                    self.view.item(row, col).setForeground(normal if checked else muted)
                combo = self.view.cellWidget(row, COL_IMPORT_AS)
                if combo is not None:
                    combo.setEnabled(checked)
        channels = self._checked_streams(CONTINUOUS, DISCRETE)
        forced = len(channels) > 1 or any(s["nominal_srate"] == 0 for s in channels)
        self.resample.setEnabled(len(channels) == 1 and not forced)
        self.resample.setChecked(forced or self._resample_choice)
        self._toggle_resample_controls()

        if channels and not self._fs_edited:
            with QSignalBlocker(self.fs_new):
                self.fs_new.setValue(self.suggested_fs())

        self._prefix_markers.setEnabled(len(self._checked_streams(ANNOTATIONS)) > 1)

        ok_button = self.buttonbox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(bool(channels))
