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

    def test_strnorm(self):
        """Normalise case and whitespace in a string."""
        self.assertEqual('foo bar', hxl_proxy.util.strnorm('  foo   Bar   '))
        self.assertEqual('foo bar', hxl_proxy.util.strnorm("  foO\nBar   "))

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
        self.assertEquals(expected, hxl_proxy.util.urlencode_utf8(params))

    def test_using_tagger_p(self):
        with hxl_proxy.app.test_request_context('/data?tagger-01-header=country+code&tagger-01-tag=country%2Bcode'):
            recipe = hxl_proxy.util.get_recipe()
            self.assertTrue(hxl_proxy.util.using_tagger_p(recipe))
        with hxl_proxy.app.test_request_context('/data?url=http://example.org'):
            recipe = hxl_proxy.util.get_recipe()
            self.assertFalse(hxl_proxy.util.using_tagger_p(recipe))

    def test_get_recipe(self):
        # TODO test with recipe_id access
        with hxl_proxy.app.test_request_context('/data?url=http://example.org&filter01=count&count-spec01=country'):
            recipe = hxl_proxy.util.get_recipe()
            self.assertTrue(recipe)
            self.assertEqual('count', recipe['args'].get('filter01'))

    # skip check_auth

    # TODO add_args

    # TODO severity_class

    # TODO re_search

# end
