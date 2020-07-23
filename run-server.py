#!/usr/bin/env python

"""Run a local dev copy of the HXL Proxy"""
import sys
from hxl_proxy import app
app.run(debug=True, host='localhost')
