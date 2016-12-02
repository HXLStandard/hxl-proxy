hxl-proxy
=========

Python-/flask-based web proxy for transforming a HXL dataset
dynamically. Currently runs only in Python 2.7+, but Python 3 support
is close.

User documentation is available at https://github.com/HXLStandard/hxl-proxy/wiki

# Installation

Installation from PyPi:

```
pip install hxl-proxy
```

Installation from source:

```
python setup.py install
```

Running unit tests:

```
python setup.py test
```

# Configuration

To configure the proxy, make a copy of config.py.TEMPLATE (e.g. to config.py), and change its values as necessary. The environment variable HXL_PROXY_CONFIG should point to your local config file's location.  More details appear below.

## Filesystem

* CACHE_DIR - a directory where the proxy can cache output files. The directory must exist and be readable and writable by the web-server process.
* REQUEST_CACHE - a file (which the proxy will create if necessary) where the proxy can cache input files. The file's directory must exist and be readable and writable by the web-server process.
* DB_FILE - a file (which the proxy will create if necessary) containing a SQLite3 database of saved configurations. The file's directory must exist and be readable and writable by the web-server process.

## Authorisation tokens

To use the Google Drive selector, you will require a client ID and OAuth id from Google.  To allow users to log in via Humanitarian.ID, you will require a client ID, client secret, and redirect URI from the Humanitarian.ID team.

## P-codes and mapping

For mapping, the Proxy uses a collection of GeoJSON files hosted online. If you want to use a local copy (e.g. for offline demos), clone the GitHub repository at https://github.com/hxlstandard/p-codes and set the new base URL as the value of PCODE_BASE_URL. Note that the server serving the local copy must implement CORS, since the shapes get loaded on the browser side: https://www.w3.org/TR/cors/

Edit PCODE_COUNTRY_MAP if you'd like to make more countries available in the map dropdown menu.


# Usage

Launching a local server (usually on http://127.0.0.1:5000):

```
python run-server.py
```

For web deployment, see the hxl-proxy.wsgi.TEMPLATE file and the
flask documentation.

For more on HXL, see http://hxlstandard.org

For more documentation about the underlying HXL engine and filters,
see https://github.com/HXLStandard/libhxl-python/wiki
