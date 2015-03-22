"""HXL filter for previewing a dataset."""

from hxl.model import DataProvider

class PreviewFilter(DataProvider):
    """Show only up to the first n rows of a dataset."""

    def __init__(self, source, max_rows=10):
        self.source = source
        self.max_rows = max_rows
        self.has_more_rows = False
        self.total_rows = 0
        self._row_counter = 0


    @property
    def columns(self):
        return self.source.columns

    def __next__(self):
        row = self.source.next()

        if self._row_counter >= self.max_rows:
            self.has_more_rows = True
            self.total_rows +=1
            for row in self.source:
                self.total_rows += 1
            raise StopIteration()
        else:
            self._row_counter += 1
            self.total_rows += 1
            return row

    next = __next__

# end
