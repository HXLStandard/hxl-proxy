DEBUG=True
SECRET_KEY='<Something hard to guess>'

DB_TYPE='sqlite3'
DB_FILE='/srv/www/hxl-proxy.db'

CACHE_CONFIG = {
   'CACHE_TYPE': 'redis',
   'CACHE_KEY_PREFIX': 'hxl-proxy-out:',
   'CACHE_DEFAULT_TIMEOUT': 30,
   'CACHE_REDIS_HOST': 'redis',
   'CACHE_REDIS_PORT': '6379',
   'CACHE_REDIS_URL': 'redis://redis:6379/2',
}


REQUEST_CACHE_NAME = 'hxl-proxy-in'
REQUEST_CACHE_BACKEND = 'redis'
REQUEST_CACHE_TIMEOUT_SECONDS = 30
