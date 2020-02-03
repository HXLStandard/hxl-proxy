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

import hxl_proxy, io, json, urllib
from . import base, resolve_path

DATASET_URL = 'http://example.org/basic-dataset.csv'



########################################################################
# Base class for controller tests
########################################################################

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



########################################################################
# Top-level controllers
########################################################################

class TestAbout(AbstractControllerTest):

    path = '/about.html'

    def test_about(self):
        response = self.get(self.path)
        assert b'About the HXL Proxy' in response.data



########################################################################
# /data controllers
########################################################################

class TestDataLogin(AbstractControllerTest):

    path = '/data/AAAAA/login'

    def test_page(self):
        response = self.get(self.path)
        assert b'Password required' in response.data
        assert b'type="password"' in response.data


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
    def test_auth(self):
        response = self.get(self.path, {
            'url': 'http://example.org/private/data.csv'
        }, 302)
        

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
    def test_auth(self):
        response = self.get("/data/edit", {
            'url': 'http://example.org/private/data.csv'
        }, 302)
        

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


class TestDataSavePage(AbstractControllerTest):

    path = '/data/save'

    def test_page(self):
        response = self.get(self.path, {
            'url': DATASET_URL,
        })
        assert b'Save recipe' in response.data
        assert b'<form' in response.data


class TestDataPage(AbstractControllerTest):
    """Test /data and /data/{recipe_id}"""

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_auth(self):
        response = self.get("/data", {
            'url': 'http://example.org/private/data.csv'
        }, 302)
        
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
    def test_auth(self):
        response = self.get("/data/validate", {
            'url': 'http://example.org/private/data.csv'
        }, 302)
        

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


class TestValidateAction(AbstractControllerTest):

    def test_post_valid_content(self):
        """Should succeed, because content is valid against default schema"""
        response = self.post(
            '/actions/validate',
            data = {
                'include_dataset': True,
                'content': (io.BytesIO(b"#adm1,#affected\r\nCoast,100\r\nPlains,200\r\n"), 'text.csv'),
            }
        )
        result = json.loads(response.get_data(True))
        self.assertTrue(result['is_valid'])

    def test_post_invalid_content(self):
        """Should failed, because #affected is not a number"""
        response = self.post(
            '/actions/validate',
            data = {
                'content': (io.BytesIO(b"#adm1,#affected\r\nCoast,xxx\r\nPlains,200\r\n"), 'text.csv')
            }
        )
        result = json.loads(response.get_data(True))
        self.assertFalse(result['is_valid'])

    def test_post_schema(self):
        """Should fail, because #affected < 1000 per custom schema"""
        response = self.post(
            '/actions/validate',
            data = {
                'content': (io.BytesIO(b"#adm1,#affected\r\nCoast,100\r\nPlains,200\r\n"), 'text.csv'),
                'schema_content': (io.BytesIO(b'[{"#valid_tag":"#affected","#valid_value+min":"1000"}]'), 'schema.csv'),
            }
        )
        result = json.loads(response.get_data(True))
        self.assertFalse(result['is_valid'])

    def test_post_excel(self):
        """Open a dataset and schema from an Excel sheet"""
        with open(resolve_path('files/validation-data.xlsx'), 'rb') as data_input:
            with open(resolve_path('files/validation-data.xlsx'), 'rb') as schema_input:
                response = self.post(
                    '/actions/validate',
                    data = {
                        'content': data_input,
                        'schema_content': schema_input,
                        'schema_sheet': 1,
                        'include_dataset': True
                    }
                )
                report = json.loads(response.get_data(True))
                self.assertTrue('Access-Control-Allow-Origin' in response.headers)
                self.assertFalse(report['is_valid'])
                self.assertTrue('dataset' in report)
                self.assertTrue(len(report['dataset']) > 2)


class TestDataAdvanced(AbstractControllerTest):

    path = '/data/advanced'

    def test_page(self):
        response = self.get(self.path)
        assert b'Advanced transformation' in response.data



########################################################################
# API tests
########################################################################

class TestPcodes(AbstractControllerTest):

    def test_good_pcodes(self):
        response = self.get('/api/pcodes/gin-adm1.csv')
        self.assertTrue(response.headers.get('content-type', '').startswith('text/csv'))
        self.assertEqual('*', response.headers.get('access-control-allow-origin'))

    def test_bad_pcodes(self):
        response = self.get('/api/pcodes/xxx-adm1.csv', status=404)
        #not easy before Flask 1.0
        #self.assertEqual('application/json', response.headers.get('content-type'))
        #self.assertEqual('*', response.headers.get('access-control-allow-origin'))

    
class TestHash(AbstractControllerTest):

    path = '/api/hash'

    URL = 'http://example.org/basic-dataset.csv'

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_headers_hash(self):
        response = self.get(self.path, {
            'url': self.URL,
            'headers_only': 'on'
        })
        report = json.loads(response.get_data(True))
        self.assertEqual(32, len(report['hash']))
        self.assertEqual(self.URL, report['url'])
        self.assertTrue('date' in report)
        self.assertTrue(report['headers_only'])
        self.assertTrue('headers' in report)
        self.assertTrue('hashtags' in report)
                            
    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_data_hash(self):
        response = self.get(self.path, {
            'url': self.URL
        })
        report = json.loads(response.get_data(True))
        self.assertEqual(32, len(report['hash']))
        self.assertEqual(self.URL, report['url'])
        self.assertTrue('date' in report)
        self.assertFalse(report['headers_only'])
        self.assertTrue('headers' in report)
        self.assertTrue('hashtags' in report)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_hashes_different(self):
        response_headers = self.get(self.path, {
            'url': self.URL,
            'headers_only': 'on'
        })
        report_headers = json.loads(response_headers.get_data(True))
        response_data = self.get(self.path, {
            'url': self.URL
        })
        report_data = json.loads(response_data.get_data(True))
        self.assertNotEquals(report_headers['hash'], report_data['hash'])
    

class TestDataPreview(AbstractControllerTest):

    path = '/api/data-preview.json'

    EXPECTED_JSON = [
        ['Organisation', 'Sector', 'Country'],
        ['#org', '#sector', '#country'],
        ['Org A', 'WASH', 'Colombia'],
        ['Org B', 'Education', 'Guinea'],
        ['Org C', 'Health', 'Myanmar']
    ]

    EXPECTED_CSV = b'Organisation,Sector,Country\r\n#org,#sector,#country\r\nOrg A,WASH,Colombia\r\nOrg B,Education,Guinea\r\nOrg C,Health,Myanmar\r\n'

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_csv_input(self):
        response = self.get(self.path, {
            'url': 'http://example.org/basic-dataset.csv'
        })
        self.assertEqual(self.EXPECTED_JSON, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_excel_input(self):
        response = self.get(self.path, {
            'url': 'http://example.org/basic-dataset.xlsx',
        })
        self.assertEqual(self.EXPECTED_JSON, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_excel_multisheet(self):
        response = self.get(self.path, {
            'url': 'http://example.org/multisheet-dataset.xlsx',
            'sheet': 1,
        })
        self.assertEqual(self.EXPECTED_JSON, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_limit_rows(self):
        response = self.get(self.path, {
            'url': 'http://example.org/basic-dataset.xlsx',
            'rows': 2,
        })
        self.assertEqual(self.EXPECTED_JSON[:2], response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_csv_output(self):
        response = self.get('/api/data-preview.csv', {
            'url': 'http://example.org/basic-dataset.xlsx',
        })
        self.assertEqual(self.EXPECTED_CSV, response.data)

class TestDataPreviewGetSheets(AbstractControllerTest):

    path = '/api/data-preview-sheets.json'

    EXPECTED_JSON_FOR_CSV = [
        'Default'
    ]
    EXPECTED_JSON_FOR_EXCEL = [
        'basic-dataset'
    ]

    EXPECTED_JSON_FOR_EXCEL_MULTISHEET = [
        'Not the right sheet',
        'The right sheet'
    ]


    EXPECTED_CSV = b'basic-dataset\r\n'

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_csv_input(self):
        response = self.get(self.path, {
            'url': 'http://example.org/basic-dataset.csv'
        })
        self.assertEqual(self.EXPECTED_JSON_FOR_CSV, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_excel_input(self):
        response = self.get(self.path, {
            'url': 'http://example.org/basic-dataset.xlsx',
        })
        self.assertEqual(self.EXPECTED_JSON_FOR_EXCEL, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_excel_multisheet(self):
        response = self.get(self.path, {
            'url': 'http://example.org/multisheet-dataset.xlsx',
        })
        self.assertEqual(self.EXPECTED_JSON_FOR_EXCEL_MULTISHEET, response.json)

    @patch(URL_MOCK_TARGET, new=URL_MOCK_OBJECT)
    def test_csv_output(self):
        response = self.get('/api/data-preview-sheets.csv', {
            'url': 'http://example.org/basic-dataset.xlsx',
        })
        self.assertEqual(self.EXPECTED_CSV, response.data)

########################################################################
# Humanitarian.ID controllers (not currently in use)
########################################################################

class TestHIDLogin(AbstractControllerTest):

    path = '/login'

    def test_redirect(self):
        response = self.get(self.path, status=303)
        assert b'/oauth/authorize' in response.data


class TestHIDLogout(AbstractControllerTest):

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



########################################################################
# Obsolete pages
########################################################################

class TestRemovedPages(AbstractControllerTest):

    def test_chart_removed(self):
        """/data/chart no longer exists. Should return 410."""
        response = self.get('/data/chart', {
            "url": "http://example.org/data.csv"
        }, 410)
        response = self.get('/data/abcdef/chart', {}, 410)

    def test_map_removed(self):
        """/data/map no longer exists. Should return 410."""
        response = self.get('/data/map', {
            "url": "http://example.org/data.csv"
        }, 410)
        response = self.get('/data/abcdef/map', {}, 410)

# end
