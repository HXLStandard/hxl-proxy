"""
Top-level Flask application for HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org

"""

__version__="1.27.1"
"""Module version number
See https://www.python.org/dev/peps/pep-0396/

"""

#
# Continue with other imports
#
import flask, flask_caching, json, os, requests_cache, werkzeug.datastructures
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
# General config
#
app.config.from_object('hxl_proxy.default_config')
if os.environ.get('HXL_PROXY_CONFIG'):
    app.config.from_envvar('HXL_PROXY_CONFIG')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


#
# Set up logging before any other imports, to get correct format in server logs
#
import logging, logging.config



# Allow all logging at root level, but filter at WSGI level
# That way, other loggers can choose their own level
# of the logging level

class ExcludeFilter(logging.Filter):

    def __init__ (self, excludes):
        self.excludes = excludes

    def filter (self, record):
        return not (record.name in self.excludes)

logging.config.dictConfig(
    {
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            },
            # This is where we can implement JSON formatting later
        },
        'handlers': {
            # default handler for everything but "hxl.REMOTE_ACCESS"
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default',
                'level': app.config.get('LOGGING_LEVEL', 'ERROR'),
                'filters': ['skip_remote_access'],
            },
            # special handler for "hxl.REMOTE_ACCESS"
            'remote_access': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default',
                'level': app.config.get('REMOTE_ACCESS_LOGGING_LEVEL', 'INFO'),
                'filters': ['remote_access'],
            },
        },
        'filters': {
            # Filter to show everything but "hxl.REMOTE_ACCESS"
            'skip_remote_access': {
                '()': ExcludeFilter,
                'excludes': ['hxl.REMOTE_ACCESS'],
            },
            # Filter to show only messages for "hxl.REMOTE_ACCESS"
            'remote_access': {
                '()': logging.Filter,
                'name': 'hxl.REMOTE_ACCESS',
            },
        },
        'root': {
            # Handlers enabled at the start (app will add at least one more)
            'handlers': ['wsgi', 'remote_access',],
            # Default root logging level (overridden by handlers)
            'level': app.config.get('ROOT_LOGGING_LEVEL', 'INFO'),
        },
    }
)

logger = logging.getLogger(__name__)
""" Python logger for this module """


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
