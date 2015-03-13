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

from hxl_proxy.profiles import Profile, get_profile, add_profile, update_profile

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

class TestFunctions(unittest.TestCase):

    def setUp(self):
        self.filename = tempfile.NamedTemporaryFile(delete=False).name
        app = MagicMock(side_effect=lambda: { PROFILE_FILE: self.filename })
        self.profile = Profile(ARGS)
        self.key = add_profile(self.profile)

    def tearDown(self):
        os.remove(self.filename)

    def test_profile_not_present(self):
        self.assertFalse(get_profile('X' + self.key))

    def test_profile_exists(self):
        profile = get_profile(self.key)
        self.assertTrue(profile.args)
        self.assertEqual(ARGS, profile.args)

    def test_update_profile(self):
        self.profile.args['XXX'] = 'YYY'
        self.assertNotEqual(self.profile.args, get_profile(self.key).args)
        update_profile(self.key, self.profile)
        self.assertEqual(self.profile.args, get_profile(self.key).args)
