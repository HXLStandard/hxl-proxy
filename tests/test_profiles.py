"""
Unit tests for hxl-proxy profile module
David Megginson
March 2015

License: Public Domain
"""

import unittest
import sys
import os
import tempfile

if sys.version_info < (3, 3):
    from mock import MagicMock
else:
    from unittest.mock import MagicMock

from hxl_proxy.profiles import Profile, ProfileManager

ARGS = {
    'arg1': 'value1',
    'arg2': 'value2',
    'arg3': 'value3'
}

PASSWORD = 'abc123'

# will hold global mock for Flask app object
app = None

class TestProfile(unittest.TestCase):

    def setUp(self):
        self.profile = Profile(ARGS)
        self.profile.set_password(PASSWORD)

    def test_actual_password_not_stored(self):
        self.assertNotEqual(PASSWORD, self.profile.passhash, "Shouldn't store actual password.")

    def test_same_password_matches(self):
        self.assertTrue(self.profile.check_password(PASSWORD), "Same password should match.")

    def test_different_password_fails(self):
        self.assertFalse(self.profile.check_password('X' + PASSWORD), "Different password should fail.")

class TestProfileManager(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile(delete=True) as file:
            self.filename = file.name
        self.manager = ProfileManager(self.filename)
        self.profile = Profile(ARGS)
        self.key = self.manager.add_profile(self.profile)

    def tearDown(self):
        os.remove(self.filename)

    def test_profile_not_present(self):
        self.assertFalse(self.manager.get_profile('X' + self.key))

    def test_profile_exists(self):
        profile = self.manager.get_profile(self.key)
        self.assertTrue(profile.args)
        self.assertEqual(ARGS, profile.args)

    def test_update_profile(self):
        self.profile.args['XXX'] = 'YYY'
        self.assertNotEqual(self.profile.args, self.manager.get_profile(self.key).args)
        self.manager.update_profile(self.key, self.profile)
        self.assertEqual(self.profile.args, self.manager.get_profile(self.key).args)
