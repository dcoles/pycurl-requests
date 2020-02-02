from .api import request, get, head, post, patch, put, delete
from .exceptions import RequestException, ConnectionError, HTTPError, URLRequired, TooManyRedirects, ConnectTimeout, ReadTimeout, Timeout
from .models import Request, Response, PreparedRequest


def patch_requests():
    """Patch Requests library with PycURL Requests"""
    import sys
    sys.modules['requests'] = sys.modules[__name__]
