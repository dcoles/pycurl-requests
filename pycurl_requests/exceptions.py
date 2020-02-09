# This file is taken from Requests v2.22.0 with the following modifications:
#   - Replaced RequestException with custom implementation for PycURL-Requests
#   - Removed dependency on `urllib3.exceptions`
#   - Removed UTF-8 coding header comment
#
# It was originally released under the following licence:
# ```
# Copyright 2019 Kenneth Reitz
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
# ```

"""
requests.exceptions
~~~~~~~~~~~~~~~~~~~

This module contains the set of Requests' exceptions.
"""

import pycurl


class RequestException(IOError):
    """There was an ambiguous exception that occurred while handling your request."""

    @classmethod
    def from_pycurl_error(cls, error: pycurl.error, **kwargs):
        """Create a RequestException (or subclass) from PycURL error."""
        code, message = error.args[:2]
        msg = '{} (cURL error: {})'.format(message, code)

        exception = PYCURL_ERROR_MAPPING.get(code, cls)
        return exception(msg, curl_message=message, curl_code=code, **kwargs)

    def __init__(self, *args, curl_message=None, curl_code=None, request=None, response=None):
        self.curl_message = curl_message
        self.curl_code = curl_code
        self.request = request
        self.response = response

        if self.response is not None and not self.request and hasattr(self.response, 'request'):
            self.request = self.response.request

        super().__init__(*args)


class HTTPError(RequestException):
    """An HTTP error occurred."""


class ConnectionError(RequestException):
    """A Connection error occurred."""


class ProxyError(ConnectionError):
    """A proxy error occurred."""


class SSLError(ConnectionError):
    """An SSL error occurred."""


class Timeout(RequestException):
    """The request timed out.

    Catching this error will catch both
    :exc:`~requests.exceptions.ConnectTimeout` and
    :exc:`~requests.exceptions.ReadTimeout` errors.
    """


class ConnectTimeout(ConnectionError, Timeout):
    """The request timed out while trying to connect to the remote server.

    Requests that produced this error are safe to retry.
    """


class ReadTimeout(Timeout):
    """The server did not send any data in the allotted amount of time."""


class URLRequired(RequestException):
    """A valid URL is required to make a request."""


class TooManyRedirects(RequestException):
    """Too many redirects."""


class MissingSchema(RequestException, ValueError):
    """The URL schema (e.g. http or https) is missing."""


class InvalidSchema(RequestException, ValueError):
    """See defaults.py for valid schemas."""


class InvalidURL(RequestException, ValueError):
    """The URL provided was somehow invalid."""


class InvalidHeader(RequestException, ValueError):
    """The header value provided was somehow invalid."""


class InvalidProxyURL(InvalidURL):
    """The proxy URL provided is invalid."""


class ChunkedEncodingError(RequestException):
    """The server declared chunked encoding but sent an invalid chunk."""


class ContentDecodingError(RequestException):
    """Failed to decode response content"""


class StreamConsumedError(RequestException, TypeError):
    """The content for this response was already consumed"""


class RetryError(RequestException):
    """Custom retries logic failed"""


class UnrewindableBodyError(RequestException):
    """Requests encountered an error when trying to rewind a body"""

# Warnings


class RequestsWarning(Warning):
    """Base warning for Requests."""
    pass


class FileModeWarning(RequestsWarning, DeprecationWarning):
    """A file was opened in text mode, but Requests determined its binary length."""
    pass


class RequestsDependencyWarning(RequestsWarning):
    """An imported dependency doesn't match the expected version range."""
    pass


#: Mapping of PycURL error codes to Request exceptions
PYCURL_ERROR_MAPPING = {
    pycurl.E_UNSUPPORTED_PROTOCOL: ConnectionError,
    pycurl.E_URL_MALFORMAT: InvalidURL,
    pycurl.E_COULDNT_RESOLVE_PROXY: ProxyError,
    pycurl.E_COULDNT_RESOLVE_HOST: ConnectionError,
    pycurl.E_COULDNT_CONNECT: ConnectionError,
    pycurl.E_OPERATION_TIMEDOUT: Timeout,
    pycurl.E_SSL_CONNECT_ERROR: SSLError,
    pycurl.E_INTERFACE_FAILED: ConnectionError,
    pycurl.E_TOO_MANY_REDIRECTS: TooManyRedirects,
    pycurl.E_GOT_NOTHING: ConnectionError,
    pycurl.E_PEER_FAILED_VERIFICATION: SSLError,
    pycurl.E_SSL_CACERT: SSLError,
    pycurl.E_SSL_ISSUER_ERROR: SSLError,
    pycurl.E_SSL_PINNEDPUBKEYNOTMATCH: SSLError,
    pycurl.E_SSL_INVALIDCERTSTATUS: SSLError,
}
