"""
Unit tests for hxl_proxy.filters module
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys
import urllib # needed for @patch

if sys.version_info < (3, 3):
    from mock import patch
else:
    from unittest.mock import patch

from hxl.io import ArrayInput, HXLReader
from hxl_proxy.filters import *

DATA = [
    ['#org', '#sector', '#country'],
    ['Org A', 'WASH', 'Country A'],
    ['Org B', 'Health', 'Country B'],
    ['Org C', 'Protection', 'Country A']
]


class TestPipelineFunctions(unittest.TestCase):

    def setUp(self):
        self.input = ArrayInput(DATA)
        self.source = HXLReader(self.input)

    def test_add_add_filter(self):
        """Test constructing a hxl.filters.AddFilter from HTTP parameters."""
        args = {
            'add-tag05': '#country',
            'add-header05': 'Country name',
            'add-value05': 'Mali',
            'add-before05': 'on'
        }
        filter = add_add_filter(self.source, args, 5)
        self.assertEqual('AddFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(args['add-tag05'], filter.values[0][0].tag)
        self.assertEqual(args['add-value05'], filter.values[0][1])
        self.assertTrue(filter.before)

    def test_add_clean_filter(self):
        """Test constructing a hxl.filters.CleanFilter from HTTP parameters."""
        args = {
            'clean-whitespace-tags07': 'adm1,sector-cluster',
            'clean-upper-tags07': 'adm1_id,sector_id',
            'clean-lower-tags07': 'org_id,agesex_id',
            'clean-date-tags07': 'from_date,to_date',
            'clean-number-tags07': 'aff_num+idp,targeted_num'
        }
        filter = add_clean_filter(self.source, args, 7)
        self.assertEqual('CleanFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#adm1', '#sector-cluster'], [str(p) for p in filter.whitespace])
        self.assertEqual(['#adm1_id', '#sector_id'], [str(p) for p in filter.upper])
        self.assertEqual(['#org_id', '#agesex_id'], [str(p) for p in filter.lower])
        self.assertEqual(['#from_date', '#to_date'], [str(p) for p in filter.date])
        self.assertEqual(['#aff_num+idp', '#targeted_num'], [str(p) for p in filter.number])

    def test_add_count_filter(self):
        """Test constructing a hxl.filters.CountFilter from HTTP parameters."""
        args = {
            'count-tags03': 'country,adm1,adm2+ocha',
            'count-aggregate-tag03': 'targeted_num+f'
        }
        filter = add_count_filter(self.source, args, 3)
        self.assertEqual('CountFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#country', '#adm1', '#adm2+ocha'], [str(p) for p in filter.count_tags])
        self.assertEqual('#targeted_num+f', str(filter.aggregate_tag))
    
    def test_add_cut_filter(self):
        args = {
            'cut-include-tags01': 'org,adm1,adm2+pcode',
            'cut-exclude-tags01': 'email+external,name-ngo'
        }
        filter = add_cut_filter(self.source, args, 1)
        self.assertEqual('CutFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#org', '#adm1', '#adm2+pcode'], [str(p) for p in filter.include_tags])
        self.assertEqual(['#email+external', '#name-ngo'], [str(p) for p in filter.exclude_tags])

    @patch('urllib.urlopen')
    def test_add_merge_filter(self, urlopen_mock):
        urlopen_mock.return_value = 'x'
        args = {
            'merge-keys11': 'adm2_id+pcode',
            'merge-tags11': 'lat_deg,lon_deg',
            'merge-replace11': 'on',
            'merge-overwrite11': 'on',
            'merge-url11': 'http://example.org/data.csv'
        }
        filter = add_merge_filter(self.source, args, 11)
        self.assertEqual('MergeFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#adm2_id+pcode'], [str(p) for p in filter.keys])
        self.assertEqual(['#lat_deg', '#lon_deg'], [str(p) for p in filter.merge_tags])
        self.assertTrue(filter.replace)
        self.assertTrue(filter.overwrite)
        #self.assertEquals(args['merge-url11'], filter.merge_source._input) # need to be able to get URL

# end
