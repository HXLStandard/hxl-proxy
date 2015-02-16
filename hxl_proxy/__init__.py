"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os
from flask import Flask

# Main application object
app = Flask(__name__)

# Global config
app.config.from_object('hxl_proxy.default_config')

# If the environment variable HXL_PROXY_CONFIG exists, use it for local config
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')

# Needed to register annotations in the controllers
import hxl_proxy.controllers

# end
