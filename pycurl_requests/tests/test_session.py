"""
Tests for Requests Sessions.

Note: We don't extensively test the various methods as they are exercised by
the tests for the tests for `api` (which itself is just a thin wrapper around a
single-use Session).
"""

import pycurl
import pytest

from pycurl_requests import requests
from pycurl_requests import cookies
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


def test_session_parameters(http_server):
    with requests.Session() as s:
        s.params = {'a': 1, 'b': 2}
        response = s.get(http_server.base_url + '/params', params={'b': 3, 'c': 4})

    assert response.text == 'a: 1\nb: 3\nc: 4'


COOKIEJAR1 = cookies.RequestsCookieJar()
COOKIEJAR1.update({'a': 'Fizz', 'b': 'Bazz'})

COOKIEJAR2 = cookies.RequestsCookieJar()
COOKIEJAR2.update({'b': 'Buzz', 'c': 'Boo'})


@pytest.mark.parametrize('cookies_', [{'b': 'Buzz', 'c': 'Boo'}, COOKIEJAR2])
def test_session_cookies(http_server, cookies_):
    with requests.Session() as s:
        s.cookies = COOKIEJAR1
        response = s.get(http_server.base_url + '/cookies', cookies=cookies_)

    assert response.text == 'a: Fizz\nb: Buzz\nc: Boo'
