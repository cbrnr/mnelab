# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QListWidget,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class AnnotationsIntervalDialog(QDialog):
    def __init__(self, parent, event_counts, annotations):
        super().__init__(parent)
        self.setWindowTitle("Create annotations from events")
        vbox = QVBoxLayout(self)
        self.event_counts = event_counts
        self.event_names = [str(e) for e in event_counts.keys()]

        # radio buttons
        self.annotations_events_button = QRadioButton("Copy events to annotations")
        vbox.addWidget(self.annotations_events_button)
        self.annotations_events_button.setChecked(True)

        self.event_event_button = QRadioButton("Define intervals between events")
        vbox.addWidget(self.event_event_button)

        self.annotation_type_group = QButtonGroup(self)
        self.annotation_type_group.addButton(self.annotations_events_button)
        self.annotation_type_group.addButton(self.event_event_button)

        # settings widget
        self.interval_settings_widget = QWidget()
        self.grid = QGridLayout(self.interval_settings_widget)
        self.grid.setContentsMargins(20, 0, 0, 20)
        self.grid.setColumnStretch(1, 1)

        # start event
        self.grid.addWidget(QLabel("Start event(s):"), 0, 0, Qt.AlignTop)
        self.start_event_list = QListWidget()
        self.start_event_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.start_event_list.addItems(self.event_names)
        self.start_event_list.setMaximumHeight(100)
        self.grid.addWidget(self.start_event_list, 0, 1)

        # start offset
        self.grid.addWidget(QLabel("Start offset:"), 1, 0)
        self.start_offset_spin = QDoubleSpinBox()
        self.start_offset_spin.setAlignment(Qt.AlignRight)
        self.start_offset_spin.setSingleStep(0.5)
        self.start_offset_spin.setMinimum(-99)
        self.start_offset_spin.setMaximum(99)
        self.start_offset_spin.setSuffix(" s")
        self.grid.addWidget(self.start_offset_spin, 1, 1)

        # end event
        self.grid.addWidget(QLabel("End event(s):"), 2, 0, Qt.AlignTop)
        self.end_event_list = QListWidget()
        self.end_event_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.end_event_list.addItems(self.event_names)
        self.end_event_list.setMaximumHeight(100)
        self.grid.addWidget(self.end_event_list, 2, 1)

        # end offset
        self.grid.addWidget(QLabel("End offset:"), 3, 0)
        self.end_offset_spin = QDoubleSpinBox()
        self.end_offset_spin.setAlignment(Qt.AlignRight)
        self.end_offset_spin.setSingleStep(0.5)
        self.end_offset_spin.setMinimum(-99)
        self.end_offset_spin.setMaximum(99)
        self.end_offset_spin.setSuffix(" s")
        self.grid.addWidget(self.end_offset_spin, 3, 1)

        # annotation name
        self.grid.addWidget(QLabel("Annotation:"), 4, 0)
        self.annotation_combo = QComboBox()
        self.annotation_combo.setEditable(True)
        self.annotation_combo.lineEdit().setPlaceholderText("Create annotation...")
        self.annotation_combo.addItems(annotations)
        self.annotation_combo.setCurrentIndex(-1)
        self.annotation_combo.setMinimumWidth(130)
        self.grid.addWidget(self.annotation_combo, 4, 1)

        # checkboxes
        self.to_start_check = QCheckBox("Extend to start")
        self.to_start_check.setChecked(True)
        self.grid.addWidget(self.to_start_check, 5, 0, 1, 2)

        self.to_end_check = QCheckBox("Extend to end")
        self.to_end_check.setChecked(True)
        self.grid.addWidget(self.to_end_check, 6, 0, 1, 2)

        # warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #d32f2f;")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        self.grid.addWidget(self.warning_label, 7, 0, 1, 2)

        vbox.addWidget(self.interval_settings_widget)

        # buttons
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.addWidget(self.buttonbox)

        # connections
        self.ok_button = self.buttonbox.button(QDialogButtonBox.Ok)
        self.annotation_type_group.buttonToggled.connect(self._on_interval_type_changed)
        self.annotation_type_group.buttonToggled.connect(self._check_validity)

        # trigger checks
        self.start_event_list.itemSelectionChanged.connect(self._check_validity)
        self.end_event_list.itemSelectionChanged.connect(self._check_validity)

        self.annotation_combo.currentTextChanged.connect(self._check_validity)

        self.interval_settings_widget.setEnabled(self.event_event_button.isChecked())

        # initial check
        self._check_validity()

        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def _check_validity(self):
        if self.annotations_events_button.isChecked():
            self.ok_button.setEnabled(True)
            self.warning_label.setVisible(False)
            return

        start_items = self.start_event_list.selectedItems()
        end_items = self.end_event_list.selectedItems()

        start_events = [item.text() for item in start_items]
        end_events = [item.text() for item in end_items]

        has_start = len(start_events) > 0
        has_end = len(end_events) > 0

        annotation_text = self.annotation_combo.currentText().strip()
        annotation_filled = len(annotation_text) > 0

        is_common = False
        warning_msg = ""

        # check events
        if has_start and has_end:
            common_events = set(start_events).intersection(set(end_events))
            if common_events:
                is_common = True
                warning_msg = "Start and end events cannot be the same."
            else:
                total_start_count = sum(
                    self.event_counts.get(int(e), 0) for e in start_events
                )
                total_end_count = sum(
                    self.event_counts.get(int(e), 0) for e in end_events
                )
                if total_start_count != total_end_count:
                    warning_msg = (
                        f"Unequal number of events. Selected start events have "
                        f"{total_start_count} occurrences, while end events have "
                        f"{total_end_count}. Unpaired events will be ignored."
                    )

        self.warning_label.setVisible(bool(warning_msg))
        self.warning_label.setText(warning_msg)

        if has_start and has_end and annotation_filled and not is_common:
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

        self.adjustSize()

    def _on_interval_type_changed(self, button, checked):
        if not checked:
            return
        is_interval_mode = button == self.event_event_button
        self.interval_settings_widget.setEnabled(is_interval_mode)

        if not is_interval_mode:
            self.warning_label.setVisible(False)

    def annotations_from_events(self):
        return self.annotations_events_button.isChecked()

    def event_to_event_data(self):
        return {
            "start_events": [
                int(i.text()) for i in self.start_event_list.selectedItems()
            ],
            "start_offset": self.start_offset_spin.value(),
            "end_events": [int(i.text()) for i in self.end_event_list.selectedItems()],
            "end_offset": self.end_offset_spin.value(),
            "annotation": self.annotation_combo.currentText(),
            "extend_start": self.to_start_check.isChecked(),
            "extend_end": self.to_end_check.isChecked(),
        }
