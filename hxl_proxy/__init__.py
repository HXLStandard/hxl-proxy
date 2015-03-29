"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import six
import re
import os
import base64
import urllib

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound
from flask import Flask, url_for, request, flash, session

from hxl_proxy.profiles import Profile, ProfileManager
from hxl.io import CSVInput, ExcelInput

# Main application object
app = Flask(__name__)
app.secret_key = app.config['SECRET_KEY']

# Global config
app.config.from_object('hxl_proxy.default_config')

# If the environment variable HXL_PROXY_CONFIG exists, use it for local config
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')

#
# Global profile manager
#
profiles = ProfileManager(app.config['PROFILE_FILE'])

#
# Utilities
#


def munge_url(url):
    """If a URL points to a tab in a Google Sheet, grab the CSV export."""

    result = re.match(r'https?://docs.google.com.*/spreadsheets/.*([0-9A-Za-z_-]{44}).*gid=([0-9]+)', str(url))
    if result:
        return 'https://docs.google.com/spreadsheets/d/{0}/export?format=csv&gid={1}'.format(result.group(1), result.group(2))

    # FIXME shouldn't need two patterns, but it's defeating me right now
    result = re.match(r'https?://docs.google.com.*/spreadsheets/.*([0-9A-Za-z_-]{44})', str(url))
    if result:
            url = 'https://docs.google.com/spreadsheets/d/{0}/export?format=csv'.format(result.group(1))

    # Return the original URL
    return url

def make_input(url):
    """Create an input object for a URL."""
    if re.match(r'^https?://.+$', url):
        if re.match(r'.*\.xlsx?$', url):
            return ExcelInput(url)
        else:
            return CSVInput(url)
    else:
        raise Forbidden('Only http and https URLs supported')

def decode_string(s):
    """Decode a UTF-8 or Latin 1 string into Unicode."""
    if not s:
        return ''
    elif isinstance(s, six.string_types):
        try:
            return s.decode('utf8')
        except:
            return s.decode('latin1')
    else:
        return s

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
        (urllib.quote_plus(k.encode('utf8'), safe='/') + '=' + urllib.quote_plus(v.encode('utf8'), safe='/')
            for k, v in params))

def get_profile(key, auth=False, args=None):
    """Load a profile or create from args."""
    if args is None:
        args = request.args
    if key:
        profile = profiles.get_profile(str(key))
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

def make_data_url(profile, key=None, facet=None, format=None):
    """Construct a data URL for a profile."""
    url = None
    if key:
        url = '/data/' + urllib.quote(key)
        if facet:
            url += '/' + urllib.quote(facet)
        elif format:
            url += '.' + urllib.quote(format)
    else:
        url = '/data'
        if format:
            url += '.' + urllib.quote(format)
        elif facet:
            url += '/' + urllib.quote(facet)
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


# Needed to register annotations in the controllers
import hxl_proxy.controllers

app.jinja_env.filters['nonone'] = (
    lambda s: '' if s is None else s
)

app.jinja_env.filters['urlencode'] = (
    urllib.quote_plus
)

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

app.jinja_env.globals['urltag'] = (
    url_escape_tag
)

app.jinja_env.globals['unicode'] = (
    decode_string
)

app.jinja_env.globals['data_url'] = (
    make_data_url
)

app.jinja_env.globals['severity_class'] = (
    severity_class
)

# end
