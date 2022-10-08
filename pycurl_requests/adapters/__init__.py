"""
Request adapters.

See https://requests.readthedocs.io/en/latest/user/advanced/#transport-adapters.
"""

from pycurl_requests.adapters.pycurl import PyCurlBaseAdapter, PyCurlHttpAdapter
from pycurl_requests.adapters.base import BaseAdapter

__all__ = ['BaseAdapter', 'PyCurlBaseAdapter', 'PyCurlHttpAdapter']
