import contextlib
import datetime
import io
import warnings
from io import BytesIO
import logging

import pycurl

from pycurl_requests import exceptions
from pycurl_requests import models
from pycurl_requests import structures

# For DEBUGFUNCTION callback
CURLINFO_TEXT = 0
CURLINFO_HEADER_IN = 1
CURLINFO_HEADER_OUT = 2

# Mapping of cURL error codes to Request exceptions
EXCEPTION_MAP = {
    pycurl.E_UNSUPPORTED_PROTOCOL:      exceptions.ConnectionError,
    pycurl.E_URL_MALFORMAT:             exceptions.InvalidURL,
    pycurl.E_COULDNT_RESOLVE_PROXY:     exceptions.ProxyError,
    pycurl.E_COULDNT_RESOLVE_HOST:      exceptions.ConnectionError,
    pycurl.E_COULDNT_CONNECT:           exceptions.ConnectionError,
    pycurl.E_OPERATION_TIMEDOUT:        exceptions.Timeout,
    pycurl.E_SSL_CONNECT_ERROR:         exceptions.SSLError,
    pycurl.E_INTERFACE_FAILED:          exceptions.ConnectionError,
    pycurl.E_TOO_MANY_REDIRECTS:        exceptions.TooManyRedirects,
    pycurl.E_GOT_NOTHING:               exceptions.ConnectionError,
    pycurl.E_PEER_FAILED_VERIFICATION:  exceptions.SSLError,
    pycurl.E_SSL_ISSUER_ERROR:          exceptions.SSLError,
    pycurl.E_SSL_PINNEDPUBKEYNOTMATCH:  exceptions.SSLError,
    pycurl.E_SSL_INVALIDCERTSTATUS:     exceptions.SSLError,
}

# Loggers
LOGGER = logging.getLogger('curl')
LOGGER_TEXT = LOGGER.getChild('text')
LOGGER_HEADER_IN = LOGGER.getChild('header_in')
LOGGER_HEADER_OUT = LOGGER.getChild('header_out')
DEBUGFUNCTION_LOGGERS = {LOGGER_TEXT, LOGGER_HEADER_IN, LOGGER_HEADER_OUT}


def send(prepared, *, curl=None, timeout=None, allow_redirects=True, max_redirects=-1):
    c = curl or pycurl.Curl()

    if timeout:
        warnings.warn('Timeouts not implemented. Ignoring...')

    response_buffer = BytesIO()
    reason = None
    headers = structures.CaseInsensitiveDict()
    reset_headers = False

    def header_function(line: bytes):
        nonlocal reason, headers, reset_headers

        if reset_headers:
            headers = structures.CaseInsensitiveDict()
            reset_headers = False

        try:
            # Some servers return UTF-8 status
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to latin-1
            line = line.decode('iso-8859-1')

        if reason is None:
            _, _, reason = line.split(' ', 2)
            reason = reason.strip()
            return

        if line == '\r\n':
            reset_headers = True
            return
        elif ':' not in line:
            return

        name, value = line.split(':', 1)
        headers[name] = value.strip()

    start_time = datetime.datetime.now(tz=datetime.timezone.utc)

    # Request
    c.setopt(c.URL, prepared.url)

    if prepared.method:
        c.setopt(c.CUSTOMREQUEST, prepared.method)

    if prepared.method == 'HEAD':
        c.setopt(c.NOBODY, 1)

    c.setopt(c.HTTPHEADER, ['{}: {}'.format(n, v) for n, v in prepared.headers.items()])

    if prepared.body is not None:
        if isinstance(prepared.body, str):
            body = io.BytesIO(prepared.body.encode('iso-8859-1'))
        elif isinstance(prepared.body, bytes):
            body = io.BytesIO(prepared.body)
        else:
            body = prepared.body

        c.setopt(c.UPLOAD, 1)
        c.setopt(c.READDATA, body)

    content_length = prepared.headers.get('Content-Length')
    if content_length is not None:
        c.setopt(c.INFILESIZE_LARGE, int(content_length))

    # Response
    c.setopt(c.HEADERFUNCTION, header_function)
    c.setopt(c.WRITEDATA, response_buffer)

    # Options
    if allow_redirects:
        c.setopt(c.FOLLOWLOCATION, 1)
        c.setopt(c.POSTREDIR, c.REDIR_POST_ALL)
        c.setopt(c.MAXREDIRS, max_redirects)

    # Logging
    if any((l.isEnabledFor(logging.DEBUG) for l in DEBUGFUNCTION_LOGGERS)):
        c.setopt(c.VERBOSE, 1)
        c.setopt(c.DEBUGFUNCTION, debug_function)

    with curl_exception(request=prepared):
        c.perform()

    status_code = c.getinfo(c.RESPONSE_CODE)
    effective_url = c.getinfo(c.EFFECTIVE_URL)

    # Update the last URL we requested
    prepared.url = effective_url

    response_buffer.seek(0)

    end_time = datetime.datetime.now(tz=datetime.timezone.utc)

    return models.Response(
        prepared_request=prepared,
        elapsed=end_time - start_time,
        status_code=status_code,
        reason=reason,
        headers=headers,
        encoding=headers.get_content_charset(),
        url=effective_url,
        buffer=response_buffer,
    )


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


@contextlib.contextmanager
def curl_exception(*, request=None, response=None):
    """Re-raise PycURL exceptions the equivalent `RequestException`"""
    if not request and response and hasattr(response, 'request'):
        request = response.request

    try:
        yield
    except pycurl.error as e:
        code, error_string = e.args[:2]
        message = '{} (cURL error: {})'.format(error_string, code)

        exception = EXCEPTION_MAP.get(code, exceptions.RequestException)

        raise exception(message, curl_message=error_string, curl_code=code,
                        request=request, response=response) from e
