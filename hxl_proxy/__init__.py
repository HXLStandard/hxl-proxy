"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os

from flask import Flask, g, request

import werkzeug.datastructures

from hxl_proxy.profiles import ProfileManager

# Main application object
app = Flask(__name__)
app.config.from_object('hxl_proxy.default_config')
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')

@app.before_request
def before_request():
    """Code to run immediately before the request"""
    app.secret_key = app.config['SECRET_KEY']
    request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
    g.profiles = ProfileManager(app.config['PROFILE_FILE'])

# Needed to register annotations in the controllers
import hxl_proxy.controllers

# end
