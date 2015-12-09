"""
Unit tests for HXL Proxy controllers.
David Megginson
March 2015

Check the rendered content of web pages.

License: Public Domain
"""

# Mock URL access so that tests work offline
from . import URL_MOCK_TARGET, URL_MOCK_OBJECT
from unittest.mock import patch

# Use a common base class
from .base import BaseControllerTest


class TestDataSource(BaseControllerTest):

    path = '/data/source'

    def test_title(self):
        response = self.get(self.path)
        assert b'<h1>Choose a dataset</h1>' in response.data

    def test_prepopulate(self):
        """When a URL is available, it should be prepopulated."""
        response = self.get(self.path, {
            'url': 'http://example.org/data.csv'
        })
        assert b'value="http://example.org/data.csv"' in response.data

    def test_cloud_icons(self):
        """Test that the cloud icons are present."""
        response = self.get(self.path)
        assert b'<span>HDX</span>' in response.data
        assert b'<span>Dropbox</span>' in response.data
        assert b'<span>Google Drive</span>' in response.data

    def test_sidebar(self):
        response = self.get(self.path)
        assert b'HXL on a postcard' in response.data


class TestTaggerPage(BaseControllerTest):

    path = '/data/tagger'

    def test_redirect(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.get(self.path)
        self.assertEquals(302, response.status_code)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_choose_row(self):
        """Row not yet chosen."""
        response = self.get(self.path, {
            'url': 'http://example.org/untagged-dataset.csv'
        })
        assert b'<h1>Add HXL tags</h1>' in response.data
        assert b'<b>last header row</b>' in response.data
        assert b'<td>Organisation</td>' in response.data
        assert b'<td>Myanmar</td>' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_choose_tags(self):
        """Row chosen."""
        response = self.get(self.path, {
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
        response = self.get('/data/edit', {
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
    """Test /data/edit and /data/{key}/edit"""

    def test_redirect_no_url(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.get('/data/edit')
        self.assertEquals(302, response.status_code)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_redirect_no_tags(self):
        """If the dataset doesn't contain HXL tags, it should redirect to tagger."""
        response = self.get('/data/edit', {
            'url': 'http://example.org/untagged-dataset.csv'
        })
        self.assertEquals(302, response.status_code)
        assert '/data/tagger' in response.location
        assert 'untagged-dataset.csv' in response.location

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.get('/data/edit', {
            'url': 'http://example.org/basic-dataset.csv'
        })
        assert b'<h1>Transform your data</h1>' in response.data
        self.assertBasicDataset(response)

    def test_need_login(self):
        response = self.get('/data/{}/edit'.format(self.key))
        self.assertEqual(302, response.status_code)
        assert '/data/{}/login'.format(self.key) in response.headers['Location']

    # TODO test logging in (good and bad passwords)

    # TODO test changing profile


class TestDataPage(BaseControllerTest):
    """Test /data and /data/{key}"""

    def test_empty_url(self):
        response = self.get('/data')
        self.assertEqual(303, response.status_code, "/data with no URL redirects to /data/edit")

    def test_local_file(self):
        response = self.get('/data?url=/etc/passwd')
        self.assertEqual(403, response.status_code)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.get('/data', {
            'url': 'http://example.org/basic-dataset.csv'
        })
        assert b'<h1>Result data</h1>' in response.data
        self.assertBasicDataset(response)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_key(self):
        response = self.get('/data/{}'.format(self.key))
        assert b'<h1>Sample dataset</h1>' in response.data
        self.assertBasicDataset(response)

    # TODO test that filters work


class TestValidationPage(BaseControllerTest):
    """Test /data/validate and /data/{key}/validate"""

    def test_empty_url(self):
        response = self.get('/data/validate')
        self.assertEqual(303, response.status_code)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_default_schema(self):
        response = self.get('/data/validate', {
            'url': 'http://example.org/basic-dataset.csv'
        })
        assert b'Using the default schema' in response.data
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_good_schema(self):
        response = self.get('/data/validate', {
            'url': 'http://example.org/basic-dataset.csv',
            'schema_url': 'http://example.org/good-schema.csv'
        })
        assert b'Validation succeeded' in response.data

# end
