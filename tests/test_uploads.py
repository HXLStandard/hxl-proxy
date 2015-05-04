"""
Unit tests for hxl-proxy uploads module
David Megginson
May 2015

License: Public Domain
"""

import unittest

from hxl_proxy.uploads import UploadManager, Upload

ROOT_DIR = "/tmp"
BASE_URL = "http://example.org/uploads"
RELPATH = "data.csv"
DATA = "#org,#sector,#adm1\nNGO A,WASH,Coast\n"

class TestUpload(unittest.TestCase):

    def setUp(self):
        self.upload = Upload(ROOT_DIR, BASE_URL, RELPATH)

    def test_path(self):
        self.assertEqual("/tmp/data.csv", self.upload.get_path())

    def test_url(self):
        self.assertEqual("http://example.org/uploads/data.csv", self.upload.get_url())

    def test_open(self):
        # FIXME relies on local filesystem
        with self.upload.open('wt') as output:
            self.assertTrue(output)

    def test_read_write(self):
        self.upload.write(DATA)
        self.assertEqual(DATA, self.upload.read())

