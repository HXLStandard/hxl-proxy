"""Unit test suite for HXL proxy."""

import os
import re
import hxl

def mock_dataset(mock, status_code=200):
    """Will open last element of the URL path as a local file under ./files/"""
    def side_effect(url, allow_local=False):
        if re.match(r'http:', url):
            filename = re.sub(r'^.*/([^/]+)$', '\\1', url)
            path = resolve_path('files/' + filename)
        else:
            path = url
        return open(path, 'rb')
    mock.side_effect = side_effect

def resolve_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)
