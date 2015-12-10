"""
Analysis logic

For now, focusses on 3W-type data.
"""

import hxl
from hxl_proxy.util import strnorm, urlquote

class Analysis:
    """Business logic for analysing a dataset."""

    # Default tags to analyse
    TAGS = [
        [
            ('#org', 'organisations')
        ],
        [
            ('#sector', 'sectors'),
            ('#subsector', 'subsectors')
        ],
        [
            ('#region', 'geographical regions'),
            ('#country', 'countries'),
            ('#adm1', 'level one subdivisions'),
            ('#adm2', 'level two subdivisions'),
            ('#adm3', 'level three subdivisions'),
            ('#adm4', 'level four subdivisions'),
            ('#adm5', 'level five subdivisions')
        ]
    ]

    def __init__(self, args):
        """
        Constructor
        @param args the GET parameters
        """
        self.args = args
        self._saved_source = None
        self._saved_filters = None
        self._get_original_values()

    def get_value_counts(self, pattern):
        """Get a list of values and frequencies for a tag pattern."""
        total = 0
        occurs = {}
        for row in self.source:
            values = row.get_all(pattern)
            for value in values:
                key = strnorm(value)
                if value:
                    total += 1
                    if occurs.get(key):
                        occurs[key]['count'] += 1
                    else:
                        occurs[key] = { 'count': 1, 'orig': value }
        return [
            {
                'value': key,
                'orig': occurs[key]['orig'],
                'count': occurs[key]['count'],
                'percentage': float(occurs[key]['count']) / total
            }
            for key in occurs
        ]

    def get_top_values(self, pattern):
        return sorted(self.get_value_counts(pattern), key = lambda entry: entry['count'], reverse=True)

    def make_query(self, pattern=None, value=None, limit=None):
        """Construct a query string"""
        queries = []
        for filter in self.filters:
            queries.append([urlquote(str(filter['pattern'])[1:]), urlquote(filter['value'])])
            if limit is not None and filter == limit:
                break
        if pattern:
            queries.append([ urlquote(str(pattern)[1:]), urlquote(value) ])
        queries.append([ urlquote('url'), urlquote(self.args.get('url')) ])
        return '&'.join(map(lambda item: '='.join(item), queries))

    def title(self, tag_pattern=None):
        who = self.who
        what = self.what
        where = self.where
        if tag_pattern:
            title = "List of " + str(tag_pattern)
            if who:
                title += " for " + who
            if what:
                title += " working on " + what
            if where:
                title += " in " + where
            return title
        else:
            if who and what and where:
                return 'What is {} doing for {} in {}?'.format(who, what, where)
            elif who and what:
                return 'Where is {} working in {}?'.format(who, what)
            elif who and where:
                return 'What is {} doing in {}?'.format(who, where)
            elif what and where:
                return 'Who is working on {} in {}?'.format(what, where)
            elif who:
                return 'What is {} doing, where?'.format(who)
            elif what:
                return 'Who is working on {}, where?'.format(what)
            elif where:
                return 'Who is doing what in {}?'.format(where)
            else:
                return 'Who is doing what, where?'

    @property
    def who(self):
        """Return the name for 'who'."""
        for filter in self.filters:
            if filter['pattern'].tag == '#org':
                return filter['orig']
        return None

    @property
    def what(self):
        """Return the name for 'what'."""
        for filter in self.filters:
            if filter['pattern'].tag in ('#sector', '#subsector'):
                return filter['orig']
        return None

    @property
    def where(self):
        """Return the name for 'where'."""
        for filter in self.filters:
            if filter['pattern'].tag in ('#region', '#country', '#adm1', '#adm2', '#adm3', '#adm4', '#adm5', '#loc'):
                return filter['orig']
        return None

    def overview_url(self, pattern=None, value=None, limit=None):
        """Make the URL for a filtered overview."""
        return '/analysis/overview?{}'.format(self.make_query(pattern, value, limit))

    def data_url(self, pattern=None, value=None, limit=None, format=''):
        """Make the URL for a data view."""
        if format:
            format = '.' + format
        return '/analysis/data{}?{}'.format(format, self.make_query(pattern, value, limit))

    def tag_url(self, tag_pattern, pattern=None, value=None, limit=None):
        """Make a URL path for a specific tag."""
        return '/analysis/tag/{}?{}'.format(urlquote(str(tag_pattern)[1:]), self.make_query(pattern, value, limit))

    @property
    def patterns(self):
        """Return a list of tag patterns in use."""
        patterns = []
        for tag_list in self.TAGS:
            for tag_info in tag_list:
                pattern = hxl.TagPattern.parse(tag_info[0])
                if (
                        pattern.tag not in [filter['pattern'].tag for filter in self.filters]
                ) and (
                    pattern.tag in [column.tag for column in self.source.columns]
                ):
                    patterns.append(tag_info)
                    break
        return patterns

    @property
    def filters(self):
        """Construct a dict of filter values for the analysis."""
        if self._saved_filters is None:
            filters = []
            for pattern in self.args.to_dict():
                # Use every parameter except "url" as a tag name
                if pattern == 'url':
                    continue
                filters.append({
                    'pattern': hxl.TagPattern.parse(pattern),
                    'value': self.args.get(pattern)
                })
            self._saved_filters = filters
        return self._saved_filters

    @property
    def source(self):
        """Open the input on initial request."""
        if not self._saved_source:
            # Cache the whole source in memory
            source = hxl.data(self.args.get('url')).cache()
            for filter_data in self.filters:
                query = '{}={}'.format(filter_data['pattern'], filter_data['value'])
                source = source.with_rows(query)
            self._saved_source = source
        return self._saved_source

    def _get_original_values(self):
        """Get an original spelling of the filter value, for display."""
        try:
            row = next(iter(self.source))
        except StopIteration:
            row = hxl.Row([])
        for filter in self.filters:
            filter['orig'] = row.get(filter['pattern'], default=filter['value'])

# end
