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

VERSION = 1.0

# Properties not to be saved or exposed in args
BLACKLIST = ['password', 'password-repeat', 'name', 'description', 'cloneable']

class Profile(object):
    """Profile for a filter pipeline."""

    def __init__(self, args={}, passhash=None, name=None, description=None, cloneable=False):
        self.version = 1.0
        self.args = self._clean(args)
        self.passhash = passhash,
        self.name = name,
        self.description = description,
        self.cloneable = cloneable

    def set_password(self, password):
        """Assign a new password to this profile (None to clear)."""
        if password:
            self.passhash = make_md5(password)
        else:
            self.passhash = None

    def check_password(self, password):
        """Check the password for this profile."""
        # if none is set, also succeeds
        if not hasattr(self, 'passhash') or self.passhash is None:
            return True
        return (self.passhash == make_md5(password))

    def copy(self):
        """Make a safe copy of a profile, removing any sensitive fields."""
        profile = copy.copy(self)
        profile.args = self._clean(profile.args)
        return profile
    
    @staticmethod
    def _clean(args):
        """Return a clean copy of args, with any blacklisted keys removed."""
        return {key: args.get(key) for key in args if key not in BLACKLIST}

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
                return profile_map[str(key)].copy()
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
        key = gen_key()
        dict = shelve.open(self.filename)
        try:
            # check for collisions
            while key in dict:
                key = gen_key()
            dict[str(key)] = profile
            return key
        finally:
            dict.close()

def make_md5(s):
    """Return an MD5 hash for a string."""
    return hashlib.md5(s.encode('utf-8')).digest()

def gen_key():
    """
    Generate a pseudo-random, 6-character hash for use as a key.
    """
    salt = str(time.time() * random.random())
    encoded_hash = base64.urlsafe_b64encode(make_md5(salt))
    return encoded_hash[:6].decode('ascii')

# end
