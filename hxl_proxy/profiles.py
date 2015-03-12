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

from hxl_proxy import app

class Profile(object):

    def __init__(self, args):
        self.version = 1.0
        self.args = args

    def set_password(self, password):
        """Assign a new password to this profile (None to clear)."""
        if password:
            self.passhash = hashlib.md5(password).digest()
        else:
            self.passhash = None

    def check_password(self, password):
        """Check the password for this profile."""
        # if none is set, also succeeds
        if not hasattr(self, 'passhash') or self.passhash is None:
            return True
        return (self.passhash == hashlib.md5(password).digest())

def make_profile(args):
    return Profile(args)

def get_profile(key):
    """
    Get an existing profile.
    @param key the string key for the profile.  
    @return the profile as an associative array.
    """
    key = str(key)
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        if key in dict:
            return copy.copy(dict[key])
        else:
            return None
    finally:
        dict.close()

def update_profile(key, profile):
    """
    Update an existing profile.
    @param key the string key for the profile
    @param profile the profile as an associative array
    @return the key provided
    """
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        dict[str(key)] = profile
        return key
    finally:
        dict.close()

def add_profile(profile):
    """
    Add a new profile.
    @param profile the profile as an associative array.
    @return the generated key for the new profile.
    """
    key = _gen_key()
    dict = shelve.open(app.config['PROFILE_FILE'])
    try:
        # check for collisions
        while key in dict:
            key = _gen_key()
        dict[str(key)] = profile
        return key
    finally:
        dict.close()

def _gen_key():
    """
    Generate a pseudo-random, 6-character hash for use as a key.
    """
    hash = base64.urlsafe_b64encode(hashlib.md5(str(time.time() * random.random())).digest())
    return hash[:6]

# end
