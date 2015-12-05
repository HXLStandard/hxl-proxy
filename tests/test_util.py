"""
Unit tests for hxl_proxy.util module
David Megginson
December 2015

License: Public Domain
"""

import unittest
import hxl_proxy

class TestUtil(unittest.TestCase):

    def setUp(self):
        self.app = hxl_proxy.app
        self.test_app = hxl_proxy.app.test_client()

        
    def test_make_cache_key(self):
        """Test making a cache key for a set of arguments."""
        import pickle
        with self.app.test_request_context('/data?a=aa&b=bb&force=1'):
            # force should be skipped
            args_out = {'a': 'aa', 'b': 'bb'}
            # this could fail in the future because key ordering isn't predictable
            expected = '/data' + pickle.dumps(args_out).decode('latin1')
            self.assertEqual(expected, hxl_proxy.util.make_cache_key())


    def test_skip_cache_p(self):
        """Check if there's a force argument for cache skipping."""
        with self.app.test_request_context('/data?a=aa&b=bb&force=1'):
            self.assertTrue(hxl_proxy.util.skip_cache_p())
