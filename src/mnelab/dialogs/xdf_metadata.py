# © MNELAB developers
#
# License: BSD (3-clause)

import xml.etree.ElementTree as ETree

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


def populate_tree(parent, node):
    item = QTreeWidgetItem(parent)
    item.setText(0, node.tag.strip())
    if node.text is not None and node.text.strip():
        item.setText(1, node.text.strip())
    for element in node:
        populate_tree(item, element)


class XDFMetadataDialog(QDialog):
    def __init__(self, parent, xml):
        super().__init__(parent)
        self.setWindowTitle("XDF Metadata")

        self.tree = tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Name", "Value"])
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 350)

        for stream in sorted(xml):
            header = xml[stream][2]
            header.tag = "Header"
            footer = xml[stream][6]
            footer.tag = "Footer"

            root = ETree.Element(f"Stream {stream}")
            root.extend([header, footer])
            populate_tree(tree, root)

        tree.expandAll()

        self.toggle_button = QPushButton()
        self.toggle_button.clicked.connect(self.toggle_all)
        tree.itemExpanded.connect(self._update_toggle_button)
        tree.itemCollapsed.connect(self._update_toggle_button)
        self._update_toggle_button()

        vbox = QVBoxLayout(self)
        vbox.addWidget(tree)
        buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        hbox = QHBoxLayout()
        hbox.addWidget(self.toggle_button)
        hbox.addStretch()
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        buttonbox.accepted.connect(self.accept)

        self.resize(650, 550)
        self.setFocus()

    def _any_expanded(self):
        return any(
            self.tree.topLevelItem(i).isExpanded()
            for i in range(self.tree.topLevelItemCount())
        )

    def _update_toggle_button(self):
        if self._any_expanded():
            self.toggle_button.setText("Collapse All")
        else:
            self.toggle_button.setText("Expand All")

    def toggle_all(self):
        """Collapse all items if any stream is expanded, otherwise expand all."""
        if self._any_expanded():
            self.tree.collapseAll()
        else:
            self.tree.expandAll()
