"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

from flask import Flask

app = Flask(__name__)

import hxl_proxy.controllers
