from typing import *

import pycurl


class AuthBase:
    """Base class that all auth implementations derive from."""
    def __call__(self, r):
        raise NotImplementedError('Auth hooks must be callable')


class CurlAuth(AuthBase):
    """Auth handled by cURL."""
    def __init__(self, httpauth: int, username: Optional[str] = None, password: Optional[str] = None):
        """
        :param httpauth: Bitmask of authentication method(s) to use (see `CURLOPT_HTTPAUTH`).
        :param username: Username for authentication.
        :param password: Password for authentication.
        """
        self.curl_httpauth = httpauth
        self.username = username
        self.password = password

    def __call__(self, r):
        return r

    def setopts(self, curl: pycurl.Curl):
        """Set cURL options for this form of auth."""
        curl.setopt(pycurl.HTTPAUTH, self.curl_httpauth)

        if self.username:
            curl.setopt(pycurl.USERNAME, self.username)

        if self.password:
            curl.setopt(pycurl.PASSWORD, self.password)


class HTTPBasicAuth(CurlAuth):
    """HTTP Basic Authentication."""
    def __init__(self, username: str, password: str):
        """
        :param username: Username for authentication.
        :param password: Password for authentication.
        """
        super().__init__(pycurl.HTTPAUTH_BASIC, username=username, password=password)
