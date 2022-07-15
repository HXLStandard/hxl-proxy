"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org

"""

__version__="1.25.2"
"""Module version number
See https://www.python.org/dev/peps/pep-0396/

"""


#
# Set up logging before any other imports, to get correct format in server logs
#
import logging, logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

logger = logging.getLogger(__name__)
""" Python logger for this module """


#
# Continue with other imports
#
import flask, flask_caching, os, requests_cache, werkzeug.datastructures
from . import reverse_proxied


#
# Create the main Flask application object
#
app = flask.Flask(__name__)


#
# Handle subpaths
#
app.wsgi_app = reverse_proxied.ReverseProxied(app.wsgi_app)


#
# General onfig
#
app.config.from_object('hxl_proxy.default_config')
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


#
# Set up output cache
#
cache = flask_caching.Cache(app, config=app.config.get('CACHE_CONFIG'))
# (Setting up requests cache dynamically in controllers.py)

#
# Needed to register annotations (save until last)
#
import hxl_proxy.controllers

# end
