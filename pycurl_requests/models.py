import codecs
import datetime
import http.client
import io
import json as json_
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl, quote
from io import BytesIO

import chardet
import pycurl

from pycurl_requests import exceptions
from pycurl_requests.exceptions import HTTPError

DEFAULT_REDIRECT_LIMIT = 30


class Request:
    def __init__(self,
                 method=None,
                 url=None,
                 headers=None,
                 files=None,
                 data=None,
                 params=None,
                 auth=None,
                 cookies=None,
                 hooks=None,
                 json=None):

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.json = json
        self.params = params
        self.auth = auth
        self.cookies = cookies
        self.hooks = hooks

    def deregister_hook(self, event, hook):
        raise NotImplementedError

    def prepare(self):
        prepared = PreparedRequest()
        prepared.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
            json=self.json)

        return prepared

    def register_hook(self, event, hook):
        raise NotImplementedError


class Response:
    def __init__(self,
                 prepared_request: Request = None,
                 elapsed: datetime.timedelta = None,
                 status_code: int = None,
                 reason: str = None,
                 headers: http.client.HTTPMessage = None,
                 encoding: str = None,
                 url: str = None,
                 buffer: BytesIO = None):
        self._prepared_request = prepared_request
        self._elapsed = elapsed
        self._status_code = status_code
        self._reason = reason
        self._headers = headers
        self.encoding = encoding
        self._url = url
        self._buffer = buffer

    @property
    def apparent_encoding(self):
        return chardet.detect(self.content)['encoding']

    def close(self):
        # Not implemented
        pass

    @property
    def content(self):
        return self._buffer.getvalue()

    @property
    def cookies(self):
        return NotImplemented

    @property
    def elapsed(self):
        return self._elapsed

    @property
    def headers(self):
        return self._headers

    @property
    def history(self):
        return NotImplemented

    @property
    def is_permanent_redirect(self):
        # Moved Permanently (HTTP 301) or Permanent Redirect (HTTP 308)
        return self.status_code in {301, 308}

    def iter_content(self, chunk_size=1, decode_unicode=False):
        chunk_size = chunk_size or -1
        decoder = codecs.getincrementaldecoder(self.encoding)('replace') if self.encoding and decode_unicode else None
        for chunk in iter(lambda: self._buffer.read1(chunk_size), b''):
            if decoder:
                yield decoder.decode(chunk)
            else:
                yield chunk

        if decoder:
            # Make sure we finalize the decoder (may yield replacement character)
            tail = decoder.decode(b'', True)
            if tail:
                yield tail

    def iter_lines(self, chunk_size=512, decode_unicode=False, delimiter=None):
        delimiter = delimiter or ('\n' if self.encoding and decode_unicode else b'\n')

        leftover = None
        for chunk in self.iter_content(chunk_size, decode_unicode=decode_unicode):
            while True:
                parts = chunk.split(delimiter, 1)
                if len(parts) == 1:
                    leftover = parts[0]
                    break
                elif leftover:
                    chunk = parts[1]
                    yield leftover + parts[0]
                else:
                    chunk = parts[1]
                    yield parts[0]

        if leftover is not None:
            yield leftover

    def json(self, **kwargs):
        return json_.loads(self.content, **kwargs)

    @property
    def links(self):
        return NotImplemented

    @property
    def next(self):
        return NotImplemented

    @property
    def ok(self):
        return self.status_code < 400

    def raise_for_status(self):
        if 400 <= self.status_code < 500:
            raise HTTPError('{s.status_code} Client Error: {s.reason} for url: {s.url}'.format(s=self),
                            response=self)

        if 500 <= self.status_code < 600:
            raise HTTPError('{s.status_code} Client Error: {s.reason} for url: {s.url}'.format(s=self),
                            response=self)

    @property
    def raw(self):
        return self._buffer

    @property
    def reason(self):
        return self._reason

    @property
    def request(self):
        return self._prepared_request

    @property
    def status_code(self):
        return self._status_code

    @property
    def text(self):
        return self.content.decode(self.encoding or 'ISO-8859-1')

    @property
    def url(self):
        return self._url


class PreparedRequest:
    def __init__(self):
        self.method = None
        self.url = None
        self.headers = None
        self.body = None
        self.hooks = None

    @property
    def path_url(self):
        return urlsplit(self.url).path

    def prepare(self,
                method=None,
                url=None,
                headers=None,
                files=None,
                data=None,
                params=None,
                auth=None,
                cookies=None,
                hooks=None,
                json=None):

        self.prepare_method(method)
        self.prepare_url(url, params)
        self.prepare_headers(headers)
        self.prepare_cookies(cookies)
        self.prepare_body(data, files, json)
        self.prepare_auth(auth, url)
        self.prepare_hooks(hooks)

    def prepare_method(self, method):
        self.method = method.upper() if method else None

    def prepare_url(self, url, params):
        url = url.strip()

        try:
            scheme, _ = url.split(':', 1)
        except ValueError:
            raise exceptions.MissingSchema('Missing scheme for {!r}'.format(url))

        info = pycurl.version_info()
        protocols = info[8]
        if scheme not in protocols:
            raise exceptions.InvalidSchema('Unsupported scheme for {!r}'.format(url))

        parts = urlsplit(url)
        path = quote(parts.path) if parts.path else '/'

        if not params:
            query = parts.query
        else:
            if isinstance(params, (str, bytes)):
                params = parse_qsl(params)

            params = list(params.items()) if isinstance(params, dict) else params
            query = urlencode(parse_qsl(parts.query) + params, doseq=True)

        self.url = urlunsplit(parts[:2] + (path, query) + parts[4:])

    def prepare_headers(self, headers):
        # NOTE: Only user-defined headers, not those set by libcurl
        self.headers = headers or http.client.HTTPMessage()

    def prepare_cookies(self, cookies):
        # FIXME: Not implemented
        pass

    def prepare_content_length(self, body):
        content_length = None

        if body is None:
            if self.method not in ('GET', 'HEAD'):
                content_length = 0
        elif isinstance(body, bytes):
            content_length = len(body)
        elif isinstance(body, str):
            content_length = len(body.encode('iso-8859-1'))
        elif getattr(body, 'seekable', False):
            content_length = body.seek(0, io.SEEK_END)
            body.seek(0)

        if content_length is not None:
            self.headers['Content-Length'] = str(content_length)

    def prepare_body(self, data, files, json=None):
        body = None

        if files is not None:
            raise NotImplementedError
        elif data is not None:
            if isinstance(data, (io.RawIOBase, io.BufferedReader)):
                # It's a file-like object, so can be sent directly
                body = data
            elif isinstance(data, (dict, list)):
                self._set_header_default('Content-Type', 'application/x-www-form-urlencoded')
                body = urlencode(data)
            else:
                # Assume it's something bytes-compatible
                body = data
        elif json is not None:
            self._set_header_default('Content-Type', 'application/json')
            body = json_.dumps(json, ensure_ascii=True).encode('ascii')

        if 'Content-Length' not in self.headers:
            self.prepare_content_length(body)

        self.body = body

    def _set_header_default(self, key, default):
        """Set header `key` to `default` if not already set"""
        if key not in self.headers:
            self.headers[key] = default

    def prepare_auth(self, auth, url=''):
        # FIXME: Not implemented
        pass

    def prepare_hooks(self, hooks):
        # FIXME: Not implemented
        pass
