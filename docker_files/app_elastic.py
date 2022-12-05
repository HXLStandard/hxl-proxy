import sys
import os
#sys.path.insert(0, '/srv/www/')
os.environ['HXL_PROXY_CONFIG'] = '/srv/config/config.py'
from hxl_proxy import app as application

from elasticapm.contrib.flask import ElasticAPM

apm = ElasticAPM(app=application,
    service_name=os.getenv('ELASTIC_APM_SERVICE_NAME'),
    server_url=os.getenv('ELASTIC_APM_SERVER_URL'),
    secret_token=os.getenv('ELASTIC_APM_SECRET_TOKEN'),
    environment=os.getenv('ELASTIC_APM_ENVIRONMENT'),
    enabled=os.getenv('ELASTIC_APM_ENABLED')
)
