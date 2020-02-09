import pycurl
import pytest

from pycurl_requests import requests


def test_connecterror_refused():
    with pytest.raises(requests.ConnectionError) as e:
        requests.get('http://127.0.0.1:0')

    assert isinstance(e.value.__cause__, pycurl.error)
    assert e.value.curl_code == pycurl.E_COULDNT_CONNECT
    assert 'Connection refused' in e.value.curl_message


def test_connecterror_resolve():
    with pytest.raises(requests.ConnectionError) as e:
        requests.get('http://nosuchdomain.example.com')

    assert isinstance(e.value.__cause__, pycurl.error)
    assert e.value.curl_code == pycurl.E_COULDNT_RESOLVE_HOST
    assert 'Could not resolve host' in e.value.curl_message
