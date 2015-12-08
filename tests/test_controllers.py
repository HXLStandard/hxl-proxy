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

import hxl_proxy
from hxl_proxy.profiles import ProfileManager, Profile

#
# Mock URL access so that tests work offline
#
from . import URL_MOCK_TARGET, URL_MOCK_OBJECT
from unittest.mock import patch

class TestDataSource(unittest.TestCase):

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_title(self):
        response = self.client.get('/data/source')
        assert b'<h1>Choose a dataset</h1>' in response.data

    def test_prepopulate(self):
        """When a URL is available, it should be prepopulated."""
        response = self.client.get('/data/source', query_string={
            'url': 'http://example.org/data.csv'
        })
        assert b'value="http://example.org/data.csv"' in response.data

    def test_cloud_icons(self):
        """Test that the cloud icons are present."""
        response = self.client.get('/data/source')
        assert b'<span>HDX</span>' in response.data
        assert b'<span>Dropbox</span>' in response.data
        assert b'<span>Google Drive</span>' in response.data

    def test_sidebar(self):
        response = self.client.get('/data/source')
        assert b'HXL on a postcard' in response.data

class TestTagPage(unittest.TestCase):

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_redirect(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.client.get('/data/tagger')
        self.assertEquals(302, response.status_code)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_choose_row(self):
        """Row not yet chosen."""
        response = self.client.get('/data/tagger', query_string={
            'url': 'http://example.org/untagged-dataset.csv'
        })
        assert b'<h1>Add HXL tags</h1>' in response.data
        assert b'<b>last header row</b>' in response.data
        assert b'<td>Organisation</td>' in response.data
        assert b'<td>Myanmar</td>' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_choose_tags(self):
        """Row chosen."""
        response = self.client.get('/data/tagger', query_string={
            'url': 'http://example.org/untagged-dataset.csv',
            'header-row': '1'
        })
        assert b'<h1>Add HXL tags</h1>' in response.data
        assert b'<th>HXL hashtag</th>' in response.data
        assert b'value="organisation"' in response.data
        assert b'value="sector"' in response.data
        assert b'value="country"' in response.data
        
class TestEditPage(unittest.TestCase):
    """Test /data/edit and /data/<key>/edit"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_redirect_no_url(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.client.get('/data/edit')
        self.assertEquals(302, response.status_code)
        self.assertTrue(response.location.endswith('/data/source'))

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_redirect_no_tags(self):
        """If the dataset doesn't contain HXL tags, it should redirect to tagger."""
        response = self.client.get('/data/edit', query_string={
            'url': 'http://example.org/untagged-dataset.csv'
        })
        self.assertEquals(302, response.status_code)
        assert '/data/tagger' in response.location
        assert 'untagged-dataset.csv' in response.location

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.client.get('/data/edit?url=http://example.org/basic-dataset.csv')
        self.assertTrue(b'<h1>Transform your data</h1>' in response.data)
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
        self.assertEqual(403, response.status_code)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.client.get('/data?url=http://example.org/basic-dataset.csv')
        self.assertTrue(b'<h1>Result data</h1>' in response.data)
        assert_basic_dataset(self, response)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_key(self):
        response = self.client.get('/data/{}'.format(self.key))
        self.assertTrue(b'<h1>Sample dataset</h1>' in response.data)
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

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_default_schema(self):
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv')
        self.assertTrue(b'Using the default schema' in response.data)
        self.assertTrue(b'Validation succeeded' in response.data)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_good_schema(self):
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv&schema_url=http://example.org/good-schema.csv')
        self.assertTrue(b'Validation succeeded' in response.data)


#
# Utility functions
#

def start_tests(tests):
    """Set up a test object with a temporary profile database"""
    with tempfile.NamedTemporaryFile(delete=True) as file:
        tests.filename = file.name
    hxl_proxy.app.config['PROFILE_FILE'] = tests.filename
    hxl_proxy.app.config['SECRET_KEY'] = 'abcde'
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

def assert_basic_dataset(test, response):
    """Check that we're looking at the basic dataset"""
    test.assertEqual(200, response.status_code)
    test.assertTrue(b'Country' in response.data, "header from dataset on page")
    test.assertTrue(b'#country' in response.data, "hashtag from dataset on page")
    test.assertTrue(b'Org A' in response.data, "org from dataset on page")
    test.assertTrue(b'Education' in response.data, "sector from dataset on page")
    test.assertTrue(b'Myanmar' in response.data, "country from dataset on page")

# end
