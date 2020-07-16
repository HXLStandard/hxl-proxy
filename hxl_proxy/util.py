""" Utility functions for hxl_proxy
TODO: also contains template output functions, which need to move to their own module.
Started 2015-02-18 by David Megginson
License: Public Domain
"""

import hxl_proxy

import flask, hashlib, hxl, json, logging, pickle, random, re, requests, time, urllib


# Logger for this module
logger = logging.getLogger(__name__)



########################################################################
# Utility functions for caching
########################################################################

def make_cache_key (path = None, args_in=None):
    """Make a key for a caching request, based on the full path.
    The cache key depends on the path and the GET parameters,
    excluding &force (so that we can cache the request by using
    the force parameter).
    @param path: the HTTP path, or None to use the current request
    @param args_in: the GET params, or None to use the current request
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
    The HTTP &force parameter requests cache skipping.
    Note that this function will not detect the &force
    parameter inside a saved recipe; for now, it has to
    be specified as a GET param.
    @returns: True if we don't want to cache
    """
    return True if flask.request.args.get('force') else False


########################################################################
# Not yet classified
########################################################################

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
            

def check_verify_ssl(args):
    """Check parameters to see if we need to verify SSL connections."""
    if args.get('skip_verify_ssl') == 'on':
        return False
    elif args.get('verify_ssl') == 'off' or args.get('verify') == 'off': # deprecated parameters
        return False
    else:
        return True


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

