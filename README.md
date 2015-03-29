hxl-proxy
=========

Python-/flask-based web proxy for transforming a HXL dataset
dynamically. Currently runs only in Python 2.7+, but Python 3 support
is close.

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

# Usage

Launching a local server (usually on http://127.0.0.1:5000):

```
python run-server.py
```

For web deployment, see the hxl-standard.wsgi.TEMPLATE file and the
flask documentation.

For more on HXL, see http://hxlstandard.org

For more documentation about the underlying HXL engine and filters,
see https://github.com/HXLStandard/libhxl-python/wiki
