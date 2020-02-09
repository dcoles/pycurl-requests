"""
Tests for Requests Sessions.

Note: We don't extensively test the various methods as they are exercised by
the tests for the tests for `api` (which itself is just a thin wrapper around a
single-use Session).
"""

import pycurl
import pytest

from pycurl_requests import requests
from pycurl_requests.tests.utils import *  # Used for fixtures


def test_session():
    s = requests.Session()
    try:
        if IS_PYCURL_REQUESTS:
            assert isinstance(s.curl, pycurl.Curl)
    finally:
        s.close()

    if IS_PYCURL_REQUESTS:
        assert s.curl is None


def test_session_contextmanager():
    with requests.Session() as s:
        if IS_PYCURL_REQUESTS:
            assert isinstance(s.curl, pycurl.Curl)

    if IS_PYCURL_REQUESTS:
        assert s.curl is None


def test_session_max_redirects(http_server):
    with pytest.raises(requests.TooManyRedirects):
        with requests.Session() as s:
            s.max_redirects = 3
            s.get(http_server.base_url + '/redirect')

    assert http_server.last_url.path == '/redirect3'
