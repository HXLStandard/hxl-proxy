"""Unit tests for HXL Proxy P-code support.
David Megginson
April 2018

Check the results of P-code requests.


License: Public Domain
"""

import io, unittest, werkzeug.exceptions
from hxl_proxy.pcodes import get_country_levels, extract_pcodes

class TestLevels(unittest.TestCase):
    # tests require network connectivity to work

    def test_good_levels(self):
        self.assertTrue('adm1' in get_country_levels('GIN'), "Have an adm1 level for GIN")
        self.assertTrue('adm2' in get_country_levels('BDI'), "Have an adm2 level for BDI")

    def test_bad_levels(self):
        seen_exception = False
        try:
            get_country_levels('XXX')
        except werkzeug.exceptions.NotFound:
            seen_exception = True
        self.assertTrue(seen_exception, "Bad country code XXX raises a NotFound exception")

class TestPcodes(unittest.TestCase):
    # tests require network connectivity to work

    def test_good_pcodes(self):
        self.try_pcodes('GIN', 'adm1')
        self.try_pcodes('gin', 'ADM1') # we want it to case-normalise

    def test_unavailable_pcodes(self):
        self.try_pcodes('GIN', 'adm4', expect_exception=True) # iTOS returns a result, but no P-codes

    def test_bad_country(self):
        self.try_pcodes('XXX', 'adm1', expect_exception=True)

    def test_bad_level(self):
        self.try_pcodes('GIN', 'adm6', expect_exception=True)

    def try_pcodes(self, country, admin_level, expect_exception=False):
        """Try loading P-codes.
        @param country: the country code (e.g. "GIN")
        @param admin_level: the HXL admin level (e.g. "adm1")
        @param expect_exception: if True, expect a NotFound exception (404)
        """
        with io.StringIO() as buffer:
            try:
                extract_pcodes(country, admin_level, buffer)
                self.assertFalse(expect_exception, 'Didn\'t get expected exception for {} {}'.format(country, admin_level))
                return buffer
            except werkzeug.exceptions.NotFound:
                self.assertTrue(expect_exception, 'Got unexpected exception for {} {}'.format(country, admin_level))
                return None
            

