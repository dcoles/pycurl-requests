import os

from .api import request, get, head, post, patch, put, delete
from .exceptions import RequestException, ConnectionError, HTTPError, URLRequired, TooManyRedirects, ConnectTimeout, ReadTimeout, Timeout
from .models import Request, Response, PreparedRequest
from .sessions import Session, session

# If PYCURL_REQUESTS is set to a non-null value, then this module imports
# Requests instead of PyCurl-Requests.
#
# This is used in unit-tests to allow checking of Requests compatibility.
if os.getenv('PYCURLREQUESTS_REQUESTS', None):
    import requests
else:
    requests = __import__(__name__)


def patch_requests():
    """Patch Requests library with PycURL Requests"""
    import sys

    for module in ('requests', 'request.adapters', 'requests.api', 'requests.cookies', 'requests.exceptions',
                   'requests.models', 'requests.sessions', 'requests.structures'):
        sys.modules[module] = sys.modules[module.replace('requests', __name__, 1)]


__all__ = [
    'request', 'get', 'head', 'post', 'patch', 'put', 'delete',
    'RequestException', 'ConnectionError', 'HTTPError', 'URLRequired', 'TooManyRedirects', 'ConnectTimeout', 'ReadTimeout', 'Timeout',
    'Request', 'Response', 'PreparedRequest',
    'Session', 'session',
    'patch_requests',
]
