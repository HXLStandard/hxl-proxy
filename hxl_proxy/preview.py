"""HXL filter for previewing a dataset."""

from hxl.model import DataProvider

class PreviewFilter(DataProvider):
    """Show only up to the first n rows of a dataset."""

    def __init__(self, source, max=10):
        self.source = source
        self.max = max
        self.count = 0
        self.has_more = True

    @property
    def columns(self):
        return self.source.columns

    def __next__(self):
        row = self.source.next()
        if not row:
            self.has_more = False
            return None
        elif self.count >= self.max:
            self.has_more = True
            return None
        else:
            self.count += 1
            return self.source.next()

    next = __next__

# end
