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
        self.assertEqual('SortFilter', source.__class__.__name__, "sort filter is fourth")
        self.assertEqual('SelectFilter', source.source.__class__.__name__, "select filter is third")
        self.assertEqual('CountFilter', source.source.source.__class__.__name__, "count filter is second")
        self.assertEqual('HXLReader', source.source.source.source.__class__.__name__, "reader is first")

    def test_null_profile(self):
        self.assertIsNone(setup_filters(None), "ok to pass None to setup_filters")

    def test_null_url(self):
        profile = Profile({})
        self.assertIsNone(setup_filters(profile), "ok to pass null URL to setup_filters")


class TestPipelineFunctions(unittest.TestCase):

    def setUp(self):
        self.input = ArrayInput(DATA)
        self.source = HXLReader(self.input)

    def test_add_add_filter(self):
        args = {
            'add-tag05': '#country',
            'add-header05': 'Country name',
            'add-value05': 'Mali',
            'add-before05': 'on'
        }
        filter = add_add_filter(self.source, args, 5)
        self.assertEqual('AddFilter', filter.__class__.__name__, "add filter from args")
        self.assertEqual(self.source, filter.source, "source OK")
        self.assertEqual(args['add-tag05'], filter.values[0][0].tag, "tag OK")
        self.assertEqual(args['add-value05'], filter.values[0][1], "value OK")
        self.assertTrue(filter.before, "before ok")

    def test_add_clean_filter(self):
        args = {
            'clean-whitespace-tags07': 'adm1,sector-cluster',
            'clean-upper-tags07': 'adm1_id,sector_id',
            'clean-lower-tags07': 'org_id,agesex_id',
            'clean-date-tags07': 'from_date,to_date',
            'clean-number-tags07': 'aff_num+idp,targeted_num'
        }
        filter = add_clean_filter(self.source, args, 7)
        self.assertEqual('CleanFilter', filter.__class__.__name__, "clean filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        self.assertEqual(['#adm1', '#sector-cluster'], [str(p) for p in filter.whitespace], "whitespace ok")
        self.assertEqual(['#adm1_id', '#sector_id'], [str(p) for p in filter.upper], "upper ok")
        self.assertEqual(['#org_id', '#agesex_id'], [str(p) for p in filter.lower], "lower ok")
        self.assertEqual(['#from_date', '#to_date'], [str(p) for p in filter.date], "date ok")
        self.assertEqual(['#aff_num+idp', '#targeted_num'], [str(p) for p in filter.number], "number ok")

    def test_add_count_filter(self):
        args = {
            'count-tags03': 'country,adm1,adm2+ocha',
            'count-aggregate-tag03': 'targeted_num+f'
        }
        filter = add_count_filter(self.source, args, 3)
        self.assertEqual('CountFilter', filter.__class__.__name__, "count filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        self.assertEqual(['#country', '#adm1', '#adm2+ocha'], [str(p) for p in filter.count_tags], "tags ok")
        self.assertEqual('#targeted_num+f', str(filter.aggregate_tag), "aggregate tag ok")
    
    def test_add_cut_filter(self):
        args = {
            'cut-include-tags01': 'org,adm1,adm2+pcode',
            'cut-exclude-tags01': 'email+external,name-ngo'
        }
        filter = add_cut_filter(self.source, args, 1)
        self.assertEqual('CutFilter', filter.__class__.__name__, "cut filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        self.assertEqual(['#org', '#adm1', '#adm2+pcode'], [str(p) for p in filter.include_tags], "include ok")
        self.assertEqual(['#email+external', '#name-ngo'], [str(p) for p in filter.exclude_tags], "exclude ok")

    @patch(URLOPEN_PATCH)
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
        self.assertEqual('MergeFilter', filter.__class__.__name__, "merge filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        self.assertEqual(['#adm2_id+pcode'], [str(p) for p in filter.keys], "keys ok")
        self.assertEqual(['#lat_deg', '#lon_deg'], [str(p) for p in filter.merge_tags], "merge tags ok")
        self.assertTrue(filter.replace, "replace flag ok")
        self.assertTrue(filter.overwrite, "overwrite flag ok")
        #self.assertEquals(args['merge-url11'], filter.merge_source._input) # need to be able to get URL

    def test_add_rename_filter(self):
        args = {
            'rename-oldtag08': 'loc-sensitive',
            'rename-newtag08': 'adm1',
            'rename-header08': 'Provincia'
        }
        filter = add_rename_filter(self.source, args, 8)
        self.assertEqual('RenameFilter', filter.__class__.__name__, "rename filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        for spec in filter.rename:
            # XXX assuming just one key, or else this will break badly
            self.assertEqual('#loc-sensitive', str(spec[0]), "original tag pattern ok")
            self.assertEqual('#adm1', spec[1].display_tag, "replacement tag pattern ok")
            self.assertEqual('Provincia', spec[1].header, "header ok")

    def test_add_select_filter(self):
        args = {
            'select-query09-01': 'sector+cluster=WASH',
            'select-query09-02': 'aff_num-adult<3',
            'select-query09-03': 'org!=UNICEF',
            'select-reverse09': 'on'
        }
        filter = add_select_filter(self.source, args, 9)
        self.assertEqual('SelectFilter', filter.__class__.__name__, "select filter from args")
        self.assertEqual(self.source, filter.source, "source ok")
        self.assertEqual(
            ['#sector+cluster', '#aff_num-adult', '#org'],
            [str(q.pattern) for q in filter.queries],
            "tag patterns ok"
        )
        self.assertEqual(
            [operator.eq, operator.lt, operator.ne],
            [q.op for q in filter.queries],
            "operators ok"
        )
        self.assertEqual(
            ['WASH', '3', 'UNICEF'],
            [str(q.value) for q in filter.queries],
            "values ok"
        )
        self.assertTrue(filter.reverse, "reverse flag ok")

    def test_add_sort_filter(self):
        args = {
            'sort-tags13': 'country,adm1,org+ngo',
            'sort-reverse13': 'on'
        }
        filter = add_sort_filter(self.source, args, 13)
        self.assertEqual('SortFilter', filter.__class__.__name__, "sort filter from args")
        self.assertEqual(
            ['#country', '#adm1', '#org+ngo'],
            [str(p) for p in filter.sort_tags],
            "tags ok"
        )
        self.assertTrue(filter.reverse, "reverse flag ok")

# end
