#!/usr/bin/env python

"""Run a local dev copy of the HXL Proxy"""
import sys
import os
from hxl_proxy import app
app.run(debug=True, host=os.getenv('FLASK_HOST', 'localhost'))
