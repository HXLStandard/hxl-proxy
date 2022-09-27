"""
Unit tests for hxl_proxy.util module
David Megginson
December 2015

License: Public Domain
"""

import unittest
from collections import OrderedDict
import hxl_proxy

class TestUtil(unittest.TestCase):

    def test_make_cache_key(self):
        """Test making a cache key for a set of arguments."""
        import pickle
        with hxl_proxy.app.test_request_context('/data?a=aa&b=bb&force=on'):
            # force should be skipped
            args_out = {'a': 'aa', 'b': 'bb'}
            # this could fail in the future because key ordering isn't predictable
            expected = '/data' + pickle.dumps(args_out).decode('latin1')
            self.assertEqual(expected, hxl_proxy.util.make_cache_key())

    def test_skip_cache_p(self):
        """Check if there's a force argument for cache skipping."""
        with hxl_proxy.app.test_request_context('/data?a=aa&b=bb&force=1'):
            self.assertTrue(hxl_proxy.util.skip_cache_p())
        with hxl_proxy.app.test_request_context('/data?a=aa&b=bb'):
            self.assertFalse(hxl_proxy.util.skip_cache_p())

    # skip stream_template

    def test_urlquote(self):
        """Test escaping special characters in URL parameters."""
        self.assertEqual('a%3Fb', hxl_proxy.util.urlquote('a?b'))
        self.assertEqual('a%26b', hxl_proxy.util.urlquote('a&b'))
        self.assertEqual('a%3Db', hxl_proxy.util.urlquote('a=b'))
        self.assertEqual('a+b', hxl_proxy.util.urlquote('a b'))

    def test_urlencode_utf8(self):
        expected = 'a=aa&b=bb&c=cc'
        # straight-forward array
        params = OrderedDict()
        params['a'] = 'aa'
        params['b'] = 'bb'
        params['c'] = 'cc'
        self.assertEqual(expected, hxl_proxy.util.urlencode_utf8(params))

    def test_using_tagger_p(self):
        with hxl_proxy.app.test_request_context('/data?tagger-01-header=country+code&tagger-01-tag=country%2Bcode'):
            recipe = hxl_proxy.recipes.Recipe()
            self.assertTrue(hxl_proxy.util.using_tagger_p(recipe))
        with hxl_proxy.app.test_request_context('/data?url=http://example.org'):
            recipe = hxl_proxy.recipes.Recipe()
            self.assertFalse(hxl_proxy.util.using_tagger_p(recipe))

    def test_is_allowed_1(self):
        """Make sure we allow external calls if no allowed list has been defined."""
        self.assertTrue(hxl_proxy.util.is_allowed('http://example.org'))

    def test_is_allowed_2(self):
        """Make sure we allow external calls if their parent domain is in the allowed list."""
        hxl_proxy.app.config['ALLOWED_DOMAINS_LIST'] = ['example.org']
        self.assertTrue(hxl_proxy.util.is_allowed('http://example.org'))

    def test_is_allowed_3(self):
        """Make sure we allow external calls if their parent domain is in the allowed list and the allowed list has been defined."""
        hxl_proxy.app.config['ALLOWED_DOMAINS_LIST'] = ['example.org']
        self.assertFalse(hxl_proxy.util.is_allowed('http://foo.org'))

    # TODO severity_class

    # TODO re_search

# end
