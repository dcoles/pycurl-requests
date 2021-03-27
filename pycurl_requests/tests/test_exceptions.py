import pycurl
import pytest

from pycurl_requests import requests
from pycurl_requests.tests.utils import *


def test_connecterror_refused():
    with pytest.raises(requests.ConnectionError) as e:
        requests.get('http://127.0.0.1:9')

    exception = e.value  # type: requests.ConnectionError

    assert exception.response is None
    assert exception.request.url == 'http://127.0.0.1:9/'

    if IS_PYCURL_REQUESTS:
        assert isinstance(exception.__cause__, pycurl.error)
        assert exception.curl_code == pycurl.E_COULDNT_CONNECT
        assert 'Connection refused' in exception.curl_message


def test_connecterror_resolve():
    with pytest.raises(requests.ConnectionError) as e:
        requests.get('http://nosuchdomain.example.com')

    exception = e.value  # type: requests.ConnectionError

    assert exception.response is None
    assert exception.request.url == 'http://nosuchdomain.example.com/'

    if IS_PYCURL_REQUESTS:
        assert isinstance(exception.__cause__, pycurl.error)
        assert exception.curl_code == pycurl.E_COULDNT_RESOLVE_HOST
        # Some versions of curl return "Couldn't" instead of "Could not"
        assert 't resolve host' in exception.curl_message


def test_toomanyredirects(http_server):
    with pytest.raises(requests.TooManyRedirects) as e:
        with requests.Session() as s:
            s.max_redirects = 0
            s.get(http_server.base_url + '/redirect')

    exception = e.value  # type: requests.TooManyRedirects

    assert exception.response.status_code == 302
    assert exception.response.url == http_server.base_url + '/redirect'
    assert exception.request.url == http_server.base_url + '/redirect'

    if IS_PYCURL_REQUESTS:
        assert isinstance(exception.__cause__, pycurl.error)
        assert exception.curl_code == pycurl.E_TOO_MANY_REDIRECTS
        assert 'Maximum (0) redirects followed' in exception.curl_message
