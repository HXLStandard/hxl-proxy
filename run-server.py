#!/usr/bin/env python

"""Run a local dev copy of the HXL Proxy"""

from hxl_proxy import app
app.run(debug=True, host='0.0.0.0')
