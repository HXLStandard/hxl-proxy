"""
Persistent profile-storage module for the HXL Proxy

Started by David Megginson, February 2015
"""

import shelve
import base64
import hashlib
import random
import time

class Profiles:
    """
    Persistent storage for HXL Proxy profiles.
    All operations are atomic, opening and closing the shelf.
    """

    def __init__(self, filename):
        """
        Save the filename, but don't open the dict.
        @param filename the full path to the shelf.
        """
        self.filename = filename

    def getProfile(self, key):
        """
        Get an existing profile.
        @param key the string key for the profile.  
        @return the profile as an associative array.
        """
        dict = shelve.open(self.filename)
        try:
            if dict.has_key(key):
                return dict[key]
            else:
                return None
        finally:
            dict.close()

    def updateProfile(self, key, profile):
        """
        Update an existing profile.
        @param key the string key for the profile
        @param profile the profile as an associative array
        @return the key provided
        """
        dict = shelve.open(self.filename)
        try:
            dict[key] = profile
            return key
        finally:
            dict.close()

    def addProfile(self, profile):
        """
        Add a new profile.
        @param profile the profile as an associative array.
        @return the generated key for the new profile.
        """
        key = self._gen_key()
        dict = shelve.open(self.filename)
        try:
            # check for collisions
            while dict.has_key(key):
                key = self._gen_key()
            dict[key] = profile
            return key
        finally:
            dict.close()

    def _gen_key(self):
        """
        Generate a pseudo-random, 6-character hash for use as a key.
        """
        hash = base64.urlsafe_b64encode(hashlib.md5(str(time.time() * random.random())).digest())
        return hash[:6]

# end
