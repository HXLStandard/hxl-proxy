hxl-proxy
=========

Python-/flask-based web proxy for transforming a HXL dataset dynamically.

http://hxlstandard.org

# Usage

Install libhxl-python and flask.

```
python run-server.py
```

Typically, the proxy will be running on port 5000 for local use.  For
web deployment, see the hxl-standard.wsgi.TEMPLATE file and the flask
documentation.
