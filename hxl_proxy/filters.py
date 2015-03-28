"""Configure a filter pipeline from command-line arguments.

The main entry point is setup_filters()

The GET parameters have numbers appended, e.g. "rename-oldtag7". This
module uses the numbers to group the parameters, then to construct the
hxl.filter objects from them and build a pipeline.
"""

from hxl_proxy import make_input

from hxl.model import TagPattern, Column
from hxl.io import HXLReader

from hxl.filters.add import AddFilter
from hxl.filters.clean import CleanFilter
from hxl.filters.count import CountFilter
from hxl.filters.cut import CutFilter
from hxl.filters.merge import MergeFilter
from hxl.filters.rename import RenameFilter
from hxl.filters.select import SelectFilter, Query
from hxl.filters.sort import SortFilter
from hxl.filters.tag import Tagger

# Minimum default number of filters to check
DEFAULT_FILTER_COUNT = 5

# Maximum number of filters to check
MAX_FILTER_COUNT = 10

def setup_filters(profile):
    """
    Open a stream to a data source URL, and create a filter pipeline based on the arguments.
    @param profile the GET-request profile (uses only profile.args).
    @return a HXL DataSource representing the full pipeline.
    """

    # null profile or url means null source
    if not profile or not profile.args.get('url'):
        return None

    # Basic input source
    source = HXLReader(make_tagged_input(profile.args))

    # Create the filter pipeline from the source
    filter_count = max(int(profile.args.get('filter_count', DEFAULT_FILTER_COUNT)), MAX_FILTER_COUNT)
    for index in range(1, 1+filter_count):
        filter = profile.args.get('filter%02d' % index)
        if filter == 'add':
            source = add_add_filter(source, profile.args, index)
        elif filter == 'clean':
            source = add_clean_filter(source, profile.args, index)
        elif filter == 'count':
            source = add_count_filter(source, profile.args, index)
        elif filter == 'cut':
            source = add_cut_filter(source, profile.args, index)
        elif filter == 'merge':
            source = add_merge_filter(source, profile.args, index)
        elif filter == 'rename':
            source = add_rename_filter(source, profile.args, index)
        elif filter == 'select':
            source = add_select_filter(source, profile.args, index)
        elif filter == 'sort':
            source = add_sort_filter(source, profile.args, index)

    return source

def make_tagged_input(args):
    """Create the raw input, optionally using the Tagger filter."""
    url = args.get('url')

    # TODO raise exception
    input = make_input(url)

    # Intercept tagging as a special data input
    if args.get('filter01') == 'tagger':
        specs = []
        for n in range(1, 21):
            header = args.get('tagger-%02d-header' % n)
            tag = args.get('tagger-%02d-tag' % n)
            if header and tag:
                specs.append((header, tag))
        if len(specs) > 0:
            input = Tagger(input, specs)

    return input

def add_add_filter(source, args, index):
    """Add the hxladd filter to the end of the chain."""
    tagspec = _parse_tagspec(args.get('add-tag%02d' % index))
    header = args.get('add-header%02d' % index)
    value = args.get('add-value%02d' % index)
    before = (args.get('add-before%02d' % index) == 'on')
    values = [(Column.parse(tagspec, header=header), value)]
    return AddFilter(source, values=values, before=before)

def add_clean_filter(source, args, index):
    """Add the hxlclean filter to the end of the pipeline."""
    whitespace_tags = TagPattern.parse_list(args.get('clean-whitespace-tags%02d' % index, ''))
    upper_tags = TagPattern.parse_list(args.get('clean-upper-tags%02d' % index, ''))
    lower_tags = TagPattern.parse_list(args.get('clean-lower-tags%02d' % index, ''))
    date_tags = TagPattern.parse_list(args.get('clean-date-tags%02d' % index, ''))
    number_tags = TagPattern.parse_list(args.get('clean-number-tags%02d' % index, ''))
    return CleanFilter(source, whitespace=whitespace_tags, upper=upper_tags, lower=lower_tags, date=date_tags, number=number_tags)

def add_count_filter(source, args, index):
    """Add the hxlcount filter to the end of the pipeline."""
    tags = TagPattern.parse_list(args.get('count-tags%02d' % index, ''))
    aggregate_tag = args.get('count-aggregate-tag%02d' % index)
    if aggregate_tag:
        aggregate_tag = TagPattern.parse(aggregate_tag)
    else:
        aggregate_tag = None
    return CountFilter(source, tags=tags, aggregate_tag=aggregate_tag)

def add_cut_filter(source, args, index):
    """Add the hxlcut filter to the end of the pipeline."""
    include_tags = TagPattern.parse_list(args.get('cut-include-tags%02d' % index, []))
    exclude_tags = TagPattern.parse_list(args.get('cut-exclude-tags%02d' % index, []))
    return CutFilter(source, include_tags=include_tags, exclude_tags=exclude_tags)

def add_merge_filter(source, args, index):
    """Add the hxlmerge filter to the end of the pipeline."""
    tags = TagPattern.parse_list(args.get('merge-tags%02d' % index, []))
    keys = TagPattern.parse_list(args.get('merge-keys%02d' % index, []))
    replace = (args.get('merge-replace%02d' % index) == 'on')
    overwrite = (args.get('merge-overwrite%02d' % index) == 'on')
    url = args.get('merge-url%02d' % index)
    merge_source = HXLReader(make_input(url))
    return MergeFilter(source, merge_source, keys=keys, tags=tags, replace=replace, overwrite=overwrite)

def add_rename_filter(source, args, index):
    """Add the hxlrename filter to the end of the pipeline."""
    oldtag = TagPattern.parse(args.get('rename-oldtag%02d' % index))
    tagspec = _parse_tagspec(args.get('rename-newtag%02d' % index))
    header = args.get('rename-header%02d' % index)
    column = Column.parse(tagspec, header=header)
    return RenameFilter(source, [(oldtag, column)])

def add_select_filter(source, args, index):
    """Add the hxlselect filter to the end of the pipeline."""
    queries = []
    for subindex in range(1, 6):
        query = args.get('select-query%02d-%02d' % (index, subindex))
        if query:
            queries.append(Query.parse(query))
    reverse = (args.get('select-reverse%02d' % index) == 'on')
    return SelectFilter(source, queries=queries, reverse=reverse)

def add_sort_filter(source, args, index):
    """Add the hxlsort filter to the end of the pipeline."""
    tags = TagPattern.parse_list(args.get('sort-tags%02d' % index, ''))
    reverse = (args.get('sort-reverse%02d' % index) == 'on')
    return SortFilter(source, tags=tags, reverse=reverse)

def _parse_tagspec(s):
    if (s[0] == '#'):
        return s
    else:
        return '#' + s

# end
