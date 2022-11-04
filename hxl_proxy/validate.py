""" Validation support functions
Started May 2018 by David Megginson
License: Public Domain
"""

import hxl_proxy

from hxl_proxy import util

import hxl, logging, werkzeug


logger = logging.getLogger(__name__)
""" Python logger for this module """


@hxl_proxy.cache.memoize(unless=util.skip_cache_p)
def run_validation(url, content, content_hash, sheet_index, selector, schema_url, schema_content, schema_content_hash, schema_sheet_index, include_dataset, args={}):
    """ Do the actual validation run, using the arguments provided.
    Separated from the controller so that we can cache the result easiler.
    The *_hash arguments exist only to assist with caching.
    @returns: a validation report, suitable for returning as JSON.
    """

    # test for opening error conditions
    if (url is not None and content is not None):
        raise werkzeug.exceptions.BadRequest("Both 'url' and 'content' specified")
    if (url is None and content is None):
        raise werkzeug.exceptions.BadRequest("Require one of 'url' or 'content'")
    if (schema_url is not None and schema_content is not None):
        raise werkzeug.exceptions.BadRequest("Both 'schema_url' and 'schema_content' specified")

    # set up the main data
    if content:
        # TODO: stop using libhxl's make_input directly
        source = util.hxl_data(hxl.input.make_input(content, util.make_input_options(args)))
    else:
        source = util.hxl_data(url, util.make_input_options(args))

    # cache if we're including the dataset in the results (we have to run over it twice)
    if include_dataset:
        source = source.cache()

    # set up the schema (if present)
    schema_args = dict(args)
    schema_args['sheet'] = args.get('schema_sheet', args.get('schema_sheet', None))
    schema_args['selector'] = args.get('schema-selector', args.get('schema_selector', None))
    schema_args['timeout'] = args.get('schema-timeout', args.get('schema_timeout', None))
    schema_args['encoding'] = args.get('schema-encoding', args.get('schema_encoding', None))
    schema_args['expand_merged'] = args.get('schema-expand-merged', args.get('schema_expand_merged', None))

    if schema_content:
        schema_source = util.hxl_data(hxl.input.make_input(schema_content, util.make_input_options(schema_args)))
    elif schema_url:
        schema_source = util.hxl_data(schema_url, util.make_input_options(schema_args))
    else:
        schema_source = None

    # Validate the dataset
    report = hxl.validate(source, schema_source)

    # add the URLs if supplied
    if url:
        report['data_url'] = url
    if sheet_index is not None:
        report['data_sheet_index'] = sheet_index
    if schema_url:
        report['schema_url'] = schema_url
    if schema_args.get('sheet') is not None:
        report['schema_sheet_index'] = schema_args.get('sheet')

    # include the original dataset if requested
    if include_dataset:
        content = []
        content.append([util.no_none(column.header) for column in source.columns])
        content.append([util.no_none(column.display_tag) for column in source.columns])
        for row in source:
            content.append([util.no_none(value) for value in row.values])
        report['dataset'] = content

    return report

