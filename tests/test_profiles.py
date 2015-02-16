"""
Unit tests for the hxl.model module
David Megginson
October 2014

License: Public Domain
"""

import unittest
import tempfile
import os
from hxl_proxy.profiles import Profiles

class TestProfiles(unittest.TestCase):

    PROFILE = {'a': 'b', 'c': 'd'}

    def setUp(self):
        tmpfile = tempfile.mkstemp()
        os.close(tmpfile[0])
        self.filename = tmpfile[1]
        os.unlink(tmpfile[1])
        self.profiles = Profiles(self.filename)

    def tearDown(self):
        try:
            os.unlink(self.filename)
        except:
            pass

    def test_add(self):
        key = self.profiles.addProfile(self.PROFILE)
        self.assertEqual(6, len(key))
        self.assertEqual(self.PROFILE, self.profiles.getProfile(key))

    def test_update(self):
        new_profile = {'x': 'y'}
        key = self.profiles.addProfile(self.PROFILE)
        self.profiles.updateProfile(key, new_profile)
        self.assertEqual(new_profile, self.profiles.getProfile(key))

    def test_load(self):
        dict = {'a': 'b', 'c': 'd'}
        for n in range(0, 20):
            key = self.profiles.addProfile(self.PROFILE)
            self.assertEqual(self.PROFILE, self.profiles.getProfile(key))
