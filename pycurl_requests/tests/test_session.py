"""
Tests for Requests Sessions.

Note: We don't extensively test the various methods as they are exercised by
the tests for the tests for `api` (which itself is just a thin wrapper around a
single-use Session).
"""

from socket import timeout
import pycurl
import pytest
import os

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
            s.get(http_server.base_url + "/redirect")

    assert http_server.last_url.path == "/redirect3"


def test_session_parameters(http_server):
    with requests.Session() as s:
        s.params = {"a": 1, "b": 2}
        response = s.get(http_server.base_url + "/params", params={"b": 3, "c": 4})

    assert response.text == "a: 1\nb: 3\nc: 4"


COOKIEJAR2 = cookies.RequestsCookieJar()
COOKIEJAR2.update({"b": "Buzz", "c": "Boo"})


@pytest.mark.parametrize("cookies_", [{"b": "Buzz", "c": "Boo"}, COOKIEJAR2])
def test_session_cookies(http_server, cookies_):
    with requests.Session() as s:
        s.cookies.update({"a": "Fizz", "b": "Bazz"})
        response = s.get(http_server.base_url + "/cookies", cookies=cookies_)

    assert response.text == "a: Fizz\nb: Buzz\nc: Boo"


PYTEST_PROXY = os.getenv("PYTEST_PROXY", None)


@pytest.mark.skipif(
    (not PYTEST_PROXY),
    reason="Skip, PYTEST_PROXY environment variable is not set",
)
def test_proxy(http_server):
    origin_response = requests.get("https://httpbin.org/ip", timeout=10)
    origin_response.raise_for_status()
    origin_ip = origin_response.json().get("origin")

    proxy_response = requests.get(
        "https://httpbin.org/ip",
        proxies={"http": PYTEST_PROXY, "https": PYTEST_PROXY},
        timeout=10,
    )
    proxy_response.raise_for_status()
    proxy_ip = proxy_response.json().get("origin")

    assert isinstance(origin_response, requests.Response)
    assert isinstance(proxy_response, requests.Response)
    # TODO: this is not the best way to test proxy. Ideally test should look for other params that imply the proxy is bieng used
    assert origin_ip != proxy_ip, f"Proxy failed: IP is still {origin_ip}"
