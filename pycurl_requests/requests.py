"""
Helper shim for importing Requests.

If PYCURL_REQUESTS is set to a non-null value, then this module imports
Requests instead of PyCurl-Requests.

This is used in unit-tests to allow checking of Requests compatibility.
"""

import os

if os.getenv('PYCURLREQUESTS_REQUESTS', None):
    from requests import *
else:
    from pycurl_requests import *
