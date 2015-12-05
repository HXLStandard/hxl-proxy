"""Unit test suite for HXL proxy."""

import os
import re
import hxl
import unittest.mock

#
# Mock URL access for local testing
#

def mock_open_url(url, allow_local=False):
    """
    Open local files instead of URLs.
    If it's a local file path, leave it alone; otherwise,
    open as a file under ./files/
    """
    if re.match(r'https?:', url):
        # Looks like a URL
        filename = re.sub(r'^.*/([^/]+)$', '\\1', url)
        path = resolve_path('files/' + filename)
    else:
        # Assume it's a file
        path = url
    return open(path, 'rb')

def resolve_path(filename):
    """Resolve a relative path against this module's directory."""
    return os.path.join(os.path.dirname(__file__), filename)

URL_MOCK_TARGET = 'hxl.io.make_stream'

URL_MOCK_OBJECT = unittest.mock.Mock()
URL_MOCK_OBJECT.side_effect = mock_open_url

