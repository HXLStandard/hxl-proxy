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
from flask import Flask, url_for

# Main application object
app = Flask(__name__)

# Global config
app.config.from_object('hxl_proxy.default_config')

# If the environment variable HXL_PROXY_CONFIG exists, use it for local config
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')

#
# Utilities
#

def munge_url(url):
    """If a URL points to a tab in a Google Sheet, grab the CSV export."""
    result = re.match(r'https?://docs.google.com.*/spreadsheets/.*([0-9A-Za-z_-]{44}).*gid=([0-9]+)', str(url))
    if result:
        url = 'https://docs.google.com/spreadsheets/d/{0}/export?format=csv&gid={1}'.format(result.group(1), result.group(2))
    return url

def decode_string(s):
    """Decode a UTF-8 or Latin 1 string into Unicode."""
    if isinstance(s, six.string_types):
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

# Needed to register annotations in the controllers
import hxl_proxy.controllers

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

app.jinja_env.globals['urltag'] = (
    url_escape_tag
)

app.jinja_env.globals['unicode'] = (
    decode_string
)


# end
