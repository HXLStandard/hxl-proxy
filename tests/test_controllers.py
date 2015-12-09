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

# Mock URL access so that tests work offline
from . import URL_MOCK_TARGET, URL_MOCK_OBJECT
from unittest.mock import patch


class BaseControllerTest(unittest.TestCase):
    """Base class for controller tests."""
    
    def setUp(self):
        """Set up a test object with a temporary profile database"""
        with tempfile.NamedTemporaryFile(delete=True) as file:
            self.filename = file.name
        hxl_proxy.app.config['PROFILE_FILE'] = self.filename
        hxl_proxy.app.config['SECRET_KEY'] = 'abcde'
        self.key = ProfileManager(self.filename).add_profile(self.make_profile())
        self.client = hxl_proxy.app.test_client()

    def tearDown(self):
        """Remove the temporary profile database"""
        os.remove(self.filename)

    def assertBasicDataset(self, response=None):
        """Check that we're looking at the basic dataset"""
        if response is None:
            response = self.response
        self.assertEqual(200, response.status_code)
        assert b'Country' in response.data
        assert b'#country' in response.data
        assert b'Org A' in response.data
        assert b'Education' in response.data
        assert b'Myanmar' in response.data

    @staticmethod
    def make_profile():
        profile = Profile({
            'url': 'http://example.org/basic-dataset.csv'
        })
        profile.name = 'Sample dataset'
        return profile


class TestDataSource(BaseControllerTest):
    """Unit tests for /data/source"""

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


class TestTaggerPage(BaseControllerTest):
    """Unit tests for /data/tagger"""

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
        
    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_tagger_output(self):
        """Test that the page accepts auto-tagged output."""
        response = self.client.get('/data/edit', query_string={
            'url': 'http://example.org/untagged-dataset.csv',
            'header-row': '1',
            'tagger-01-header': 'organisation',
            'tagger-01-tag': 'org',
            'tagger-02-header': 'sector',
            'tagger-02-tag': 'sector',
            'tagger-03-header': 'country',
            'tagger-03-tag': 'country'
        })
        assert b'<h3>Preview</h3>' in response.data
        assert b'<th>#org</th>' in response.data
        assert b'<th>#sector</th>' in response.data
        assert b'<th>#country</th>' in response.data


class TestEditPage(BaseControllerTest):
    """Test /data/edit and /data/<key>/edit"""

    def test_redirect_no_url(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.client.get('/data/edit')
        self.assertEquals(302, response.status_code)
        assert response.location.endswith('/data/source')

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
        assert b'<h1>Transform your data</h1>' in response.data
        self.assertBasicDataset(response)

    def test_need_login(self):
        response = self.client.get('/data/{}/edit'.format(self.key))
        self.assertEqual(302, response.status_code)
        assert '/data/{}/login'.format(self.key) in response.headers['Location']

    # TODO test logging in (good and bad passwords)

    # TODO test changing profile


class TestDataPage(BaseControllerTest):
    """Test /data and /data/<key>"""

    def test_empty_url(self):
        response = self.client.get('/data')
        self.assertEqual(303, response.status_code, "/data with no URL redirects to /data/edit")

    def test_local_file(self):
        response = self.client.get('/data?url=/etc/passwd')
        self.assertEqual(403, response.status_code)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.client.get('/data?url=http://example.org/basic-dataset.csv')
        assert b'<h1>Result data</h1>' in response.data
        self.assertBasicDataset(response)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_key(self):
        response = self.client.get('/data/{}'.format(self.key))
        assert b'<h1>Sample dataset</h1>' in response.data
        self.assertBasicDataset(response)

    # TODO test that filters work


class TestValidationPage(BaseControllerTest):
    """Test /data/validate and /data/key/validate"""

    def test_empty_url(self):
        response = self.client.get('/data/validate')
        self.assertEqual(303, response.status_code, "/data/validate with no URL redirects to /data/edit")

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_default_schema(self):
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv')
        assert b'Using the default schema' in response.data
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_good_schema(self):
        response = self.client.get('/data/validate?url=http://example.org/basic-dataset.csv&schema_url=http://example.org/good-schema.csv')
        assert b'Validation succeeded' in response.data

# end
