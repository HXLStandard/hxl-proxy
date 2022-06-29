"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os

import requests_cache
from flask import Flask, g, request
from flask_caching import Cache

import werkzeug.datastructures
from . import reverse_proxied

__version__="1.25"
"""Module version number
See https://www.python.org/dev/peps/pep-0396/
"""

# Main application object
app = Flask(__name__)

# Handle subpaths
app.wsgi_app = reverse_proxied.ReverseProxied(app.wsgi_app)

# Config
app.config.from_object('hxl_proxy.default_config')
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Set up output cache
cache = Cache(app, config=app.config.get('CACHE_CONFIG'))

# (Setting up requests cache dynamically in controllers.py)

# Needed to register annotations
import hxl_proxy.controllers

# end
