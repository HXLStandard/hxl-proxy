"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six, hashlib, json, re, time, random, base64, urllib, datetime, pickle, iati2hxl.generator, requests

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import url_for, request, flash, session, g

import hxl

import hxl_proxy
from hxl_proxy import app

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

            
RECIPE_OVERRIDES = ['url', 'schema_url', 'filter_tag', 'filter_value', 'count_tag', 'label_tag', 'value_tag', 'type']

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

    # Allow some values to be overridden from request parameters
    for key in RECIPE_OVERRIDES:
        if args.get(key):
            recipe['overridden'] = True
            recipe['args'][key] = args.get(key)

    return recipe


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

def data_url_for(endpoint, recipe={}, format=None, flavour=None, recipe_id=None, cloned=False):
    """Generate a URL relative to the subpath (etc)
    Wrapper around flask.url_for
    """
    if not recipe_id:
        recipe_id = recipe.get('recipe_id')
    args = make_args(recipe, format=format, flavour=flavour, recipe_id=recipe_id, cloned=cloned)
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
    if hasattr(e, 'response'):
        json_error['source_status_code'] = e.response.status_code
        json_error['source_url'] = e.response.url
        json_error['source_message'] = e.response.text
    return json.dumps(json_error, indent=4, sort_keys=True)

def parse_validation_errors(errors, data_url, schema_url):
    """Parse libhxl validation errors into a JSON-like data structure.
    Format: https://docs.google.com/document/d/1PXVtK1YWwZEtAUOtImDSBudE3YYvzEXLEU2rFc6XC88/edit?usp=sharing
    @param errors: a list of L{hxl.validation.HXLValidationError} objects
    @param data_url: the URL of the dataset being validated
    @param schema_url: the URL of the HXL schema in use
    @returns: a data structure listing the errors, suitable for JSON rendition
    """

    # top-level report
    error_report = {
        "validator": "HXL Proxy",
        "timestamp": datetime.datetime.now().isoformat(),
        "data_url": data_url,
        "schema_url": schema_url,
        "stats": {
            "info": 0,
            "warning": 0,
            "error": 0,
            "total": 0
        },
        "issues": [],
    }

    # individual issues inside the report
    for key in errors:
        model = errors[key][0]
        if model.row is not None and model.column is not None:
            scope = 'cell'
        elif model.row is not None:
            scope = 'row'
        elif model.column is not None:
            scope = 'column'
        else:
            scope = 'dataset'
        error_report['stats']['total'] += len(errors[key])
        error_report['stats'][model.rule.severity] += len(errors[key])

        description = model.rule.description
        if not description:
            description = model.message
        
        issue = {
            "rule_id": key,
            "tag_pattern": str(model.rule.tag_pattern),
            "description": description,
            "severity": model.rule.severity,
            "location_count": len(errors[key]),
            "scope": scope,
            "locations": []
        }

        # individual locations inside an issue
        for error in errors[key]:
            location = {}
            if error.row is not None:
                if error.row.row_number is not None:
                    location['row'] = error.row.row_number
                if error.row.source_row_number is not None:
                    location['source_row'] = error.row.source_row_number
            if error.column is not None:
                if error.column.column_number is not None:
                    location['col'] = error.column.column_number
                if error.column.display_tag is not None:
                    location['hashtag'] = error.column.display_tag
            if error.value is not None:
                location['error_value'] = error.value
            if error.suggested_value is not None:
                location['suggested_value'] = error.suggested_value
            issue['locations'].append(location)

        error_report['issues'].append(issue)

    return error_report
    

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


#
# Declare Jinja2 filters and functions
#

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
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

