"""
Utility functions for hxl_proxy

Started 2015-02-18 by David Megginson
"""

import six
import re
import urllib
import datetime
import pickle
import re

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import url_for, request, flash, session, g

import hxl

from hxl_proxy import app
from hxl_proxy.profiles import Profile

CACHE_KEY_EXCLUDES = ['force']

def make_cache_key ():
    """Make a key for a caching request, based on the full path."""
    args = {}
    for name in request.args:
        if name not in CACHE_KEY_EXCLUDES:
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

def urlencode_utf8(params):
    if hasattr(params, 'items'):
        params = list(params.items())
    return '&'.join(
        (urllib.parse.quote_plus(k.encode('utf8'), safe='/') + '=' + urllib.parse.quote_plus(v.encode('utf8'), safe='/')
            for k, v in params if v))

def using_tagger_p(profile):
    for name in profile.args:
        if re.match(r'^tagger-', name):
            return True
    return False

PROFILE_OVERRIDES = ['url', 'schema_url']

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

    # Allow some values to be overridden from request parameters
    for key in PROFILE_OVERRIDES:
        if args.get(key):
            profile.overridden = True
            profile.args[key] = args.get(key)

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

def make_data_url(profile, key=None, facet=None, format=None):
    """Construct a data URL for a profile."""
    url = None
    if key:
        url = '/data/' + urllib.parse.quote(key)
        if facet:
            url += '/' + urllib.parse.quote(facet)
        elif format:
            if hasattr(profile, 'stub') and profile.stub:
                url += '/download/' + urllib.parse.quote(profile.stub) + '.' + urllib.parse.quote(format)
            else:
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

def re_search(regex, string):
    """Try matching a regular expression."""
    return re.search(regex, string)


#
# Declare Jinja2 filters and functions
#

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
)

app.jinja_env.filters['urlencode'] = (
    urllib.parse.quote_plus
)

app.jinja_env.filters['norm'] = (
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

