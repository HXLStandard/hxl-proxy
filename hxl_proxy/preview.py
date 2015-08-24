"""HXL filter for previewing a dataset."""

import hxl


class PreviewFilter(hxl.Dataset):
    """Show only up to the first n rows of a dataset."""

    def __init__(self, source, max_rows=10):
        self.source = source
        self.max_rows = max_rows
        self.has_more_rows = False
        self.total_rows = 0


    @property
    def columns(self):
        return self.source.columns

    def __iter__(self):
        return PreviewFilter.Iterator(self)

    class Iterator:

        def __init__(self, outer):
            self.outer = outer
            self.iterator = iter(outer.source)
            self._row_counter = 0

        def __next__(self):
            row = next(self.iterator)

            if self._row_counter >= self.outer.max_rows:
                self.outer.has_more_rows = True
                self.outer.total_rows +=1
                while next(self.iterator):
                    self.outer.total_rows += 1
                raise StopIteration()
            else:
                self._row_counter += 1
                self.outer.total_rows += 1
                return row

        next = __next__

# end
