""" Validation support functions
Started May 2018 by David Megginson
License: Public Domain
"""

import hxl_proxy, hxl_proxy.util

import hxl, logging


logger = logging.getLogger(__name__)
""" Python logger for this module """


@hxl_proxy.cache.memoize(unless=hxl_proxy.util.skip_cache_p)
def run_validation(url, content, content_hash, sheet_index, selector, schema_url, schema_content, schema_content_hash, schema_sheet_index, include_dataset):
    """ Do the actual validation run, using the arguments provided.
    Separated from the controller so that we can cache the result easiler.
    The *_hash arguments exist only to assist with caching.
    @returns: a validation report, suitable for returning as JSON.
    """
    
    # test for opening error conditions
    if (url is not None and content is not None):
        raise requests.exceptions.BadRequest("Both 'url' and 'content' specified")
    if (url is None and content is None):
        raise requests.exceptions.BadRequest("Require one of 'url' or 'content'")
    if (schema_url is not None and schema_content is not None):
        raise requests.exceptions.BadRequest("Both 'schema_url' and 'schema_content' specified")

    # set up the main data
    if content:
        source = hxl.data(hxl.io.make_input(
            content, sheet_index=sheet_index, selector=selector
        ))
    else:
        source = hxl.data(
            url,
            sheet_index=sheet_index,
            http_headers={'User-Agent': 'hxl-proxy/validation'}
        )

    # cache if we're including the dataset in the results (we have to run over it twice)
    if include_dataset:
        source = source.cache()

    # set up the schema (if present)
    if schema_content:
        schema_source = hxl.data(hxl.io.make_input(
            schema_content,
            sheet_index=schema_sheet_index,
            selector=selector
        ))
    elif schema_url:
        schema_source = hxl.data(
            schema_url,
            sheet_index=schema_sheet_index,
            http_headers={'User-Agent': 'hxl-proxy/validation'}
        )
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
    if schema_sheet_index is not None:
        report['schema_sheet_index'] = schema_sheet_index

    # include the original dataset if requested
    if include_dataset:
        content = []
        content.append([hxl_proxy.util.no_none(column.header) for column in source.columns])
        content.append([hxl_proxy.util.no_none(column.display_tag) for column in source.columns])
        for row in source:
            content.append([hxl_proxy.util.no_none(value) for value in row.values])
        report['dataset'] = content

    return report

