from hxl.model import TagPattern
from hxl.io import HXLReader
from hxl.filters.cache import CacheFilter

from hxl_proxy.util import norm, make_input

class Analysis:

    TAGS = [
        [
            ('#org', 'organisations')
        ],
        [
            ('#region', 'geographical regions'),
            ('#country', 'countries'),
            ('#adm1', 'level one subdivisions'),
            ('#adm2', 'level two subdivisions'),
            ('#adm3', 'level three subdivisions'),
            ('#adm4', 'level four subdivisions'),
            ('#adm5', 'level five subdivisions')
        ],
        [
            ('#sector', 'sectors'),
            ('#subsector', 'subsectors')
        ]
    ]

    def __init__(self, args):
        self.args = args
        self.filter_tags = [] # TODO
        self._saved_source = None

    @property
    def source(self):
        """Open the input on initial request."""
        if not self._saved_source:
            self._saved_source = CacheFilter(HXLReader(make_input(self.args.get('url'))))
        return self._saved_source

    def get_value_counts(self, pattern):
        """Get a list of values and frequencies for a tag pattern."""
        total = 0
        occurs = {}
        for row in self.source:
            values = row.get_all(pattern)
            for value in values:
                key = norm(value)
                if value:
                    total += 1
                    if occurs.get(key):
                        occurs[key] += 1
                    else:
                        occurs[key] = 1
        return [ { 'value': key, 'count': occurs[key], 'percentage': float(occurs[key]) / total } for key in occurs ]

    def get_top_values(self, pattern):
        return sorted(self.get_value_counts(pattern), key = lambda entry: entry['count'], reverse=True)

    @property
    def patterns(self):
        patterns = []
        for tag_list in self.TAGS:
            print(tag_list)
            for tag_info in tag_list:
                if tag_info[0] not in self.filter_tags:
                    patterns.append(tag_info)
                    break
        return patterns

