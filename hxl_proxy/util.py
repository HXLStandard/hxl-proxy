"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six, hashlib, time, random, base64
import re
import urllib
import datetime
import pickle
import re

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
    return hxl.common.normalise_string(s)

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
            raise Forbidden("Wrong or missing password.")
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
    return hashlib.md5(s.encode('utf-8')).digest()

def gen_recipe_id():
    """
    Generate a pseudo-random, 6-character hash for use as a recipe_id.
    """
    salt = str(time.time() * random.random())
    encoded_hash = base64.urlsafe_b64encode(make_md5(salt))
    return encoded_hash[:6].decode('ascii')

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
            del args[key]
    return '?' + urlencode_utf8(args)

def make_data_url(recipe={}, facet=None, format=None, recipe_id=None):
    """Construct a data URL for a recipe."""
    url = None
    if not recipe_id:
        recipe_id = recipe.get('recipe_id')
    if recipe_id and facet != 'clone':
        url = '/data/' + urlquote(recipe_id)
        if facet:
            url += '/' + urlquote(facet)
        elif format:
            if recipe.get('stub'):
                url += '/download/' + urlquote(recipe['stub']) + '.' + urlquote(format)
            else:
                url += '.' + urlquote(format)
    else:
        url = '/data'
        if format:
            if recipe.get('stub'):
                url += '/download/' + urlquote(recipe['stub']) + '.' + urlquote(format)
            else:
                url += '.' + urlquote(format)
        elif facet and facet != 'clone':
            url += '/' + urlquote(facet)
        if recipe.get('args'):
            url += '?' + urlencode_utf8(recipe['args'])

    return url

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


#
# Declare Jinja2 filters and functions
#

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
)

app.jinja_env.filters['urlquote'] = (
    urlquote
)

app.jinja_env.filters['strnorm'] = (
    hxl.common.normalise_string
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

app.jinja_env.globals['data_url'] = (
    make_data_url
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

