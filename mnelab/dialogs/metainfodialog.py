# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import xml.etree.ElementTree as ETree

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout)


def populate_tree(parent, node):
    item = QTreeWidgetItem(parent)
    item.setText(0, node.tag.strip())
    if node.text is not None and node.text.strip():
        item.setText(1, node.text.strip())
    for element in node:
        populate_tree(item, element)


class MetaInfoDialog(QDialog):
    def __init__(self, parent, xml):
        super().__init__(parent)
        self.setWindowTitle("Information")

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Name", "Value"])
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 350)

        for stream in xml:
            header = xml[stream][2]
            header.tag = "Header"
            footer = xml[stream][6]
            footer.tag = "Footer"

            root = ETree.Element(f"Stream {stream}")
            root.extend([header, footer])
            populate_tree(tree, root)

        tree.expandAll()

        vbox = QVBoxLayout(self)
        vbox.addWidget(tree)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)

        self.resize(650, 550)
