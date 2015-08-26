#!/usr/bin/env python

"""Run a local dev copy of the HXL Proxy"""
import sys
from werkzeug.contrib.profiler import ProfilerMiddleware
from hxl_proxy import app

app.config['PROFILE'] = True
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
app.run(debug=True, host='0.0.0.0')
