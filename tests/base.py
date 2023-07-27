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

class AbstractTest(unittest.TestCase):
    """Base for all HXL Proxy tests that require a database.
    """

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()


