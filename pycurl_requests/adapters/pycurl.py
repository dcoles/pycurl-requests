"""
PyCurl adapters.
"""

import datetime
import http.client
import io
from io import BytesIO
import logging
from typing import *

import pycurl

from pycurl_requests import exceptions
from pycurl_requests import models
from pycurl_requests import structures
from pycurl_requests.adapters.base import BaseAdapter

try:
    from urllib3.util.timeout import Timeout
except ImportError:
    # Timeout not supported
    Timeout = None


# For DEBUGFUNCTION callback
CURLINFO_TEXT = 0
CURLINFO_HEADER_IN = 1
CURLINFO_HEADER_OUT = 2

# Loggers
LOGGER = logging.getLogger('curl')
LOGGER_TEXT = LOGGER.getChild('text')
LOGGER_HEADER_IN = LOGGER.getChild('header_in')
LOGGER_HEADER_OUT = LOGGER.getChild('header_out')
DEBUGFUNCTION_LOGGERS = {LOGGER_TEXT, LOGGER_HEADER_IN, LOGGER_HEADER_OUT}

VERSION_INFO = pycurl.version_info()


class PyCurlBaseAdapter(BaseAdapter):
    """
    Base adapter for PyCurl.
    """
    def __init__(self, curl: pycurl.Curl) -> None:
        super().__init__()
        self.curl = curl or pycurl.Curl()

    def close(self) -> None:
        if self.curl:
            self.curl.close()

        self.curl = None


class PyCurlHttpAdapter(PyCurlBaseAdapter):
    """
    HTTP adapter for PyCurl.

    Usage::
      >>> import pycurl_requests as requests
      >>> s = requests.Session()
      >>> a = requests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None, **kwargs) -> None:
        if stream:
            raise NotImplementedError('stream not supported')

        if cert:
            raise NotImplementedError('cert not supported')

        if proxies:
            raise NotImplementedError('proxies not supported')

        pycurl_request = PyCurlRequest(
            request,
            curl = self.curl,
            timeout = timeout,
            **kwargs
        )

        return pycurl_request.send()


class PyCurlRequest:
    def __init__(self, prepared, *, curl=None, timeout=None, allow_redirects=True, max_redirects=-1):
        self.prepared = prepared
        self.curl = curl or pycurl.Curl()
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects

        if timeout is not None:
            if isinstance(timeout, (int, float)):
                self.connect_timeout, self.read_timeout = timeout, timeout
            elif Timeout and isinstance(timeout, Timeout):
                timeout.start_connect()
                self.connect_timeout = (0 if timeout.connect_timeout is Timeout.DEFAULT_TIMEOUT
                                        else timeout.connect_timeout)
                self.read_timeout = (0 if timeout.read_timeout is Timeout.DEFAULT_TIMEOUT
                                     else timeout.read_timeout)
            else:
                self.connect_timeout, self.read_timeout = timeout
        else:
            self.connect_timeout, self.read_timeout = (None, None)

        self.response_buffer = BytesIO()
        self.reason = None
        self.headers = http.client.HTTPMessage()
        self.reset_headers = False

    def header_function(self, line: bytes):
        if self.reset_headers:
            self.headers = http.client.HTTPMessage()
            self.reset_headers = False

        try:
            # Some servers return UTF-8 status
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to latin-1
            line = line.decode('iso-8859-1')

        if self.reason is None:
            _, _, reason = line.split(' ', 2)
            self.reason = reason.strip()
            return

        if line == '\r\n':
            self.reset_headers = True
            return
        elif ':' not in line:
            return

        name, value = line.split(':', 1)
        self.headers.add_header(name, value.strip())

    def send(self):
        try:
            # Avoid urlparse/urlsplit as they only support RFC 3986 compatible URLs
            scheme, _ = self.prepared.url.split(':', 1)
        except ValueError:
            raise exceptions.MissingSchema('Missing scheme for {!r}'.format(self.prepared.url))

        supported_protocols = VERSION_INFO[8]
        if scheme.lower() not in supported_protocols:
            raise exceptions.InvalidSchema('Unsupported scheme for {!r}'.format(self.prepared.url))

        # Request
        self.curl.setopt(pycurl.URL, self.prepared.url)

        if self.prepared.method:
            self.curl.setopt(pycurl.CUSTOMREQUEST, self.prepared.method)

        if self.prepared.method == 'HEAD':
            self.curl.setopt(pycurl.NOBODY, 1)

        # Automatically decompress downloads
        self.curl.setopt(pycurl.ACCEPT_ENCODING, '')

        # HTTP server authentication
        self._prepare_http_auth()

        self.curl.setopt(pycurl.HTTPHEADER, [render_header(h) for h in self.prepared.headers.items()])

        if self.prepared.body is not None:
            if isinstance(self.prepared.body, str):
                body = io.BytesIO(self.prepared.body.encode('iso-8859-1'))
            elif isinstance(self.prepared.body, bytes):
                body = io.BytesIO(self.prepared.body)
            else:
                body = self.prepared.body

            self.curl.setopt(pycurl.UPLOAD, 1)
            self.curl.setopt(pycurl.READDATA, body)

        content_length = self.prepared.headers.get('Content-Length')
        if content_length is not None:
            self.curl.setopt(pycurl.INFILESIZE_LARGE, int(content_length))

        # Response
        self.curl.setopt(pycurl.HEADERFUNCTION, self.header_function)
        self.curl.setopt(pycurl.WRITEDATA, self.response_buffer)

        # Options
        if self.connect_timeout is not None:
            timeout = int(self.connect_timeout * 1000)
            self.curl.setopt(pycurl.CONNECTTIMEOUT_MS, timeout)

        if self.read_timeout is not None:
            timeout = int(self.read_timeout * 1000)
            self.curl.setopt(pycurl.TIMEOUT_MS, timeout)

        if self.allow_redirects:
            self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
            self.curl.setopt(pycurl.POSTREDIR, pycurl.REDIR_POST_ALL)
            self.curl.setopt(pycurl.MAXREDIRS, self.max_redirects)

        # Logging
        if any((l.isEnabledFor(logging.DEBUG) for l in DEBUGFUNCTION_LOGGERS)):
            self.curl.setopt(pycurl.VERBOSE, 1)
            self.curl.setopt(pycurl.DEBUGFUNCTION, debug_function)

        return self.perform()

    def _prepare_http_auth(self):
        if not (hasattr(self.prepared, 'curl_auth') and self.prepared.curl_auth):
            return

        self.prepared.curl_auth.setopts(self.curl)

    def perform(self):
        try:
            start_time = datetime.datetime.now(tz=datetime.timezone.utc)
            try:
                self.curl.perform()
            finally:
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
                self.prepared.url = self.curl.getinfo(pycurl.EFFECTIVE_URL)
                self.response_buffer.seek(0)
                response = self.build_response(elapsed=end_time - start_time)
        except pycurl.error as e:
            raise exceptions.RequestException.from_pycurl_error(
                e, request=self.prepared, response=response) from e

        return response

    def build_response(self, elapsed=None):
        status_code = self.curl.getinfo(pycurl.RESPONSE_CODE)
        if not status_code:
            return None

        response = models.Response()
        response.request = self.prepared
        response.elapsed = elapsed
        response.status_code = status_code
        response.reason = self.reason
        # Merge headers as allowed by RFC-7230 section 3.3.2
        response.headers = structures.CaseInsensitiveDict(
            ((k, ', '.join(self.headers.get_all(k))) for k in self.headers.keys()))
        response.encoding = get_encoding_from_headers(self.headers)
        response.url = self.prepared.url
        response.raw = self.response_buffer

        return response


def debug_function(infotype: int, message: bytes):
    """cURL `DEBUGFUNCTION` that writes to logger"""
    if infotype > CURLINFO_HEADER_OUT:
        # Ignore data messages
        return

    message = message.decode('utf-8', 'replace')

    if infotype == CURLINFO_TEXT:
        LOGGER_TEXT.debug(message.rstrip())
    elif infotype == CURLINFO_HEADER_IN:
        for line in message.splitlines():
            LOGGER_HEADER_IN.debug(line)
    elif infotype == CURLINFO_HEADER_OUT:
        for line in message.splitlines():
            LOGGER_HEADER_OUT.debug(line)


def get_encoding_from_headers(headers: http.client.HTTPMessage) -> Optional[str]:
    """
    Return encoding based on HTTP headers.
    """
    charset = headers.get_content_charset()
    if charset:
        return charset

    content_type = headers.get('Content-Type')
    if not content_type:
        return None

    if content_type.startswith('text/'):
        return 'iso-8859-1'

    if content_type.startswith('application/json'):
        # Assume UTF-8 based on RFC 4627
        return 'utf-8'

    return None


def render_header(header: Tuple[Union[str, bytes], Union[str, bytes]]) -> bytes:
    """
    Render HTTP header.
    """
    key, value = header

    encoded = bytearray()
    encoded.extend(key if isinstance(key, bytes) else key.encode('iso-8859-1'))
    encoded.extend(b': ')
    encoded.extend(value if isinstance(value, bytes) else value.encode('iso-8859-1'))

    return bytes(encoded)
