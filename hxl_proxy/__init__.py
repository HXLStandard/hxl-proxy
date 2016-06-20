"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os

from flask import Flask, g, request
from flask_cache import Cache

import werkzeug.datastructures

# Main application object
app = Flask(__name__)
app.config.from_object('hxl_proxy.default_config')
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Set up cache
cache = Cache(app,config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': app.config.get('CACHE_DIR', '/tmp/'),
    'CACHE_THRESHOLD': app.config.get('CACHE_MAX_ITEMS', 1000),
    'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT_SECONDS', 3600)
})

# Needed to register annotations
import hxl_proxy.controllers

# end
