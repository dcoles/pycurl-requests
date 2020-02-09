"""
Test helper utilities.
"""

import json
import threading
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

        if self.url.path == '/hello':
            self.response('Hello\nWorld\n')
        elif self.url.path == '/params':
            self.response('\n'.join(('{}: {}'.format(n, v)
                                     for n, v in parse_qsl(self.url.query))))
        elif self.url.path == '/headers':
            self.response('\n'.join(('{}: {}'.format(n, v)
                                     for n, v in self.headers.items())))
        elif self.url.path.startswith('/redirect'):
            n = int(self.url.path[9:]) + 1 if len(self.url.path) > 9 else 1
            self.response('Redirecting...\n', (302, 'Found'),
                          headers={'Location': f'/redirect{n}'})
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
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()

        self.wfile.write(body)
