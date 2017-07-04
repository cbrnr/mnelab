from copy import deepcopy


class EmptyDataSetsError(Exception):
    pass


class DataSets:
    def __init__(self):
        self.data = []  # list of DataSet items
        self.index = -1  # index of the currently active data set
        self.current = None  # copy of currently active data set

    def insert_data(self, dataset):
        """Insert new data set at current index.
        """
        self.index += 1
        self.data.insert(self.index, dataset)
        self.update_current()

    def remove_data(self):
        """Remove data set at current index.
        """
        try:
            self.data.pop(self.index)
        except IndexError:
            raise EmptyDataSetsError("Cannot remove data set from empty list.")
        else:
            if self.index >= len(self.data):  # if last entry was removed
                self.index = len(self.data) - 1  # reset index to last entry
            self.update_current()

    def update_current(self):
        """Update current data set copy.
        """
        if self.index > -1:
            self.current = deepcopy(self.data[self.index])
        else:
            self.current = None

    @property
    def names(self):
        """Return a list of all names.
        """
        return [item.name for item in self.data]

    @property
    def nbytes(self):
        return sum([item.raw._data.nbytes for item in self.data])

    def __len__(self):
        """Return number of data sets.
        """
        return len(self.data)


class DataSet:
    def __init__(self, name=None, fname=None, ftype=None, raw=None,
                 events=None):
        self.name = name
        self.fname = fname
        self.ftype = ftype
        self.raw = raw
        self.events = events
