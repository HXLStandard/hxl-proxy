"""
Persistent profile-storage module for the HXL Proxy

Started by David Megginson, February 2015
"""

import shelve
import base64
import hashlib
import random
import time
import copy

VERSION=1.0

class Profile(object):
    """Profile for a filter pipeline."""

    def __init__(self, args):
        self.version = 1.0
        self.args = args
        self.passhash = None

    def set_password(self, password):
        """Assign a new password to this profile (None to clear)."""
        if password:
            self.passhash = _make_md5(password)
        else:
            self.passhash = None

    def check_password(self, password):
        """Check the password for this profile."""
        # if none is set, also succeeds
        if not hasattr(self, 'passhash') or self.passhash is None:
            return True
        return (self.passhash == _make_md5(password))

class ProfileManager:
    """Manage saved filter pipelines."""

    def __init__(self, filename):
        """
        Construct a new profile manager.
        @param filename The base filename for an on-disk key database file.
        """
        self.filename = filename

    def get_profile(self, key):
        """
        Get an existing profile.
        @param key the string key for the profile.  
        @return the profile as an associative array.
        """
        profile_map = shelve.open(self.filename)
        try:
            if str(key) in profile_map:
                return copy.copy(profile_map[str(key)])
            else:
                return None
        finally:
            profile_map.close()

    def update_profile(self, key, profile):
        """
        Update an existing profile.
        @param key the string key for the profile
        @param profile the profile as an associative array
        @return the key provided
        """
        dict = shelve.open(self.filename)
        try:
            dict[str(key)] = profile
            return str(key)
        finally:
            dict.close()

    def add_profile(self, profile):
        """
        Add a new profile.
        @param profile the profile as an associative array.
        @return the generated key for the new profile.
        """
        key = _gen_key()
        dict = shelve.open(self.filename)
        try:
            # check for collisions
            while key in dict:
                key = _gen_key()
            dict[str(key)] = profile
            return key
        finally:
            dict.close()

def _make_md5(s):
    """Return an MD5 hash for a string."""
    return hashlib.md5(s.encode('utf-8')).digest()

def _gen_key():
    """
    Generate a pseudo-random, 6-character hash for use as a key.
    """
    salt = str(time.time() * random.random())
    encoded_hash = base64.urlsafe_b64encode(_make_md5(salt))
    return str(encoded_hash[:6])

# end
