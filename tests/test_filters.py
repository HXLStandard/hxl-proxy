"""
Unit tests for hxl_proxy.filters module
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys

from hxl.io import ArrayInput, HXLReader

if sys.version_info < (3, 3):
    from mock import MagicMock
else:
    from unittest.mock import MagicMock

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
        self.assertEqual(['#country', '#adm1', '#adm2+ocha'], [str(p) for p in filter.count_tags])
        self.assertEqual('#targeted_num+f', str(filter.aggregate_tag))

# end
