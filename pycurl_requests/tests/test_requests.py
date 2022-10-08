import datetime
import sys

import pytest

from pycurl_requests import cookies
from pycurl_requests import requests
from pycurl_requests.tests.utils import *  # Used for fixtures

if IS_PYCURL_REQUESTS:
    from pycurl_requests.structures import CaseInsensitiveDict
else:
    from requests.structures import CaseInsensitiveDict

try:
    from urllib3.util.timeout import Timeout
except ImportError:
    def Timeout(total=None, connect=None, read=None):
        return NotImplemented


def test_get(http_server):
    response = requests.get(http_server.base_url + '/hello')
    assert isinstance(response, requests.Response)
    response.raise_for_status()

    assert http_server.last_url.path == '/hello'

    assert isinstance(response.request, requests.PreparedRequest)
    assert response.request.method == 'GET'
    assert response.request.url == http_server.base_url + '/hello'
    assert response.request.path_url == '/hello'
    assert isinstance(response.request.headers, CaseInsensitiveDict)
    assert response.request.body is None

    assert response.elapsed > datetime.timedelta(0)
    assert response.url.endswith('/hello')
    assert response.status_code == 200
    assert response.reason == 'OK'
    assert response.headers['content-type'] == 'text/html; charset=UTF-8'
    assert response.headers['content-length'] == str(len(b'Hello\nWorld\n'))
    assert response.encoding.lower() == 'utf-8'
    assert response.apparent_encoding == 'ascii'
    assert response.content == b'Hello\nWorld\n'
    assert response.text == 'Hello\nWorld\n'


def test_get_notfound(http_server):
    response = requests.get(http_server.base_url + '/not_found')
    with pytest.raises(requests.HTTPError) as err:
        response.raise_for_status()
    assert err.value.response.status_code == 404


def test_get_params(http_server):
    response = requests.get(http_server.base_url + '/params', params={'q': 'foo', 'r': 'bar'})
    response.raise_for_status()

    assert response.text == 'q: foo\nr: bar'


@pytest.mark.parametrize('sequence_type', [list, tuple])
def test_get_params_list(http_server, sequence_type):
    response = requests.get(http_server.base_url + '/params', params=sequence_type([('q', 'foo'), ('r', 'bar'), ('q', 'baz')]))
    response.raise_for_status()

    assert response.text == 'q: foo\nr: bar\nq: baz'


def test_get_headers(http_server):
    response = requests.get(http_server.base_url + '/headers', headers={'Foo': 'foo', 'Bar': b'bar', 'Baz': '\U0001F60A'.encode()})
    response.raise_for_status()

    headers = CaseInsensitiveDict()
    for line in response.text.splitlines():
        name, value = line.split(':', 1)
        headers[name] = value.strip()

    assert headers['Foo'] == 'foo'
    assert headers['Bar'] == 'bar'
    assert headers['Baz'].encode('iso-8859-1') == '\U0001F60A'.encode()  # Yes, this is mojibake

def test_get_response_headers(http_server):
    response = requests.get(http_server.base_url + '/response/headers', params=[('Foo', 'foo'), ('FooBar', 'foo'), ('FooBar', 'bar')])
    response.raise_for_status()

    assert response.headers['Foo'] == 'foo'
    assert response.headers['FooBar'] == 'foo, bar'


def test_get_response_set_cookie(http_server):
    response = requests.get(
        http_server.base_url + '/response/headers',
        params=[
            ('Set-Cookie', 'test!'),
            ('Set-Cookie', 'PHPSESSID=8536fl1c5igh89aqsjuf3l40jm; path=/'),
            ('Set-Cookie', 'TestCookie=%3A%202595; expires=Thu, 01-Jul-2021 07:56:03 GMT; Max-Age=3600'),
        ])
    response.raise_for_status()

    assert response.headers['Set-Cookie'] == 'test!, PHPSESSID=8536fl1c5igh89aqsjuf3l40jm; path=/, TestCookie=%3A%202595; expires=Thu, 01-Jul-2021 07:56:03 GMT; Max-Age=3600'


def test_get_redirect_nofollow(http_server):
    response = requests.get(http_server.base_url + '/redirect', allow_redirects=False)
    response.raise_for_status()

    assert response.request.url.endswith('/redirect')
    assert response.url.endswith('/redirect')
    assert response.status_code == 302
    assert response.text == 'Redirecting...\n'


def test_get_redirect(http_server):
    with pytest.raises(requests.TooManyRedirects) as e:
        requests.get(http_server.base_url + '/redirect')

    # max_redirects defaults to 30
    assert http_server.last_url.path == '/redirect30'


def test_get_json(http_server):
    response = requests.get(http_server.base_url + '/json')
    response.raise_for_status()

    assert response.json() == {'Hello': 'World'}


def test_get_iter_content(http_server):
    response = requests.get(http_server.base_url + '/hello')
    response.raise_for_status()

    assert response.content == b'Hello\nWorld\n'
    it = response.iter_content(5, decode_unicode=True)
    assert next(it) == 'Hello'
    assert next(it) == '\nWorl'
    assert next(it) == 'd\n'
    with pytest.raises(StopIteration):
        assert next(it)


@pytest.mark.parametrize('delimiter', [None, '\n'])
def test_get_iter_lines(delimiter, http_server):
    response = requests.get(http_server.base_url + '/hello')
    response.raise_for_status()

    assert response.content == b'Hello\nWorld\n'
    it = response.iter_lines(5, decode_unicode=True, delimiter=delimiter)
    assert next(it) == 'Hello'
    assert next(it) == 'World'
    if delimiter is not None:
        assert next(it) == ''
    with pytest.raises(StopIteration):
        assert next(it)


TEST_COOKIEJAR = cookies.RequestsCookieJar()
TEST_COOKIEJAR.update({'a': 'Fizz', 'b': 'Bazz'})


@pytest.mark.parametrize('cookies_', [{'x': 'Foo', 'y': 'Bar'}, TEST_COOKIEJAR])
def test_cookies(http_server, cookies_):
    response = requests.get(http_server.base_url + '/cookies', cookies=cookies_)

    cookiejar = cookies.RequestsCookieJar()
    cookiejar.update(cookies_)
    assert response.text == '\n'.join('{}: {}'.format(*item) for item in cookiejar.items())


# Timeouts should go last, because '/slow' hangs the HTTP server
@pytest.mark.parametrize('timeout', [0.1, (None, 0.1)])
def test_get_timeout(http_server, timeout):
    with pytest.raises(requests.Timeout):
        requests.get(http_server.base_url + '/slow', timeout=timeout)


@pytest.mark.skipif('urllib3' not in sys.modules, reason='urllib3 not available')
@pytest.mark.parametrize('timeout', [Timeout(read=0.1), Timeout(total=0.1)])
def test_get_timeout_urllib3(http_server, timeout):
    with pytest.raises(requests.Timeout):
        requests.get(http_server.base_url + '/slow', timeout=timeout)


@pytest.mark.parametrize('timeout', [0.1, (0.1, None)])
def test_get_connect_timeout(http_server, timeout):
    with pytest.raises(requests.Timeout):
        # Use RFC-5737 TEST-NET-1 address since it should always be unreachable
        requests.get('http://192.0.2.1', timeout=timeout)
        requests.get(http_server.base_url + '/slow', timeout=timeout)


@pytest.mark.skipif('urllib3' not in sys.modules, reason='urllib3 not available')
@pytest.mark.parametrize('timeout', [Timeout(connect=0.1), Timeout(total=0.1)])
def test_get_connect_timeout_urllib3(http_server, timeout):
    with pytest.raises(requests.Timeout):
        # Use RFC-5737 TEST-NET-1 address since it should always be unreachable
        requests.get('http://192.0.2.1', timeout=timeout)
        requests.get(http_server.base_url + '/slow', timeout=timeout)
