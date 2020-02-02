import datetime
import http.client
import json
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

import pycurl_requests as requests


@pytest.fixture(scope='module')
def http_server():
    httpd = HTTPServer(('127.0.0.1', 0), HTTPRequestHandler)
    httpd.base_url = 'http://{}:{}'.format(*httpd.server_address)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join()


class HTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute HTTP logging
        pass

    def do_GET(self):
        if self.url.path == '/hello':
            self.response('Hello\nWorld\n')
        elif self.url.path == '/params':
            self.response('\n'.join(('{}: {}'.format(n, v)
                                     for n, v in urllib.parse.parse_qsl(self.url.query))))
        elif self.url.path == '/headers':
            self.response('\n'.join(('{}: {}'.format(n, v)
                                     for n, v in self.headers.items())))
        elif self.url.path == '/redirect':
            self.response('Redirecting...\n', (302, 'Found'),
                          headers={'Location': '/redirected'})
        elif self.url.path == '/redirected':
            self.response('Redirected\n')
        elif self.url.path == '/json':
            self.response(json.dumps({'Hello': 'World'}), content_type='application/json')
        else:
            self.send_error(404, 'Not Found')

    @property
    def url(self):
        if not hasattr(self, '_url'):
            # For some annoying reason this can't be set in `__init__`
            self._url = urllib.parse.urlsplit(self.path)

        return self._url

    def response(self, body, status=None, content_type=None, headers=None):
        body = body.encode('utf-8') if isinstance(body, str) else body
        status = status or (200, 'OK')
        content_type = content_type or 'text/html; charset=UTF-8'
        headers = headers or {}
        self.send_response(*status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()

        self.wfile.write(body)


def test_get(http_server):
    response = requests.get(http_server.base_url + '/hello')
    assert isinstance(response, requests.Response)
    response.raise_for_status()

    assert isinstance(response.request, requests.PreparedRequest)
    assert response.request.method == 'GET'
    assert response.request.url == http_server.base_url + '/hello'
    assert response.request.path_url == '/hello'
    assert isinstance(response.request.headers, http.client.HTTPMessage)
    assert response.request.body is None

    assert response.elapsed > datetime.timedelta(0)
    assert response.url.endswith('/hello')
    assert response.status_code == 200
    assert response.reason == 'OK'
    assert response.headers['content-type'] == 'text/html; charset=UTF-8'
    assert response.headers['content-length'] == str(len(b'Hello\nWorld\n'))
    assert response.encoding == 'utf-8'
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


def test_get_headers(http_server):
    response = requests.get(http_server.base_url + '/headers', headers={'Foo': 'foo', 'Bar': 'bar'})
    response.raise_for_status()
    print(response.text)

    headers = http.client.HTTPMessage()
    for line in response.text.splitlines():
        name, value = line.split(':', 1)
        headers[name] = value.strip()

    assert headers['Foo'] == 'foo'
    assert headers['Bar'] == 'bar'


def test_get_redirect_nofollow(http_server):
    response = requests.get(http_server.base_url + '/redirect', allow_redirects=False)
    response.raise_for_status()

    assert response.url.endswith('/redirect')
    assert response.status_code == 302
    assert response.text == 'Redirecting...\n'


def test_get_redirect(http_server):
    response = requests.get(http_server.base_url + '/redirect')
    response.raise_for_status()

    assert response.url.endswith('/redirected')
    assert response.text == 'Redirected\n'


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
    assert next(it) == ''
    with pytest.raises(StopIteration):
        assert next(it)
