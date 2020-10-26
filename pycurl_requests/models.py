import codecs
import datetime
import io
import json as json_
from collections import abc
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl, quote
from io import BytesIO
from typing import *

import chardet

from pycurl_requests.auth import HTTPBasicAuth, CurlAuth
from pycurl_requests.cookies import RequestsCookieJar
from pycurl_requests import exceptions
from pycurl_requests import structures

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
    def __init__(self):
        self.request = None  # type: Optional[Request]
        self.elapsed = None  # type: Optional[datetime.timedelta]
        self.status_code = None  # type: Optional[int]
        self.reason = None  # type: Optional[str]
        self.headers = None  # type: Optional[structures.CaseInsensitiveDict]
        self.encoding = None  # type: Optional[str]
        self.url = None  # type: Optional[str]
        self.raw = None  # type: Optional[BytesIO]

    @property
    def apparent_encoding(self):
        return chardet.detect(self.content)['encoding']

    def close(self):
        # Not implemented
        pass

    @property
    def content(self):
        return self.raw.getvalue()

    @property
    def cookies(self):
        return NotImplemented

    @property
    def history(self):
        return NotImplemented

    @property
    def is_permanent_redirect(self):
        # Moved Permanently (HTTP 301) or Permanent Redirect (HTTP 308)
        return self.status_code in {301, 308}

    @property
    def is_redirect(self):
        return self.status_code in {301, 302, 303, 307, 308}

    def iter_content(self, chunk_size=1, decode_unicode=False):
        chunk_size = chunk_size or -1
        decoder = codecs.getincrementaldecoder(self.encoding)('replace') if self.encoding and decode_unicode else None
        for chunk in iter(lambda: self.raw.read1(chunk_size), b''):
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
        leftover = None
        for chunk in self.iter_content(chunk_size, decode_unicode=decode_unicode):
            if leftover:
                chunk = leftover + chunk

            if delimiter is not None:
                parts = chunk.split(delimiter)
            else:
                parts = chunk.splitlines()

            # FIXME: This logic doesn't work for CR-only line endings
            if chr(ord(chunk[-1])) == '\n':
                yield from parts
                leftover = None
            else:
                # This may be a partial line, so add to the next chunk
                yield from parts[:-1]
                leftover = parts[-1]

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
            raise exceptions.HTTPError('{s.status_code} Client Error: {s.reason} for url: {s.url}'.format(s=self),
                                       response=self)

        if 500 <= self.status_code < 600:
            raise exceptions.HTTPError('{s.status_code} Client Error: {s.reason} for url: {s.url}'.format(s=self),
                                       response=self)

    @property
    def text(self):
        return self.content.decode(self.encoding or 'ISO-8859-1')


class PreparedRequest:
    def __init__(self):
        self.method = None
        self.url = None
        self.headers = None
        self.body = None
        self.hooks = None

        # Extensions
        self.curl_auth = None

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
        if isinstance(url, bytes):
            url = url.decode('iso-8859-1')

        url = url.strip()

        # Leave non-HTTP schemes as-is
        if ':' in url and not url.lower().startswith('http'):
            self.url = url
            return

        parts = urlsplit(url)
        path = quote(parts.path) if parts.path else '/'

        if not params:
            query = parts.query
        else:
            if isinstance(params, (str, bytes)):
                params = parse_qsl(params)
            if isinstance(params, abc.Mapping):
                params = list(params.items())
            else:
                params = list(params)

            query = urlencode(parse_qsl(parts.query) + params, doseq=True)

        self.url = urlunsplit(parts[:2] + (path, query) + parts[4:])

    def prepare_headers(self, headers):
        # NOTE: Only user-defined headers, not those set by libcurl
        headers = headers or structures.CaseInsensitiveDict()

        # Filter out headers with None value
        header_names = headers.keys()
        for name in header_names:
            if headers[name] is None:
                del headers[name]

        self.headers = headers

    def prepare_cookies(self, cookies):
        # Cookies can only be set if there is no existing `Cookie` header
        if 'Cookie' in self.headers or cookies is None:
            return

        cookiejar = RequestsCookieJar()
        cookiejar.update(cookies)

        value = '; '.join(('{}={}'.format(n, v) for n, v in cookiejar.iteritems()))

        self.headers['Cookie'] = value

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
            elif isinstance(data, (abc.Mapping, list, tuple)):
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
        if not auth:
            return

        if isinstance(auth, tuple):
            username, password = auth
            self.curl_auth = HTTPBasicAuth(username, password)
        elif isinstance(auth, CurlAuth):
            # Handled by libcurl
            self.curl_auth = auth
        else:
            # Allow auth to make its changes
            r = auth(self)
            self.__dict__.update(r.__dict__)

            self.prepare_content_length(self.body)

    def prepare_hooks(self, hooks):
        # FIXME: Not implemented
        pass
