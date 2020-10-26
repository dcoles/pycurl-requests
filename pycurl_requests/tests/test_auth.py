import base64

import pycurl_requests as requests
from pycurl_requests.tests.utils import *  # Used for fixtures

from pycurl_requests import auth


def test_basic_auth(http_server):
    resp = requests.get(http_server.base_url + '/auth', auth=auth.HTTPBasicAuth('user', 'pass'))
    assert resp.status_code == 200
    assert resp.text == 'Authorization: Basic dXNlcjpwYXNz\n'


def test_basic_auth_tuple(http_server):
    resp = requests.get(http_server.base_url + '/auth', auth=('user', 'pass'))
    assert resp.status_code == 200
    assert resp.text == 'Authorization: Basic dXNlcjpwYXNz\n'


def test_user_auth(http_server):
    class Auth(auth.AuthBase):
        """User-defined auth"""
        def __call__(self, r):
            r.headers['Authorization'] = 'Basic dXNlcjpwYXNz'
            return r

    resp = requests.get(http_server.base_url + '/auth', auth=Auth())
    assert resp.status_code == 200
    assert resp.text == 'Authorization: Basic dXNlcjpwYXNz\n'


def test_auth_session(http_server):
    with requests.Session() as s:
        s.auth = auth.HTTPBasicAuth('user', 'pass')

        resp = s.get(http_server.base_url + '/auth')
        assert resp.status_code == 200
        assert resp.text == 'Authorization: Basic dXNlcjpwYXNz\n'


def test_auth_session_tuple(http_server):
    with requests.Session() as s:
        s.auth = ('user', 'pass')

        resp = s.get(http_server.base_url + '/auth')
        assert resp.status_code == 200
        assert resp.text == 'Authorization: Basic dXNlcjpwYXNz\n'


