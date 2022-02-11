# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

def select_all(list_widget):
    """Select all items in a QListWidget."""
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)
