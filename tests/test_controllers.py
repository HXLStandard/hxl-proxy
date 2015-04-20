"""
Unit tests for actual web pages
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys
import os
import re
import tempfile

from . import resolve_path

if sys.version_info < (3, 3):
    from mock import patch
    URLOPEN_PATCH = 'urllib2.urlopen'
else:
    from unittest.mock import patch
    URLOPEN_PATCH = 'urllib.request.urlopen'

import hxl_proxy
from hxl_proxy.profiles import ProfileManager, Profile


class TestEditPage(unittest.TestCase):
    """Test /data/edit and /data/<key>/edit"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        rv = self.client.get('/data/edit')
        self.assertTrue('New HXL view' in rv.data, 'title')
        self.assertTrue('No data yet' in rv.data, 'no data warning')

    @patch(URLOPEN_PATCH)
    def test_url(self, mock):
        mock_basic_dataset(mock)
        response = self.client.get('/data/edit?url=http://example.org/basic-dataset.csv')
        self.assertTrue('<h1>New HXL view</h1>' in response.data)
        assert_basic_dataset(self, response)

    def test_need_login(self):
        response = self.client.get('/data/{}/edit'.format(self.key))
        self.assertEqual(302, response.status_code)
        self.assertTrue('/data/{}/login'.format(self.key) in response.headers['Location'], 'redirect to login')

    # TODO test logging in (good and bad passwords)

    # TODO test changing profile

class TestDataPage(unittest.TestCase):
    """Test /data and /data/<key>"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        response = self.client.get('/data')
        self.assertEqual(303, response.status_code, "/data with no URL redirects to /data/edit")

    def test_local_file(self):
        response = self.client.get('/data?url=/etc/passwd')
        self.assertEqual(403, response.status_code, "non-URL forbidden")

    @patch(URLOPEN_PATCH)
    def test_url(self, mock):
        mock_basic_dataset(mock)
        response = self.client.get('/data?url=http://example.org/basic-dataset.csv')
        self.assertTrue('<h1>New filter preview</h1>' in response.data)
        assert_basic_dataset(self, response)

    @patch(URLOPEN_PATCH)
    def test_key(self, mock):
        mock_basic_dataset(mock)
        response = self.client.get('/data/{}'.format(self.key))
        self.assertTrue('<h1>Sample dataset</h1>' in response.data)
        assert_basic_dataset(self, response)

    # TODO test that filters work


class TestValidationPage(unittest.TestCase):
    """Test /data/validate and /data/key/validate"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        response = self.client.get('/data/validate')
        self.assertEqual(303, response.status_code, "/data/validate with no URL redirects to /data/edit")

    @patch(URLOPEN_PATCH)
    def test_default_schema(self, mock):
        mock_basic_dataset(mock)
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv')
        self.assertTrue('Using the default schema' in response.data)
        self.assertTrue('Validation succeeded' in response.data)

    @patch(URLOPEN_PATCH)
    def test_good_schema(self, mock):
        mock_basic_dataset(mock)
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv&schema_url=foo')
        print(response.data)
        self.assertTrue('Validation succeeded' in response.data)


#
# Utility functions
#

def start_tests(tests):
    """Set up a test object with a temporary profile database"""
    with tempfile.NamedTemporaryFile(delete=True) as file:
        tests.filename = file.name
    hxl_proxy.app.config['PROFILE_FILE'] = tests.filename
    tests.key = ProfileManager(tests.filename).add_profile(make_profile())
    tests.client = hxl_proxy.app.test_client()

def end_tests(tests):
    """Remove the temporary profile database"""
    os.remove(tests.filename)

def make_profile():
    profile = Profile({
        'url': 'http://example.org/basic-dataset.csv'
    })
    profile.name = 'Sample dataset'
    return profile

def mock_basic_dataset(mock):
    """Will open last element of the URL path as a local file under ./files/"""
    def side_effect(url):
        filename = re.sub(r'^.*/([^/]+)$', '\\1', url)
        return open(resolve_path('files/' + filename))
    mock.side_effect = side_effect

def assert_basic_dataset(test, response):
    """Check that we're looking at the basic dataset"""
    test.assertEqual(200, response.status_code)
    test.assertTrue('Country' in response.data, "header from dataset on page")
    test.assertTrue('#country' in response.data, "hashtag from dataset on page")
    test.assertTrue('Org A' in response.data, "org from dataset on page")
    test.assertTrue(u'Education' in response.data, "sector from dataset on page")
    test.assertTrue('Myanmar' in response.data, "country from dataset on page")

# end
