from collections import abc
from typing import *

import pycurl

from pycurl_requests.auth import HTTPBasicAuth, CurlAuth
from pycurl_requests.models import Request, PreparedRequest, Response, DEFAULT_REDIRECT_LIMIT
from pycurl_requests import structures
from pycurl_requests import _pycurl


# Stubbed out for Requests tests
class SessionRedirectMixin:
    pass


class Session:
    def __init__(self):
        self.auth = None
        self.cert = None
        self.cookies = None
        self.headers = structures.CaseInsensitiveDict()
        self.hooks = NotImplemented
        self.max_redirects = DEFAULT_REDIRECT_LIMIT
        self.params = {}
        self.proxies = {}
        self.stream = False
        self.trust_env = True
        self.verify = True

        self.curl = pycurl.Curl()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.curl:
            self.curl.close()

        self.curl = None

    def get(self, url, params=None, **kwargs) -> Response:
        return self.request('GET', url, params=params, **kwargs)

    def head(self, url, **kwargs) -> Response:
        return self.request('HEAD', url, **kwargs)

    def options(self, url, **kwargs) -> Response:
        return self.request('OPTIONS', url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs) -> Response:
        return self.request('POST', url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs) -> Response:
        return self.request('PUT', url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs) -> Response:
        return self.request('PATCH', url, data=data, **kwargs)

    def delete(self, url, **kwargs) -> Response:
        return self.request('DELETE', url, **kwargs)

    def request(self, method, url,
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=True, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None) -> Response:
        request = Request(method, url,
                          params=params,
                          data=data,
                          json=json,
                          headers=headers,
                          cookies=cookies,
                          files=files,
                          auth=auth,
                          hooks=hooks)

        prepared = self.prepare_request(request)

        settings = dict(curl=self.curl, timeout=timeout, allow_redirects=allow_redirects,
                        max_redirects=self.max_redirects)
        settings.update(self.merge_environment_settings(prepared.url, proxies, stream, verify, cert))

        return self.send(prepared, **settings)

    def get_adapter(self, url) -> NotImplemented:
        raise NotImplementedError

    def get_redirect_target(self, resp: Response) -> Optional[str]:
        raise NotImplementedError

    def merge_environment_settings(self, url, proxies, stream, verify, cert) -> dict:
        # TODO: Read settings from environment
        return {}

    def mount(self, prefix, adapter):
        raise NotImplementedError

    def prepare_request(self, request: Request) -> PreparedRequest:
        prepared = PreparedRequest()

        headers = structures.CaseInsensitiveDict()
        for name, value in self.headers.items():
            headers[name] = value
        for name, value in (request.headers or {}).items():
            headers[name] = value

        prepared.prepare(
            method=request.method,
            url=request.url,
            headers=headers,
            files=request.files,
            data=request.data,
            json=request.json,
            params=_merge_params(self.params, request.params),
            auth=request.auth or self.auth,
            cookies=_merge_params(self.cookies, request.cookies),
            hooks=NotImplemented)  # TODO: Merge request with Session

        return prepared

    def rebuild_auth(self, prepared_request, response):
        raise NotImplementedError

    def rebuild_method(self, prepared_request, response):
        raise NotImplementedError

    def rebuild_proxies(self, prepared_request, proxies) -> dict:
        raise NotImplementedError

    def resolve_redirects(self, resp: Response, req: PreparedRequest, stream=False, timeout=None, verify=True, cert=None,
                          proxies=None, yield_requests=False, **adapter_kwargs) -> Generator:
        raise NotImplementedError

    def send(self, request: PreparedRequest, **kwargs):
        return _pycurl.send(request, **kwargs)

    def should_strip_auth(self, old_url, new_url):
        raise NotImplementedError


def _merge_params(current, new):
    """Merge parameters dictionary"""
    if not new:
        return current

    if not current:
        return new

    current = current.copy()
    current.update(new)

    return current


def session():
    """
    Create a Session

    .. deprecated:: 1.0.0
        Use :class:`~pycurl_requests.sessions.Session` instead.
    """
    return Session()
