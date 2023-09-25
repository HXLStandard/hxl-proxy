hxl-proxy
=========

Python-/flask-based web proxy for transforming a HXL dataset
dynamically. Requires Python3.

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

To configure the proxy, make a copy of config.py.TEMPLATE (e.g. to config.py), and change its values as necessary. The environment variable HXL\_PROXY\_CONFIG should point to your local config file's location.  More details appear below.

## Caching

Choose and configure your input and output caches as needed, following the examples in the config template. You may need to create local directories or databases, depending on the caching backends you choose.

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
