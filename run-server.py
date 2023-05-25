#!/usr/bin/env python

"""Run a local dev copy of the HXL Proxy"""
import sys
import os
from hxl_proxy import app
from hxl import datatypes
if __name__ == "__main__":
    DEBUG = bool(datatypes.is_truthy(os.getenv('DEBUG', 'True')))
    app.run(debug=DEBUG, host=os.getenv('FLASK_HOST', 'localhost'))
