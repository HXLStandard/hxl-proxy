""" Context managers for caching """

import hxl_proxy, logging, os, redis, requests_cache

logger = logging.getLogger(__name__)
""" Python logger for this module """


class input:
    """Context manager for input caching.

    Uses the app.config REQUEST_CACHE_* variables, including
    REQUEST_CACHE_TYPE, REQUEST_CACHE_NAME, and
    REQUEST_CACHE_TIMEOUT_SECONDS, as defaults.

    Usage:
        with caching.input():
            data = hxl.data(source_url)

        with caching.input(namespace="foo", timeout=3600):
            data = hxl.data(source_url)

    """

    def __init__ (self, namespace=None, timeout=None):
        """ Temporarily enable input caching.

        Args:
            namespace: the cache namespace to use (defaults to app.config["REQUEST_CACHE_NAME"])
            timeout: the duration for caching items, in seconds (defaults to app.config["REQUEST_CACHE_TIMEOUT_SECONDS"])
        """

        config = hxl_proxy.app.config

        if namespace is None:
            self.namespace = config.get('REQUEST_CACHE_NAME', "hxl-proxy-in")
        else:
            self.namespace = namespace
            
        if timeout is None:
            self.timeout = config.get('REQUEST_CACHE_TIMEOUT', 3600)
        else:
            self.timeout = timeout

        self.backend = config.get('REQUEST_CACHE_BACKEND', "memory")

        self.backend_args = config.get('REQUEST_CACHE_EXTRAS', {})

    def __enter__ (self):
        requests_cache.install_cache(self.namespace, backend=self.backend, expire_after=self.timeout, **self.backend_args)

    def __exit__ (self, type, value, traceback):
        requests_cache.uninstall_cache()
