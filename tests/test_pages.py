"""
Unit tests for actual web pages
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys
import os
import tempfile

if sys.version_info < (3, 3):
    from mock import patch
    URLOPEN_PATCH = 'urllib.urlopen'
else:
    from unittest.mock import patch
    URLOPEN_PATCH = 'urllib.request.urlopen'

import hxl_proxy

class TestEditPage(unittest.TestCase):
    """Test /data/edit and /data/<key>/edit"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        rv = self.app.get('/data/edit')
        self.assertTrue('New HXL view' in rv.data)
        self.assertTrue('No data yet' in rv.data)

class TestDataPage(unittest.TestCase):
    """Test /data and /data/<key>"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        # No URL should redirect to data
        response = self.app.get('/data')
        print response.headers
        self.assertEqual(303, response.status_code)

    def test_local_file(self):
        # Trying to read a non-URL should result in 403 Forbidden
        response = self.app.get('/data?url=/etc/passwd')
        self.assertEqual(403, response.status_code)

    @patch(URLOPEN_PATCH)
    def test_url(self, mock):
        # TODO - mock up URL access to a local file
        response = self.app.get('/data?url=/tmp/foo')

class TestValidationPage(unittest.TestCase):
    """Test /data/validate and /data/key/validate"""

    def setUp(self):
        start_tests(self)

    def tearDown(self):
        end_tests(self)

    def test_empty_url(self):
        response = self.app.get('/data')
        self.assertEqual(303, response.status_code)


def start_tests(tests):
    """Set up a test object with a temporary profile database"""
    with tempfile.NamedTemporaryFile(delete=False) as file:
        tests.filename = file.name
    os.environ['HXL_PROXY_CONFIG'] = tests.filename
    tests.app = hxl_proxy.app.test_client()

def end_tests(tests):
    """Remove the temporary profile database"""
    os.remove(tests.filename)
    

