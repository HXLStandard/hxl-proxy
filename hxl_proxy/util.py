""" Utility functions for hxl_proxy
TODO: also contains template output functions, which need to move to their own module.
Started 2015-02-18 by David Megginson
License: Public Domain
"""

from ast import Try
import hxl_proxy

import flask, hashlib, hxl, json, logging, pickle, random, re, requests, time, urllib
from hxl_proxy import caching, exceptions

from urllib.parse import urlparse

# Logger for this module
logger = logging.getLogger(__name__)

from structlog import contextvars
from functools import wraps
import uuid
from hxl.util import logup

def structlogged(f):
    """ decorator to add essential fields on json logs
    """
    @wraps(f)
    def decorated_structlog_binder(*args, **kwargs):
        contextvars.clear_contextvars()
        contextvars.bind_contextvars(
            user_agent=flask.request.headers.get('User-Agent', "UNKNOWN"),
            peer_ip=flask.request.headers.get('X-Real-IP', flask.request.remote_addr),
            request=flask.request.url,
            request_id=str(uuid.uuid4()),
        )
        return f(*args, **kwargs)
    return decorated_structlog_binder


########################################################################
# Utility functions for caching
########################################################################

def make_cache_key (path = None, args_in=None):
    """ Make a key for a caching request, based on the full path.

    The cache key depends on the path and the GET parameters,
    excluding &force (so that we can cache the request by using
    the force parameter).

    Args:
        path(str): the HTTP path, or None to use the current request
        args_in(dict): the GET params, or None to use the current request

    Returns:
        str: the cache key string

    """
    CACHE_KEY_EXCLUDES = ['force']

    # Fill in default
    if path is None:
        path = flask.request.path
    if args_in is None:
        args_in = flask.request.args

    # Construct the args for the cache key
    args_out = {}
    for name in sorted(args_in.keys()):
        if name not in CACHE_KEY_EXCLUDES:
            args_out[name] = args_in[name]

    # Use a pickled version path and args for the cache key
    return path + pickle.dumps(args_out).decode('latin1')


def skip_cache_p ():
    """ Determine whether we are skipping the cache.

    The HTTP &force parameter requests cache skipping.  Note that this
    function will not detect the &force parameter inside a saved
    recipe; for now, it has to be specified as a GET param.

    Returns:
        bool: True if we don't want to cache

    """
    return True if flask.request.args.get('force') else False



########################################################################
# Input wrappers and options
########################################################################

def hxl_data (raw_source, input_options=None):
    """ Wrapper for hxl.data() to implement a domain-based allow list.

    If the raw_source is a string (i.e. URL), check that the base
    domain is in the allow list. If the allow list is empty, assume
    testing and allow any domain.

    Args:
        raw_source: a HXL data provider, file object, array, or string (representing a URL)
        input_options (hxl.input.InputOptions): input options for reading a dataset

    Returns:
        hxl.model.Dataset: a HXL dataset object

    Raises:
        hxl_proxy.exceptions.DomainNotAllowedError: if the domain for a URL is not in the allow list

    """
    # don't catch exceptions here; see controllers.py for general exception handling
    check_allowed_domain(raw_source)
    return hxl.data(raw_source, input_options)


def hxl_make_input (raw_source, input_options=None):
    """ Wrapper for hxl.make_input() to implement a domain-based allow list.

    If the raw_source is a string (i.e. URL), check that the base
    domain is in the allow list. If the allow list is empty, assume
    testing and allow any domain.

    Args:
        raw_source: a HXL data provider, file object, array, or string (representing a URL)
        input_options(hxl.input.InputOptions): input options for reading a dataset

    Returns:
        hxl.input.AbstractInput: a row-by-row input object (pre-HXL-processing)

    Raises:
        hxl_proxy.exceptions.DomainNotAllowedError: if the domain for a URL is not in the allow list

    """
    # don't catch exceptions here; see controllers.py for general exception handling
    check_allowed_domain(raw_source)
    return hxl.make_input(raw_source, input_options)


def check_allowed_domain (raw_source):
    """ Raise an exception if raw_source is a URL and its base domain is not in the allow list.

    Args:
        raw_source: a HXL data source, possibly a string representing a URL

    Raises:
        hxl_proxy.exceptions.DomainNotAllowedException: if the base domain for a URL is not in the allow list.

    """

    if isinstance(raw_source, str) and not is_allowed_domain(raw_source):
        logup("Domain not in allow list", {'raw_source': raw_source}, "error")
        logger.error("Domain not in allow list: %s", raw_source)
        raise exceptions.DomainNotAllowedError(
            "The HXL Proxy does not allow data from this domain.\n" +
            "If your data is on HDX, you can use the dataset or resource\n" +
            "URL with the HXL Proxy. Otherwise, please send requests to\n"
            "allow new humanitarian-data domains to hdx@un.org.\n\n" +
            raw_source
        )


def is_allowed_domain (raw_source):
    """ Check if raw_source is a URL and its base domain is in the allow list.

    Args:
        raw_source: a HXL data source, possibly a string representing a URL

    Returns:
        bool: True if the url is in the allow list, or the list is empty

    """
    hostnames = hxl_proxy.app.config.get('ALLOWED_DOMAINS_LIST', [])

    # if allowed list is empty just wave in for eveybody. test mode eh?
    # also, if it's not a string (i.e. URL), proceed
    if len(hostnames) == 0 or not isinstance(raw_source, str):
        return True

    url=urlparse(raw_source)
    # it is a hostname match?
    if url.netloc in hostnames:
        return True
    # maybe an allowed domain child?
    domains = tuple(['.{}'.format(d) for d in hostnames])
    if url.netloc.endswith(domains):
        return True
    # sorry, call us
    return False


def make_input_options (args):
    """ Create an InputOptions object from the parameters provided

    Ensure that allow_local is always false. Allow both "-" and "_" between words.

    Args:
        args(dict): an dictionary of command-line params

    Returns:
        hxl.input.InputOptions: the input options extracted from the params

    """

    # set the user agent, to help with analytics
    http_headers = args.get("http-headers", args.get("http_headers", {}))
    http_headers['User-Agent'] = 'hxl-proxy'

    # add an authorisation token, if needed
    if args.get('authorization_token'):
        http_headers['Authorization'] = args['authorization_token']

    # set up the sheet index
    sheet_index = args.get("sheet")
    if sheet_index is not None:
        try:
            sheet_index = int(sheet_index)
        except:
            logup('Invalid sheet index; defaulting to 0', {sheet_index: sheet_index}, level='error')
            logger.error("Invalid sheet index \"%s\"; defaulting to 0", sheet_index)
            sheet_index = 0

    # get the max timeout from configuration, defaulting to 30 seconds
    max_timeout = hxl_proxy.app.config.get("MAX_REQUEST_TIMEOUT", 30.0)
    try:
        timeout = min(float(args.get("timeout")), max_timeout)
    except TypeError:
        timeout = max_timeout

    return hxl.input.InputOptions(
        allow_local = False,
        sheet_index = sheet_index,
        timeout = timeout,
        http_headers = http_headers,
        selector = args.get("selector", None),
        encoding = args.get("encoding", None),
        expand_merged = args.get("expand-merged", args.get("expand_merged", False)),
        scan_ckan_resources = args.get("scan-ckan-resources", args.get("scan_ckan_resources", False)),
    )



########################################################################
# Not yet classified
########################################################################

def check_markup(s):
    """ Check if text contains markup or URLs
    """
    if re.search(r'(<[a-zA-Z]|>|href|https?:|\.com|\[url=)', s):
        return True
    else:
        return False

def forbid_markup(s, field_name=None):
    """ Raise an exception if markup or URLs appear in a string
    Otherwise, return the string.
    """
    if check_markup(s):
        raise hxl_proxy.exceptions.ForbiddenContentException(s, "markup and URLs not allowed", field_name)
    else:
        return s

def clean_tagger_mappings(headers, recipe):
    """ Create a clean list of hashtag mappings for the tagger form
    """
    existing_mappings = dict()
    mappings = list()
    headers_seen = set()

    # Existing mappings are in tagger-nn-header and tagger-nn-tag
    for arg in recipe.args:
        result = re.match(r'^tagger-(\d{2})-header', arg)
        if result:
            n = result.group(1)
            header = hxl.datatypes.normalise_string(recipe.args[arg])
            tagspec = recipe.args.get("tagger-" + n + "-tag")
            if header and tagspec and header not in existing_mappings:
                existing_mappings[header] = tagspec

    # Do the headers in document order
    for header in headers:
        header = hxl.datatypes.normalise_string(header)
        if header and header not in headers_seen:
            mappings.append([header, existing_mappings.get(header, "")])
            headers_seen.add(header)

    # Add any extra mappings back in
    for header in existing_mappings:
        if header not in headers_seen:
            mappings.append([header, existing_mappings[header]])
            headers_seen.add(header)

    return mappings


def make_file_hash(stream):
    """Calculate a hash in chunks from a stream.
    Must be random-access. Resets to position 0 before and after read.
    @param stream: a bytes stream to read
    @returns: an MD5 hash
    """
    file_hash = hashlib.md5()
    stream.seek(0)
    while True:
        s = stream.read(8192)
        if len(s) < 1:
            break
        else:
            file_hash.update(s)
    stream.seek(0)
    return file_hash.hexdigest()

def make_md5(s):
    """Return an MD5 hash for a string."""
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def make_args(recipe=None, format=None, flavour=None, recipe_id=None, cloned=False):
    """Construct args for url_for."""
    args = {}
    if recipe and recipe.args and (cloned or not recipe_id):
        for key in recipe.args:
            args[key] = recipe.args[key]
    if format:
        args['format'] = format
        args['flavour'] = flavour
        stub = recipe.stub
        if stub:
            args['stub'] = re.sub("[^a-zA-Z0-9_-]+", '_', stub) # Flask's url_for doesn't escape !!!
    if not recipe_id and recipe:
        recipe_id = recipe.recipe_id
    if recipe_id and not cloned:
        args['recipe_id'] = recipe_id
    return args

def make_json_error(e, status):
    """Convert an exception to a string containing a JSON-formatted error
    @param e: the exception to convert
    @returns: a string containing JSON markup
    """
    json_error = {
        'error': e.__class__.__name__,
        'status': status
    }
    if hasattr(e, 'message'):
        json_error['message'] = e.message
    else:
        json_error['message'] = str(e)
    if hasattr(e, 'human'):
        json_error['human_message'] = e.human
    if hasattr(e, 'errno') and (e.errno is not None):
        json_error['errno'] = e.errno
    if hasattr(e, 'response') and e.response:
        json_error['source_status_code'] = e.response.status_code
        json_error['source_url'] = e.response.url
        json_error['source_message'] = e.response.text
    return json.dumps(json_error, indent=4, sort_keys=True)


########################################################################
# Output helper functions for templates
########################################################################

def no_none(s):
    """ Template helper: prevent None from appearing in output.
    @param s: the input value
    @returns: a string version of the value, or "" if None
    """
    return str(s) if s is not None else ''

def stream_template(template_name, **context):
    """From the flask docs - stream a long template result."""
    hxl_proxy.app.update_template_context(context)
    t = hxl_proxy.app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

def urlquote(value):
    return urllib.parse.quote_plus(value, safe='/')

def spreadsheet_col_num_to_name(num):
    """Convert a column index to spreadsheet letters.
    Adapted from http://asyoulook.com/computers%20&%20internet/python-convert-spreadsheet-number-to-column-letter/659618
    """
    letters = ''
    num += 1
    while num:
        mod = num % 26
        letters += chr(mod + 64)
        num = num // 26
    return ''.join(reversed(letters))

def using_tagger_p(recipe):
    for name in recipe.args:
        if re.match(r'^tagger-', name):
            return True
    return False

def add_args(extra_args):
    """Add GET parameters."""
    args = {key: flask.request.args.get(key) for key in flask.request.args}
    for key in extra_args:
        if extra_args[key]:
            # add keys with truthy values
            args[key] = extra_args[key]
        else:
            # remove keys with non-truthy values
            if args.get(key):
                del args[key]
    return '?' + urlencode_utf8(args)

def data_url_for(endpoint, recipe=None, format=None, flavour=None, recipe_id=None, cloned=False, extras={}):
    """Generate a URL relative to the subpath (etc)
    Wrapper around flask.url_for
    """
    if not recipe_id and recipe:
        recipe_id = recipe.recipe_id
    args = make_args(recipe, format=format, flavour=flavour, recipe_id=recipe_id, cloned=cloned)
    if extras:
        # add in any extra GET params requested
        for key in extras:
            args[key] = extras[key]
    if recipe_id and not cloned:
        args['recipe_id'] = recipe_id
    return flask.url_for(endpoint, **args)

def severity_class(severity):
    """Return a CSS class for a validation error severity"""
    if severity == 'error':
        return 'severity_error'
    elif severity == 'warning':
        return 'severity_warning'
    else:
        return 'severity_info'

def re_search(regex, string):
    """Try matching a regular expression."""
    return re.search(regex, string)

def search_by_attributes(attributes, columns):
    result_columns = []
    for column in columns:
        for attribute in attributes:
            if attribute in column.attributes:
                result_columns.append(column)
                break
    return result_columns

def get_gravatar(email, size=40):
    import hashlib
    hash = hashlib.md5(email.encode('utf8').lower()).hexdigest()
    url = "http://www.gravatar.com/avatar/{hash}?s={size}".format(
        hash=hash,
        size=size
    )
    return url


def urlencode_utf8(params):
    if hasattr(params, 'items'):
        params = list(params.items())
    return '&'.join(
            urlquote(k) + '=' + urlquote(v) for k, v in params if v
    )

#
# Declare Jinja2 filters and functions
#

hxl_proxy.app.jinja_env.filters['nonone'] = (
    no_none
)

hxl_proxy.app.jinja_env.filters['urlquote'] = (
    urlquote
)

hxl_proxy.app.jinja_env.filters['spreadsheet_col'] = (
    spreadsheet_col_num_to_name
)

hxl_proxy.app.jinja_env.filters['strnorm'] = (
    hxl.datatypes.normalise_string
)

hxl_proxy.app.jinja_env.globals['static'] = (
    lambda filename: flask.url_for('static', filename=filename)
)

hxl_proxy.app.jinja_env.globals['using_tagger_p'] = (
    using_tagger_p
)

hxl_proxy.app.jinja_env.globals['add_args'] = (
    add_args
)

hxl_proxy.app.jinja_env.globals['data_url_for'] = (
    data_url_for
)

hxl_proxy.app.jinja_env.globals['severity_class'] = (
    severity_class
)

hxl_proxy.app.jinja_env.globals['re_search'] = (
    re_search
)

hxl_proxy.app.jinja_env.globals['search_by_attributes'] = (
    search_by_attributes
)

hxl_proxy.app.jinja_env.globals['get_gravatar'] = (
    get_gravatar
)

