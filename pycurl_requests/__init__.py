from .api import request, get, head, post, patch, put, delete
from .exceptions import RequestException, ConnectionError, HTTPError, URLRequired, TooManyRedirects, ConnectTimeout, ReadTimeout, Timeout
from .models import Request, Response, PreparedRequest
from .sessions import Session, session


def patch_requests():
    """Patch Requests library with PycURL Requests"""
    import sys

    for module in ('requests', 'requests.api', 'requests.exceptions', 'requests.models'):
        sys.modules[module] = sys.modules[module.replace('requests', __name__, 1)]
