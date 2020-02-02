import contextlib
import datetime
import http.client
import io
from io import BytesIO
import logging

import pycurl

from pycurl_requests import exceptions
from pycurl_requests import models

# For DEBUGFUNCTION callback
CURLINFO_TEXT = 0
CURLINFO_HEADER_IN = 1
CURLINFO_HEADER_OUT = 2

# Mapping of cURL error codes to Request exceptions
EXCEPTION_MAP = {
    1: exceptions.ConnectionError,   # UNSUPPORTED_PROTOCOL
    3: exceptions.ConnectionError,   # URL_MALFORMAT
    5: exceptions.ConnectionError,   # COULDNT_RESOLVE_PROXY
    6: exceptions.ConnectionError,   # COULDNT_RESOLVE_HOST
    7: exceptions.ConnectionError,   # COULDNT_CONNECT
    28: exceptions.Timeout,          # OPERATION_TIMEDOUT
    35: exceptions.ConnectionError,  # SSL_CONNECT_ERROR
    45: exceptions.ConnectionError,  # INTERFACE_FAILED
    47: exceptions.ConnectionError,  # TOO_MANY_REDIRECTS
    52: exceptions.ConnectionError,  # GOT_NOTHING
    60: exceptions.ConnectionError,  # PEER_FAILED_VERIFICATION
    83: exceptions.ConnectionError,  # SSL_ISSUER_ERROR
    90: exceptions.ConnectionError,  # SSL_PINNEDPUBKEYNOTMATCH
    91: exceptions.ConnectionError,  # SSL_INVALIDCERTSTATUS
}

# Loggers
LOGGER = logging.getLogger('curl')
LOGGER_TEXT = LOGGER.getChild('text')
LOGGER_HEADER_IN = LOGGER.getChild('header_in')
LOGGER_HEADER_OUT = LOGGER.getChild('header_out')
DEBUGFUNCTION_LOGGERS = {LOGGER_TEXT, LOGGER_HEADER_IN, LOGGER_HEADER_OUT}


def request(*args, curl=None, allow_redirects=True, **kwargs):
    curl = curl or pycurl.Curl()

    request = models.Request(*args, **kwargs)
    prepared = request.prepare()

    response_buffer = BytesIO()
    reason = None
    headers = http.client.HTTPMessage()
    reset_headers = False

    def header_function(line: bytes):
        nonlocal reason, headers, reset_headers

        if reset_headers:
            headers = http.client.HTTPMessage()
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

    with contextlib.closing(curl) as c:
        # Request
        c.setopt(c.URL, prepared.url)
        c.setopt(c.CUSTOMREQUEST, prepared.method)
        c.setopt(c.HTTPHEADER, ['{}: {}'.format(n, v) for n, v in prepared.headers.items()])
        if prepared.body is not None:
            c.setopt(c.UPLOAD, 1)
            c.setopt(c.READDATA, prepared.body)
            if prepared.body.seekable:
                # Set `Content-Length` if available
                size = prepared.body.seek(0, io.SEEK_END)
                prepared.body.seek(0)  # Seek back to start
                c.setopt(c.INFILESIZE_LARGE, size)

        # Response
        c.setopt(c.HEADERFUNCTION, header_function)
        c.setopt(c.WRITEDATA, response_buffer)

        # Options
        if allow_redirects:
            c.setopt(c.FOLLOWLOCATION, 1)
            c.setopt(c.MAXREDIRS, models.DEFAULT_REDIRECT_LIMIT)

        # Logging
        if any((l.isEnabledFor(logging.DEBUG) for l in DEBUGFUNCTION_LOGGERS)):
            c.setopt(c.VERBOSE, 1)
            c.setopt(c.DEBUGFUNCTION, debug_function)

        with curl_exception(request=prepared):
            c.perform()

        status_code = c.getinfo(c.RESPONSE_CODE)
        effective_url = c.getinfo(c.EFFECTIVE_URL)

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

        raise exception(message, curl_error=error_string, curl_code=code,
                        request=request, response=response) from e
