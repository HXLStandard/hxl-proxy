"""Unit test suite for HXL proxy."""

import os

def resolve_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)
