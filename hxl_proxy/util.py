"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six
import re
import urllib
import datetime
import pickle

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import url_for, request, flash, session, g

from hxl.io import CSVInput, ExcelInput

from hxl_proxy import app
from hxl_proxy.profiles import Profile

EXCLUDES = ['force']

def make_cache_key ():
    """Make a key for a caching request, based on the full path."""
    args = {}
    for name in request.args:
        if name not in EXCLUDES:
            args[name] = request.args.get(name)
    return request.path + pickle.dumps(args).decode('latin1')

def skip_cache_p ():
    """Test if we should skip the cache."""
    return True if request.args.get('force') else False
    
def norm (s):
    """Normalise a string"""
    return s.strip().lower().replace(r'\s\s+', ' ')

def stream_template(template_name, **context):
    """From the flask docs - stream a long template result."""
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

def url_escape_tag(tag):
    if tag[0] == '#':
        tag = tag[1:]
    return tag

def urlencode_utf8(params):
    if hasattr(params, 'items'):
        params = params.items()
    return '&'.join(
        (urllib.parse.quote_plus(k.encode('utf8'), safe='/') + '=' + urllib.parse.quote_plus(v.encode('utf8'), safe='/')
            for k, v in params))

def get_profile(key, auth=False, args=None):
    """Load a profile or create from args."""
    if args is None:
        args = request.args
    if key:
        profile = g.profiles.get_profile(str(key))
        if not profile:
            raise NotFound("No saved profile for " + key)
        if auth and not check_auth(profile):
            raise Forbidden("Wrong or missing password.")
    else:
        profile = Profile(args)
    return profile


def check_auth(profile):
    """Check authorisation."""
    passhash = session.get('passhash')
    if passhash and profile.passhash == passhash:
        return True
    password = request.form.get('password')
    if password:
        if profile.check_password(password):
            session['passhash'] = profile.passhash
            return True
        else:
            session['passhash'] = None
            flash("Wrong password")
    return False

def add_args(extra_args):
    """Add GET parameters."""
    args = {}
    for key in request.args:
        args[key] = request.args[key]
    for key in extra_args:
        if extra_args[key]:
            # add keys with truthy values
            args[key] = extra_args[key]
        else:
            # remove keys with non-truthy values
            del args[key]
    return '?' + urlencode_utf8(args)

def request_args_form():
    """Return hidden form fields for GET parameters."""
    fields = ""
    for key in request.args:
        if request.args[key]:
            fields = "<input type=\"hidden\" name=\"{}\" value=\"{}\" />\n".format(key, request.args[key])
    return fields

def make_data_url(profile, key=None, facet=None, format=None):
    """Construct a data URL for a profile."""
    url = None
    if key:
        url = '/data/' + urllib.parse.quote(key)
        if facet:
            url += '/' + urllib.parse.quote(facet)
        elif format:
            url += '.' + urllib.parse.quote(format)
    else:
        url = '/data'
        if format:
            url += '.' + urllib.parse.quote(format)
        elif facet:
            url += '/' + urllib.parse.quote(facet)
        url += '?' + urlencode_utf8(profile.args)

    return url

def severity_class(severity):
    """Return a CSS class for a validation error severity"""
    if severity == 'error':
        return 'severity_error'
    elif severity == 'warning':
        return 'severity_warning'
    else:
        return 'severity_info'

def display_date(date_string):
    """Reformat an ISO datetime into something readable."""
    return datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f').strftime('%c')

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
)

app.jinja_env.filters['urlencode'] = (
    urllib.parse.quote_plus
)

app.jinja_env.filters['display_date'] = (
    display_date
)

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

app.jinja_env.globals['urltag'] = (
    url_escape_tag
)

app.jinja_env.globals['add_args'] = (
    add_args
)

app.jinja_env.globals['request_args_form'] = (
    request_args_form
)

app.jinja_env.globals['data_url'] = (
    make_data_url
)

app.jinja_env.globals['severity_class'] = (
    severity_class
)

