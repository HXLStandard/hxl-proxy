bind = '0.0.0.0:5000'
# worker type. comment out to use async gevent instead of the default sync
#worker_class = 'gevent'
access_log_format = '"%({x-real-ip}i)s" %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
accesslog = '/var/log/proxy/proxy.access.log'
errorlog = '/var/log/proxy/proxy.error.log'
loglevel = 'warning'
timeout = 120
graceful_timeout = 90
limit_request_line = 8096
