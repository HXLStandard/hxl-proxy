"""Test utility functions in __init__.py"""

import unittest

from hxl_proxy import *

class TestUtil(unittest.TestCase):

    def test_munge_url_nogid(self):
        url_in = 'https://docs.google.com/spreadsheets/d/1ytPD-f4a8CbNKTfMS3EqZOpBo9LWCk_NDKxJCgmpXA8/edit?usp=sharing'
        url_out = 'https://docs.google.com/spreadsheets/d/1ytPD-f4a8CbNKTfMS3EqZOpBo9LWCk_NDKxJCgmpXA8/export?format=csv'
        self.assertEqual(url_out, munge_url(url_in))

    def test_munge_url_gid(self):
        url_in = 'https://docs.google.com/spreadsheets/d/1ytPD-f4a8CbNKTfMS3EqZOpBo9LWCk_NDKxJCgmpXA8/edit#gid=1101521524'
        url_out = 'https://docs.google.com/spreadsheets/d/1ytPD-f4a8CbNKTfMS3EqZOpBo9LWCk_NDKxJCgmpXA8/export?format=csv&gid=1101521524'
        self.assertEqual(url_out, munge_url(url_in))
