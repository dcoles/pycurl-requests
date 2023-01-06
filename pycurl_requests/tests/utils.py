"""
Test helper utilities.
"""

import json
import random
import threading
import time
from http import cookies
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl

import pytest

from pycurl_requests import requests

__all__ = ['IS_PYCURL_REQUESTS', 'http_server', 'test_data']

#: Is this _really_ PyCurl-Requests?
#: Should be used when testing for PyCurl-Requests extensions.
IS_PYCURL_REQUESTS = requests.__name__ == 'pycurl_requests'


test_data = bytes(random.getrandbits(8) for _ in range(123456))


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

    def do_POST(self):
        path = self.url.path[1:].replace('/', '_')
        getattr(self, f'do_POST_{path}', self.do_HTTP_404)()

    def do_POST_stream(self):
        self.POST_stream_helper(allow_chunked=True)

    def do_POST_stream_no_chunked(self):
        self.POST_stream_helper(allow_chunked=False)

    def POST_stream_helper(self, allow_chunked: bool):
        if "Content-Length" in self.headers:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
        elif "Transfer-Encoding" in self.headers and "chunked" in self.headers["Transfer-Encoding"]:
            if not allow_chunked:
                self.response('This endpoint has chunked transfer deactivated.', status=(400, "Bad Request"))
                return
            body = b""
            while True:
                line = self.rfile.readline()
                chunk_length = int(line, 16)
                if chunk_length != 0:
                    chunk = self.rfile.read(chunk_length)
                    body += chunk
                self.rfile.readline()
                if chunk_length == 0:
                    break
        else:
            self.response('Missing Content-Length or Transfer-Encoding header.', status=(400, "Bad Request"))
            return

        if body == test_data:
            self.response('Upload succeeded.')
        else:
            self.response('Upload failed.', status=(400, "Bad Request"))


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
