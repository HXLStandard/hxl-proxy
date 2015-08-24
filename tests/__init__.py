"""Unit test suite for HXL proxy."""

import os
import re

def mock_dataset(mock, status_code=200):
    """Will open last element of the URL path as a local file under ./files/"""
    def side_effect(url):
        filename = re.sub(r'^.*/([^/]+)$', '\\1', url)
        response = MockHTTPResponse(open(resolve_path('files/' + filename), 'rb'), status_code)
        return response
    mock.side_effect = side_effect

class MockHTTPResponse:
    """Mock a response from urllib"""

    def __init__(self, stream, status_code=200):
        self.stream = stream
        self.status_code = status_code
        self.status = status_code

    def read(self, n=None):
        return self.stream.read(n)

    def __enter__(self):
        pass

    def __exit__(self):
        self.stream.close()


def resolve_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)
