from hxl.model import TagPattern
from hxl.filters.cache import CacheFilter

from hxl_proxy.util import norm

class Data:

    def __init__(self, url):
        self.url = url
        self.source = HXLReader(CSVInput(munge_url(url)))

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

    def __init__(self, source, profile, filter_tags=[]):
        self.source = CacheFilter(source)
        self.view_tag = profile.args.get('tag')
        self.filter_tags = filter_tags

    def get_frequencies(self, pattern):
        """Get a list of values and frequencies for a tag pattern."""
        pattern = TagPattern.parse(pattern)
        occurs = {}
        for row in self.source:
            values = row.get_all(pattern)
            for value in values:
                key = norm(value)
                if value:
                    if occurs.get(key):
                        occurs[key] += 1
                    else:
                        occurs[key] = 1
        return occurs.items()

    def get_top_values(self, pattern, max=3):
        return sorted(self.get_frequencies(pattern), key = lambda frequency: frequency[1], reverse=True)[:max]

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

def do_analyse(source, tag=None):
    return Analysis(source, tag)
