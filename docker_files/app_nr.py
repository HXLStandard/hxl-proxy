import newrelic.agent
import sys
import os
newrelic.agent.initialize()
#sys.path.insert(0, '/srv/www/')
os.environ['HXL_PROXY_CONFIG'] = '/srv/config/config.py'
from hxl_proxy import app as application
