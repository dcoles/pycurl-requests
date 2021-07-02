"""
Test helper utilities.
"""

import json
import threading
import time
from http import cookies
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl

import pytest

from pycurl_requests import requests

__all__ = ['IS_PYCURL_REQUESTS', 'http_server']

#: Is this _really_ PyCurl-Requests?
#: Should be used when testing for PyCurl-Requests extensions.
IS_PYCURL_REQUESTS = requests.__name__ == 'pycurl_requests'


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
        # Remember last requested URL
        self.server.last_url = self.url

        if self.url.path.startswith('/redirect'):
            self.do_GET_redirect()
        else:
            path = self.url.path[1:].replace('/', '_')
            getattr(self, f'do_GET_{path}', self.do_HTTP_404)()

    def do_GET_hello(self):
        self.response('Hello\nWorld\n')

    def do_GET_params(self):
        self.response('\n'.join(('{}: {}'.format(n, v) for n, v in parse_qsl(self.url.query))))

    def do_GET_headers(self):
        self.response('\n'.join(('{}: {}'.format(n, v) for n, v in self.headers.items())))

    def do_GET_redirect(self):
        n = int(self.url.path[9:]) + 1 if len(self.url.path) > 9 else 1
        self.response('Redirecting...\n', (302, 'Found'), headers={'Location': f'/redirect{n}'})

    def do_GET_json(self):
        self.response(json.dumps({'Hello': 'World'}), content_type='application/json')

    def do_GET_slow(self):
        time.sleep(2)
        self.response('zZzZ\n')

    def do_GET_cookies(self):
        if 'Cookie' not in self.headers:
            self.send_error(400, 'No `Cookie` header sent')
            return

        cookie = cookies.SimpleCookie()
        cookie.load(self.headers['Cookie'])
        self.response('\n'.join(('{}: {}'.format(n, v.coded_value) for n, v in cookie.items())))

    def do_GET_auth(self):
        authorization = self.headers.get('Authorization')
        if not authorization:
            self.response('', status=(401, 'Unauthorized'), headers={'WWW-Authenticate': 'Basic realm=Test'})
            return

        self.response('Authorization: {}\n'.format(authorization))

    def do_GET_response_headers(self):
        params = parse_qsl(self.url.query)

        self.response('Headers\n', headers=params)

    def do_HTTP_404(self):
        self.send_error(404, 'Not Found')

    @property
    def url(self):
        if not hasattr(self, '_url'):
            # For some annoying reason this can't be set in `__init__`
            self._url = urlsplit(self.path)

        return self._url

    def response(self, body, status=None, content_type=None, headers=None):
        body = body.encode('utf-8') if isinstance(body, str) else body
        status = status or (200, 'OK')
        content_type = content_type or 'text/html; charset=UTF-8'
        headers = headers or {}
        self.send_response(*status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        for key, value in headers.items() if isinstance(headers, dict) else headers:
            self.send_header(key, value)
        self.end_headers()

        self.wfile.write(body)
