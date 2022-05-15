"""Unit test suite for HXL proxy."""

import os
import re
import hxl
import unittest.mock

#
# Mock URL access for local testing
#

def mock_open_url(url, allow_local=False, timeout=None, verify_ssl=True, http_headers=None):
    """
    Open local files instead of URLs.
    If it's a local file path, leave it alone; otherwise,
    open as a file under ./files/

    This is meant as a side effect for unittest.mock.Mock

    Arguments are the same as hxl.input.open_url_or_file(), which this replaces
    """

    if re.match(r'https?:', url):
        if re.match('.*/private/.*', url):
            # fake a URL that needs authorisation (if it has /private/ in it)
            # if there's no 'Authorization' header, raise an exception
            if http_headers is None or not "Authorization" in http_headers:
                raise hxl.input.HXLAuthorizationException('Need Authorization header', url)
        # Looks like a URL
        filename = re.sub(r'^.*/([^/]+)$', '\\1', url)
        path = resolve_path('files/' + filename)
    else:
        # Assume it's a file
        path = url
    return (open(path, 'rb'), None, None, None)

def resolve_path(filename):
    """Resolve a relative path against this module's directory."""
    return os.path.join(os.path.dirname(__file__), filename)

# Target function to replace for mocking URL access.
URL_MOCK_TARGET = 'hxl.input.open_url_or_file'

# Mock object to replace hxl.input.open_url_or_file
URL_MOCK_OBJECT = unittest.mock.Mock()
URL_MOCK_OBJECT.side_effect = mock_open_url

# end
