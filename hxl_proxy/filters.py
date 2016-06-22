"""Configure a filter pipeline from command-line arguments.

The main entry point is setup_filters()

The GET parameters have numbers appended, e.g. "rename-oldtag7". This
module uses the numbers to group the parameters, then to construct the
hxl.filter objects from them and build a pipeline.
"""

import hxl
import hxl.filters # why do we have to import this???
from hxl.converters import Tagger

# Maximum number of filters to check
MAX_FILTER_COUNT = 99

def setup_filters(recipe):
    """
    Open a stream to a data source URL, and create a filter pipeline based on the arguments.
    @param recipe the GET-request recipe (uses only recipe['args']).
    @return a HXL DataSource representing the full pipeline.
    """

    # null recipe or url means null source
    if not recipe or not recipe['args'].get('url'):
        return None

    # Basic input source
    source = hxl.data(make_tagged_input(recipe['args']))

    # Create the filter pipeline from the source
    for index in range(1, MAX_FILTER_COUNT):
        filter = recipe['args'].get('filter%02d' % index)
        if filter == 'add':
            source = add_add_filter(source, recipe['args'], index)
        elif filter == 'clean':
            source = add_clean_filter(source, recipe['args'], index)
        elif filter == 'count':
            source = add_count_filter(source, recipe['args'], index)
        elif filter == 'column' or filter == 'cut':
            source = add_column_filter(source, recipe['args'], index)
        elif filter == 'dedup':
            source = add_dedup_filter(source, recipe['args'], index)
        elif filter == 'explode':
            source = add_explode_filter(source, recipe['args'], index)
        elif filter == 'merge':
            source = add_merge_filter(source, recipe['args'], index)
        elif filter == 'rename':
            source = add_rename_filter(source, recipe['args'], index)
        elif filter == 'rows' or filter == 'select':
            source = add_row_filter(source, recipe['args'], index)
        elif filter == 'sort':
            source = add_sort_filter(source, recipe['args'], index)
        elif filter == 'append':
            source = add_append_filter(source, recipe['args'], index)
        elif filter == 'replace':
            source = add_replace_filter(source, recipe['args'], index)
        elif filter == 'replace-map':
            source = add_replace_map_filter(source, recipe['args'], index)
        elif filter:
            raise Exception("Unknown filter type '{}'".format(filter))

    return source

def make_tagged_input(args):
    """Create the raw input, optionally using the Tagger filter."""
    url = args.get('url')
    sheet_index = int(args.get('sheet')) if args.get('sheet') else None
    input = hxl.io.make_input(url, sheet_index=sheet_index)

    # Intercept tagging as a special data input
    specs = []
    for n in range(1, 101):
        header = args.get('tagger-%02d-header' % n)
        tag = _parse_tagspec(args.get('tagger-%02d-tag' % n))
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
    values = [(hxl.Column.parse(tagspec, header=header), value)]
    return source.add_columns(specs=values, before=before)

def add_append_filter(source, args, index):
    """Add the hxlappend filter to the end of the chain."""
    exclude_columns = args.get('append-exclude-columns%02d' % index, False)
    for subindex in range(1, 100):
        dataset_url = args.get('append-dataset%02d-%02d' % (index, subindex))
        if dataset_url:
            source = source.append(hxl.data(dataset_url), not exclude_columns)
    return source

def add_clean_filter(source, args, index):
    """Add the hxlclean filter to the end of the pipeline."""
    whitespace_tags = hxl.TagPattern.parse_list(args.get('clean-whitespace-tags%02d' % index, ''))
    upper_tags = hxl.TagPattern.parse_list(args.get('clean-toupper-tags%02d' % index, ''))
    lower_tags = hxl.TagPattern.parse_list(args.get('clean-tolower-tags%02d' % index, ''))
    date_tags = hxl.TagPattern.parse_list(args.get('clean-date-tags%02d' % index, ''))
    number_tags = hxl.TagPattern.parse_list(args.get('clean-num-tags%02d' % index, ''))
    return source.clean_data(whitespace=whitespace_tags, upper=upper_tags, lower=lower_tags, date=date_tags, number=number_tags)

def add_count_filter(source, args, index):
    """Add the hxlcount filter to the end of the pipeline."""
    tags = hxl.TagPattern.parse_list(args.get('count-tags%02d' % index, ''))
    count_spec = args.get('count-spec%02d' % index, None)
    if not count_spec:
        count_spec = 'Count#meta+count'
    aggregate_pattern = args.get('count-aggregate-tag%02d' % index)
    if aggregate_pattern:
        aggregate_pattern = hxl.TagPattern.parse(aggregate_pattern)
    else:
        aggregate_pattern = None
    return source.count(patterns=tags, aggregate_pattern=aggregate_pattern, count_spec=count_spec)

def add_column_filter(source, args, index):
    """Add the hxlcut filter to the end of the pipeline."""
    include_tags = hxl.TagPattern.parse_list(args.get('cut-include-tags%02d' % index, []))
    exclude_tags = hxl.TagPattern.parse_list(args.get('cut-exclude-tags%02d' % index, []))
    if include_tags:
        source = source.with_columns(include_tags)
    if exclude_tags:
        source = source.without_columns(exclude_tags)
    return source

def add_dedup_filter(source, args, index):
    return source.dedup(args.get('dedup-tags%02d' % index, []))

def add_explode_filter(source, args, index):
    return source.explode(
        args.get('explode-header-att%02d' % index, 'header'),
        args.get('explode-value-att%02d' % index, 'value')
    )

def add_merge_filter(source, args, index):
    """Add the hxlmerge filter to the end of the pipeline."""
    tags = hxl.TagPattern.parse_list(args.get('merge-tags%02d' % index, []))
    keys = hxl.TagPattern.parse_list(args.get('merge-keys%02d' % index, []))
    replace = (args.get('merge-replace%02d' % index) == 'on')
    overwrite = (args.get('merge-overwrite%02d' % index) == 'on')
    url = args.get('merge-url%02d' % index)
    merge_source = hxl.data(url)
    return source.merge_data(merge_source, keys=keys, tags=tags, replace=replace, overwrite=overwrite)

def add_rename_filter(source, args, index):
    """Add the hxlrename filter to the end of the pipeline."""
    oldtag = hxl.TagPattern.parse(args.get('rename-oldtag%02d' % index))
    tagspec = _parse_tagspec(args.get('rename-newtag%02d' % index))
    header = args.get('rename-header%02d' % index)
    column = hxl.Column.parse(tagspec, header=header)
    return source.rename_columns([(oldtag, column)])

def add_replace_filter(source, args, index):
    """Add the hxlreplace filter to the end of the pipeline."""
    original = args.get('replace-pattern%02d' % index)
    replacement = args.get('replace-value%02d' % index)
    tags = args.get('replace-tags%02d' % index)
    use_regex = args.get('replace-regex%02d' % index)
    return source.replace_data(original, replacement, tags, use_regex)

def add_replace_map_filter(source, args, index):
    """Add the hxlreplace filter to the end of the pipeline."""
    url = args.get('replace-map-url%02d' % index)
    return source.replace_data_map(hxl.data(url))

def add_row_filter(source, args, index):
    """Add the hxlselect filter to the end of the pipeline."""
    queries = []
    for subindex in range(1, 6):
        query = args.get('select-query%02d-%02d' % (index, subindex))
        if query:
            queries.append(query)
    reverse = (args.get('select-reverse%02d' % index) == 'on')
    if reverse:
        return source.without_rows(queries)
    else:
        return source.with_rows(queries)

def add_sort_filter(source, args, index):
    """Add the hxlsort filter to the end of the pipeline."""
    tags = hxl.TagPattern.parse_list(args.get('sort-tags%02d' % index, ''))
    reverse = (args.get('sort-reverse%02d' % index) == 'on')
    return source.sort(tags, reverse)

def _parse_tagspec(s):
    if not s:
        return None
    elif s[0] == '#':
        return s
    else:
        return '#' + s

# end
