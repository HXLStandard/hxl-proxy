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


class TestUploadManager:

    def setUp(self):
        self.manager = UploadManager(ROOT_DIR, BASE_DIR)

    def test_create_default(self):
        upload = self.manager.create_upload()
        self.assertEqual(ROOT_DIR, upload.root_dir)
        self.assertEqual(BASE_DIR, upload.base_dir)
        self.assertTrue(upload.reldir.endswith('data.csv'))

    def test_create_named(self):
        NAME = 'new_dataset.csv'
        upload = self.manager.create_upload(NAME)
        self.assertEqual(ROOT_DIR, upload.root_dir)
        self.assertEqual(BASE_DIR, upload.base_dir)
        self.assertTrue(upload.reldir.endswith(NAME))
