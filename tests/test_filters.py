"""
Unit tests for hxl_proxy.filters module
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys
import operator
import urllib # needed for @patch

if sys.version_info < (3, 3):
    from mock import patch
    URLOPEN_PATCH = 'urllib.urlopen'
else:
    from unittest.mock import patch
    URLOPEN_PATCH = 'urllib.request.urlopen'

from hxl.model import TagPattern
from hxl.io import ArrayInput, HXLReader
from hxl_proxy.filters import *
from hxl_proxy.profiles import Profile

DATA = [
    ['#org', '#sector', '#country'],
    ['Org A', 'WASH', 'Country A'],
    ['Org B', 'Health', 'Country B'],
    ['Org C', 'Protection', 'Country A']
]

class TestSetupFilters(unittest.TestCase):

    def test_filters(self):
        """Test the normal case of a filter pipeline."""
        args = {
            'url': 'http://example.org/data.csv',
            'filter_count': 3,
            'filter01': 'count',
            'count-tags02': 'adm1,adm2',
            'filter02': 'select',
            'select-query02-01': 'country=Liberia',
            'filter03': 'sort',
            'sort-tags02': 'adm1,adm2'
        }
        profile = Profile(args)
        source = setup_filters(profile)

        # check the whole pipeline
        self.assertEqual('SortFilter', source.__class__.__name__)
        self.assertEqual('SelectFilter', source.source.__class__.__name__)
        self.assertEqual('CountFilter', source.source.source.__class__.__name__)
        self.assertEqual('HXLReader', source.source.source.source.__class__.__name__)

    def test_null_profile(self):
        """Test passing a null profile to setup_filters"""
        self.assertIsNone(setup_filters(None))

    def test_null_url(self):
        "Test passing a profile with no url."
        profile = Profile({})
        self.assertIsNone(setup_filters(profile))


class TestMakeInput(unittest.TestCase):

    def test_plain_input(self):
        """Test setting up normal URL input."""
        args = {
            'url': 'http://example.org/data.csv'
        }
        input = make_input(args)
        self.assertEqual('URLInput', input.__class__.__name__)

    def test_tagger_input(self):
        """Test setting up normal auto-tagger input."""
        args = {
            'url': 'http://example.org/data.csv',
            'filter01': 'tagger',
            'tagger-01-tag': '#org',
            'tagger-01-header': 'Organisation',
        }
        input = make_input(args)
        self.assertEqual('Tagger', input.__class__.__name__)
        self.assertEqual([('organisation', '#org')], input.specs)


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
        """Test constructing a hxl.filters.CutFilter from HTTP parameters."""
        args = {
            'cut-include-tags01': 'org,adm1,adm2+pcode',
            'cut-exclude-tags01': 'email+external,name-ngo'
        }
        filter = add_cut_filter(self.source, args, 1)
        self.assertEqual('CutFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#org', '#adm1', '#adm2+pcode'], [str(p) for p in filter.include_tags])
        self.assertEqual(['#email+external', '#name-ngo'], [str(p) for p in filter.exclude_tags])

    @patch(URLOPEN_PATCH)
    def test_add_merge_filter(self, urlopen_mock):
        """Test constructing a hxl.filters.MergeFilter from HTTP parameters."""
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

    def test_add_rename_filter(self):
        """Test constructing a hxl.filters.RenameFilter from HTTP parameters."""
        args = {
            'rename-oldtag08': 'loc-sensitive',
            'rename-newtag08': 'adm1',
            'rename-header08': 'Provincia'
        }
        filter = add_rename_filter(self.source, args, 8)
        self.assertEqual('RenameFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        for key in filter.rename:
            # XXX assuming just one key, or else this will break badly
            self.assertEqual('#loc-sensitive', str(key))
            self.assertEqual('#adm1', str(filter.rename[key][0]))
            self.assertEqual('Provincia', filter.rename[key][1])

    def test_add_select_filter(self):
        """Test constructing a hxl.filters.SelectFilter from HTTP parameters."""
        args = {
            'select-query09-01': 'sector+cluster=WASH',
            'select-query09-02': 'aff_num-adult<3',
            'select-query09-03': 'org!=UNICEF',
            'select-reverse09': 'on'
        }
        filter = add_select_filter(self.source, args, 9)
        self.assertEqual('SelectFilter', filter.__class__.__name__)
        self.assertEqual(self.source, filter.source)
        self.assertEqual(['#sector+cluster', '#aff_num-adult', '#org'], [str(q.pattern) for q in filter.queries])
        self.assertEqual([operator.eq, operator.lt, operator.ne], [q.op for q in filter.queries])
        self.assertEqual(['WASH', '3', 'UNICEF'], [str(q.value) for q in filter.queries])
        self.assertTrue(filter.reverse)

    def test_add_sort_filter(self):
        """Test constructing a hxl.filters.SortFilter from HTTP parameters."""
        args = {
            'sort-tags13': 'country,adm1,org+ngo',
            'sort-reverse13': 'on'
        }
        filter = add_sort_filter(self.source, args, 13)
        self.assertEqual('SortFilter', filter.__class__.__name__)
        self.assertEqual(['#country', '#adm1', '#org+ngo'], [str(p) for p in filter.sort_tags])
        self.assertTrue(filter.reverse)

# end
