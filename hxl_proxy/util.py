"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six, hashlib, json, re, time, random, base64, urllib, datetime, pickle, iati2hxl.generator, requests, logging

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import url_for, request, flash, session, g

from . import cache

import hxl

import hxl_proxy
from hxl_proxy import app

logger = logging.getLogger(__name__)

CACHE_KEY_EXCLUDES = ['force']

def make_cache_key (path = None, args_in=None):
    """Make a key for a caching request, based on the full path."""
    if path is None:
        path = request.path
    if args_in is None:
        args_in = request.args
    args_out = {}
    for name in args_in:
        if name not in CACHE_KEY_EXCLUDES:
            args_out[name] = args_in[name]
    return path + pickle.dumps(args_out).decode('latin1')

def skip_cache_p ():
    """Test if we should skip the cache."""
    return True if request.args.get('force') else False
    
def no_none(s):
    return s if s is not None else ''
    
def strnorm (s):
    """Normalise a string"""
    return hxl.datatypes.normalise_string(s)

def stream_template(template_name, **context):
    """From the flask docs - stream a long template result."""
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

def urlquote(value):
    return urllib.parse.quote_plus(value, safe='/')

def urlencode_utf8(params):
    if hasattr(params, 'items'):
        params = list(params.items())
    return '&'.join(
            urlquote(k) + '=' + urlquote(v) for k, v in params if v
    )

def using_tagger_p(recipe):
    for name in recipe['args']:
        if re.match(r'^tagger-', name):
            return True
    return False

def get_gravatar(email, size=40):
    import hashlib
    hash = hashlib.md5(email.encode('utf8').lower()).hexdigest()
    url = "http://www.gravatar.com/avatar/{hash}?s={size}".format(
        hash=hash,
        size=size
    )
    return url


def check_verify_ssl(args):
    """Check parameters to see if we need to verify SSL connections."""
    if args.get('skip_verify_ssl') == 'on':
        return False
    elif args.get('verify_ssl') == 'off' or args.get('verify') == 'off': # deprecated parameters
        return False
    else:
        return True


def gen_iati_hxl(url):
    """Generate HXL CSV from IATI"""
    import csv

    class TextOut:
        """Simple string output source to capture CSV"""
        def __init__(self):
            self.data = ''
        def write(self, s):
            self.data += s
        def get(self):
            data = self.data
            self.data = ''
            return data

    output = TextOut()
    writer = csv.writer(output)
    with requests.get(url, stream=True) as response:
        response.raw.decode_content = True
        for row in iati2hxl.generator.genhxl(response.raw):
            writer.writerow(row)
            yield output.get()

            
RECIPE_OVERRIDES = ['url', 'schema_url']

def get_recipe(recipe_id=None, auth=False, args=None):
    """Load a recipe or create from args."""

    if args is None:
        args = request.args

    if recipe_id:
        recipe = hxl_proxy.dao.recipes.read(str(recipe_id))
        if not recipe:
            raise NotFound("No saved recipe for " + recipe_id)
        if auth and not check_auth(recipe):
            raise Unauthorized("Wrong or missing password.")
    else:
        recipe = {'args': {key: args.get(key) for key in args}}
        if args.get('stub'):
            recipe['stub'] = args.get('stub')

    # No overrides with a private authorization token!!!!!!!
    # (potential security hole)
    if args.get('authorization_token') is None:
        # Allow some values to be overridden from request parameters
        for key in RECIPE_OVERRIDES:
            if args.get(key):
                recipe['overridden'] = True
                recipe['args'][key] = args.get(key)

    return recipe

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

def gen_recipe_id():
    """
    Generate a pseudo-random, 6-character hash for use as a recipe_id.
    """
    salt = str(time.time() * random.random())
    encoded_hash = make_md5(salt)
    return encoded_hash[:6]

def make_recipe_id():
    """Make a unique recipe_id for a saved recipe."""
    recipe_id = gen_recipe_id()
    while hxl_proxy.dao.recipes.read(recipe_id):
        recipe_id = gen_recipe_id()
    return recipe_id

def check_auth(recipe, password=None):
    """Check authorisation."""
    passhash = recipe.get('passhash')
    if passhash:
        if password:
            session_passhash = make_md5(password)
            session['passhash'] = session_passhash
        else:
            session_passhash = session.get('passhash')
        if passhash == session_passhash:
            return True
        else:
            session['passhash'] = None
            flash("Wrong password")
            return False
    else:
        return True

def add_args(extra_args):
    """Add GET parameters."""
    args = {key: request.args.get(key) for key in request.args}
    for key in extra_args:
        if extra_args[key]:
            # add keys with truthy values
            args[key] = extra_args[key]
        else:
            # remove keys with non-truthy values
            if args.get(key):
                del args[key]
    return '?' + urlencode_utf8(args)

def make_args(recipe={}, format=None, flavour=None, recipe_id=None, cloned=False):
    """Construct args for url_for."""
    args = {}
    if recipe.get('args') and (cloned or not recipe_id):
        args = dict.copy(recipe['args'])
    if format:
        args['format'] = format
        args['flavour'] = flavour
        stub = recipe.get('stub')
        if stub:
            args['stub'] = stub
    if not recipe_id:
        recipe_id = recipe.get('recipe_id')
    if recipe_id and not cloned:
        args['recipe_id'] = recipe_id
    return args

def data_url_for(endpoint, recipe={}, format=None, flavour=None, recipe_id=None, cloned=False, extras={}):
    """Generate a URL relative to the subpath (etc)
    Wrapper around flask.url_for
    """
    if not recipe_id:
        recipe_id = recipe.get('recipe_id')
    args = make_args(recipe, format=format, flavour=flavour, recipe_id=recipe_id, cloned=cloned)
    if extras:
        # add in any extra GET params requested
        for key in extras:
            args[key] = extras[key]
    if recipe_id and not cloned:
        args['recipe_id'] = recipe_id
    return url_for(endpoint, **args)

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

@cache.memoize(unless=skip_cache_p)
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
        content.append([no_none(column.header) for column in source.columns])
        content.append([no_none(column.display_tag) for column in source.columns])
        for row in source:
            content.append([no_none(value) for value in row.values])
        report['dataset'] = content

    return report


#
# Declare Jinja2 filters and functions
#

app.jinja_env.filters['nonone'] = (
    no_none
)

app.jinja_env.filters['urlquote'] = (
    urlquote
)

app.jinja_env.filters['spreadsheet_col'] = (
    spreadsheet_col_num_to_name
)

app.jinja_env.filters['strnorm'] = (
    hxl.datatypes.normalise_string
)

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

app.jinja_env.globals['using_tagger_p'] = (
    using_tagger_p
)

app.jinja_env.globals['add_args'] = (
    add_args
)

app.jinja_env.globals['data_url_for'] = (
    data_url_for
)

app.jinja_env.globals['severity_class'] = (
    severity_class
)

app.jinja_env.globals['re_search'] = (
    re_search
)

app.jinja_env.globals['search_by_attributes'] = (
    search_by_attributes
)

app.jinja_env.globals['get_gravatar'] = (
    get_gravatar
)

