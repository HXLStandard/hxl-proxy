"""
Base classes for HXL Proxy unit tests.
David Megginson
December 2015

License: Public Domain
"""

import unittest
import os
import tempfile

import hxl_proxy

TEST_DATA = os.path.join(os.path.dirname(__file__), 'test-data.sql')

class AbstractDBTest(unittest.TestCase):
    """Base for all HXL Proxy tests that require a database.
    """

    def setUp(self):
        super().setUp()
        hxl_proxy.dao.db.create_db()
        hxl_proxy.dao.db.execute_file(TEST_DATA)

    def tearDown(self):
        super().tearDown()
    

