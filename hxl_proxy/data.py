"""Data operations."""

from hxl_proxy import munge_url

from hxl.model import TagPattern
from hxl.io import URLInput, HXLReader

from hxl.filters.add import AddFilter
from hxl.filters.clean import CleanFilter
from hxl.filters.count import CountFilter
from hxl.filters.cut import CutFilter
from hxl.filters.merge import MergeFilter
from hxl.filters.rename import RenameFilter
from hxl.filters.select import SelectFilter, Query
from hxl.filters.sort import SortFilter
from hxl.filters.tag import Tagger
from hxl.filters.validate import ValidateFilter

def setup_filters(profile):
    """Create a filter pipeline based on a profile."""

    url = profile.args.get('url')
    input = URLInput(munge_url(url))

    # Intercept tagging as a special data input
    if profile.args.get('filter01') == 'tagger':
        specs = []
        for n in range(1, 11):
            header = profile.args.get('tagger-%02d-header' % n)
            tag = profile.args.get('tagger-%02d-tag' % n)
            if header and tag:
                specs.append((header, tag))
        if len(specs) > 0:
            print(specs)
            input = Tagger(input, specs)

    source = HXLReader(input)
    filter_count = int(profile.args.get('filter_count', 5))
    for n in range(1,filter_count+1):
        filter = profile.args.get('filter%02d' % n)
        if filter == 'add':
            tag = TagPattern.parse(profile.args.get('add-tag%02d' % n))
            value = profile.args.get('add-value%02d' % n)
            header = profile.args.get('add-header%02d' % n)
            before = (profile.args.get('add-before%02d' % n) == 'on')
            source = AddFilter(source, {tag: [value, header]}, before)
        elif filter == 'clean':
            whitespace_tags = TagPattern.parse_list(profile.args.get('clean-whitespace-tags%02d' % n, ''))
            upper_tags = TagPattern.parse_list(profile.args.get('clean-upper-tags%02d' % n, ''))
            lower_tags = TagPattern.parse_list(profile.args.get('clean-lower-tags%02d' % n, ''))
            date_tags = TagPattern.parse_list(profile.args.get('clean-date-tags%02d' % n, ''))
            number_tags = TagPattern.parse_list(profile.args.get('clean-number-tags%02d' % n, ''))
            source = CleanFilter(source, whitespace=whitespace_tags, upper=upper_tags, lower=lower_tags, date=date_tags, number=number_tags)
        elif filter == 'count':
            tags = TagPattern.parse_list(profile.args.get('count-tags%02d' % n, ''))
            aggregate_tag = profile.args.get('count-aggregate-tag%02d' % n)
            if aggregate_tag:
                aggregate_tag = TagPattern.parse(aggregate_tag)
            else:
                aggregate_tag = None
            source = CountFilter(source, tags=tags, aggregate_tag=aggregate_tag)
        elif filter == 'cut':
            include_tags = TagPattern.parse_list(profile.args.get('cut-include-tags%02d' % n, []))
            exclude_tags = TagPattern.parse_list(profile.args.get('cut-exclude-tags%02d' % n, []))
            source = CutFilter(source, include_tags=include_tags, exclude_tags=exclude_tags)
        elif filter == 'merge':
            tags = TagPattern.parse_list(profile.args.get('merge-tags%02d' % n, []))
            keys = TagPattern.parse_list(profile.args.get('merge-keys%02d' % n, []))
            before = (profile.args.get('merge-before%02d' % n) == 'on')
            url = profile.args.get('merge-url%02d' % n)
            merge_source = HXLReader(URLInput(munge_url(url)))
            source = MergeFilter(source, merge_source, keys, tags, before)
        elif filter == 'rename':
            oldtag = TagPattern.parse(profile.args.get('rename-oldtag%02d' % n))
            newtag = TagPattern.parse(profile.args.get('rename-newtag%02d' % n))
            header = profile.args.get('rename-header%02d' % n)
            source = RenameFilter(source, {oldtag: [newtag, header]})
        elif filter == 'select':
            queries = []
            for m in range(1, 6):
                query = profile.args.get('select-query%02d-%02d' % (n, m))
                if query:
                    queries.append(Query.parse(query))
            reverse = (profile.args.get('select-reverse%02d' % n) == 'on')
            source = SelectFilter(source, queries=queries, reverse=reverse)
        elif filter == 'sort':
            tags = TagPattern.parse_list(profile.args.get('sort-tags%02d' % n, ''))
            reverse = (profile.args.get('sort-reverse%02d' % n) == 'on')
            source = SortFilter(source, tags=tags, reverse=reverse)

        return source
