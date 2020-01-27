import contextlib
import datetime
import http.client
from io import BytesIO
from typing import *

import pycurl

from pycurl_requests import models


def request(method, url, *, curl=None, allow_redirects=True, **kwargs):
    if method != 'GET':
        raise NotImplementedError

    curl = curl or pycurl.Curl()

    request = models.Request(method, url, **kwargs)
    prepared = request.prepare()

    buffer = BytesIO()
    reason = None
    headers = http.client.HTTPMessage()

    def header_function(line):
        nonlocal reason

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

        if ':' not in line:
            return

        name, value = line.split(':', 1)
        headers[name] = value.strip()

    start_time = datetime.datetime.now(tz=datetime.timezone.utc)

    with contextlib.closing(curl) as c:
        c.setopt(c.URL, prepared.url)
        c.setopt(c.HTTPHEADER, ['{}: {}'.format(n, v) for n, v in prepared.headers.items()])
        c.setopt(c.HEADERFUNCTION, header_function)
        c.setopt(c.WRITEDATA, buffer)
        if allow_redirects:
            c.setopt(c.FOLLOWLOCATION, 1)

        c.perform()

        status_code = c.getinfo(c.RESPONSE_CODE)
        effective_url = c.getinfo(c.EFFECTIVE_URL)

    mime_type, params = parse_content_type(headers['Content-Type'])
    encoding = params.get('charset')

    buffer.seek(0)

    end_time = datetime.datetime.now(tz=datetime.timezone.utc)

    return models.Response(
        prepared_request=prepared,
        elapsed=end_time - start_time,
        status_code=status_code,
        reason=reason,
        headers=headers,
        encoding=encoding,
        url=effective_url,
        buffer=buffer,
    )


def parse_content_type(content_type: str) -> (str, Dict[str, str]):
    """Parse value of `Content-Type` header"""
    parameters = content_type.split(';')
    mime_type = parameters[0].strip()
    params = http.client.HTTPMessage()
    for parameter in parameters[1:]:
        name, value = parameter.split('=', 1)
        name, value = name.strip(), value.strip()
        params[name] = value

    return mime_type, params



