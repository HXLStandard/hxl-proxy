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

import hxl_proxy, urllib
from . import base

DATASET_URL = 'http://example.org/basic-dataset.csv'

class AbstractControllerTest(base.AbstractDBTest):
    """Base class for controller tests."""

    def setUp(self):
        """Configure a test app instance."""
        super().setUp()
        hxl_proxy.app.config['DEBUG'] = False
        hxl_proxy.app.config['SECRET_KEY'] = 'abcde'
        hxl_proxy.app.config['HID_BASE_URL'] = 'https://hid.example.org'
        hxl_proxy.app.config['HID_CLIENT_ID'] = '12345'
        hxl_proxy.app.config['HID_REDIRECT_URI'] = 'https://proxy.example.org'

        self.recipe_id = 'AAAAA'
        self.client = hxl_proxy.app.test_client()

    def tearDown(self):
        super().tearDown()

    def get(self, path, query_string=None, status=200):
        """
        Send a request to the test client and hang onto the result.
        @param path the path to request
        @param query_string (optional) a dict of get parameters
        @param status (optional) the expected HTTP status (defaults to 200)
        @return a Response object
        """
        self.response = self.client.get(path, query_string=query_string)
        self.assertEqual(status, self.response.status_code)
        return self.response

    def post(self, path, query_string=None, data=None, status=200):
        """
        Send a request to the test client and hang onto the result.
        @param path the path to request
        @param params (optional) a dict of get parameters
        @param status (optional) the expected HTTP status (defaults to 200)
        @return a Response object
        """
        print('***', path)
        self.response = self.client.post(path, query_string=query_string, data=data)
        self.assertEqual(status, self.response.status_code)
        return self.response

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
    def make_recipe():
        recipe = Recipe({
            'url': 'http://example.org/basic-dataset.csv'
        })
        recipe.name = 'Sample dataset'
        return recipe


class TestLogin(AbstractControllerTest):

    path = '/login'

    def test_redirect(self):
        response = self.get(self.path, status=303)
        assert b'/oauth/authorize' in response.data


class TestLogout(AbstractControllerTest):

    path = '/logout'

    def test_redirect(self):
        response = self.get(self.path, status=303)
        self.assertEqual('http://localhost/', response.location)

    def test_session(self):
        """Test that logout clears the session."""
        import flask
        # Extra cruft for setting a session cookie
        with self.client as client:
            with client.session_transaction() as session:
                session['user'] = 'abc'
            response = self.get('/data/source')
            assert 'user' in flask.session
            response = self.get(self.path, status=303)
            assert 'user' not in flask.session


class TestDataSource(AbstractControllerTest):

    path = '/data/source'

    def test_title(self):
        response = self.get(self.path)
        assert b'Choose your HXL data source' in response.data

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

class TestTaggerPage(AbstractControllerTest):

    path = '/data/tagger'

    def test_redirect(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.get(self.path, status=303)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_choose_row(self):
        """Row not yet chosen."""
        response = self.get(self.path, {
            'url': 'http://example.org/untagged-dataset.csv'
        })
        assert b'Tag a non-HXL dataset' in response.data
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
        assert b'Tag a non-HXL dataset' in response.data
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
        assert b'<h3>Result preview</h3>' in response.data
        assert b'<th>#org</th>' in response.data
        assert b'<th>#sector</th>' in response.data
        assert b'<th>#country</th>' in response.data


class TestEditPage(AbstractControllerTest):
    """Test /data/edit and /data/{recipe_id}/edit"""

    def test_redirect_no_url(self):
        """With no URL, the app should redirect to /data/source automatically."""
        response = self.get('/data/edit', status=303)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_redirect_no_tags(self):
        """If the dataset doesn't contain HXL tags, it should redirect to tagger."""
        response = self.get('/data/edit', {
            'url': 'http://example.org/untagged-dataset.csv'
        }, status=303)
        assert '/data/tagger' in response.location
        assert 'untagged-dataset.csv' in response.location

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.get('/data/edit', {
            'url': DATASET_URL,
            'force': 'on'
        })
        assert b'Data transformation recipe' in response.data
        self.assertBasicDataset(response)

    def test_need_login(self):
        response = self.get('/data/{}/edit'.format(self.recipe_id), status=303)
        assert '/data/{}/login'.format(self.recipe_id) in response.headers['Location']

    # TODO test logging in (good and bad passwords)

    # TODO test changing recipe


class TestDataPage(AbstractControllerTest):
    """Test /data and /data/{recipe_id}"""

    def test_empty_url(self):
        response = self.get('/data', status=303)
        assert response.location.endswith('/data/source')

    def test_local_file(self):
        """Make sure we're not leaking local data."""
        response = self.get('/data?url=/etc/passwd&force=on', status=500)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_url(self):
        response = self.get('/data', {
            'url': DATASET_URL,
            'force': 'on'
        })
        assert b'View data' in response.data
        self.assertBasicDataset(response)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_recipe_id(self):
        response = self.get('/data/{}?force=on'.format(self.recipe_id))
        assert b'Recipe #1' in response.data
        self.assertBasicDataset(response)

    # TODO test that filters work


class TestValidationPage(AbstractControllerTest):
    """Test /data/validate and /data/{recipe_id}/validate"""

    def test_empty_url(self):
        response = self.get('/data/validate', status=303)
        assert response.location.endswith('/data/source')

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_default_schema(self):
        response = self.get('/data/validate', {
            'url': DATASET_URL
        })
        assert b'Using the default schema' in response.data
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_good_schema(self):
        response = self.get('/data/validate', {
            'url': DATASET_URL,
            'schema_url': 'http://example.org/good-schema.csv'
        })
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_get_schema_pass(self):
        """GET with an inline schema that succeeds"""
        response = self.get('/data/validate', {
            'url': DATASET_URL,
            'schema_content': '[{"#valid_tag":"#org","#valid_required":"true"}]'
        })
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_get_schema_fail(self):
        """GET with an inline schema that fails"""
        response = self.get('/data/validate', {
            'url': DATASET_URL,
            'schema_content': '[{"#valid_tag":"#xxx","#valid_required":"true"}]'
        })
        assert b'validation issue(s)' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_post_schema_pass(self):
        """POST with an inline schema that succeeds"""
        response = self.post(
            '/data/validate',
            query_string={'url': DATASET_URL},
            data={'schema_content': '[{"#valid_tag":"#org","#valid_required":"true"}]'}
        )
        assert b'Validation succeeded' in response.data

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_post_schema_fail(self):
        """POST with an inline schema that fails"""
        response = self.post(
            '/data/validate',
            query_string={'url': DATASET_URL},
            data={'schema_content': '[{"#valid_tag":"#xxx","#valid_required":"true"}]'}
        )
        assert b'validation issue(s)' in response.data
# end
