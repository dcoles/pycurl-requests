#!/usr/bin/env python3
# A helper for executing Request's unit-test suite
#
# See https://github.com/psf/requests/tree/master/tests

import os
import sys
import runpy
import pkg_resources

import requests.compat
import pycurl_requests

REQUIRED_PACKAGES = ['pytest-httpbin', 'pytest-mock']


if __name__ == '__main__':
    if not os.path.exists('Pipfile'):
        print('ERROR: Requests\' unit tests expect to run from the top-level of the repository',
              file=sys.stderr)
        sys.exit(1)

    try:
        for package in REQUIRED_PACKAGES:
            pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        print('ERROR: Requests\' unit tests require additional fixtures:', file=sys.stderr)
        print('  pip install --user {}'.format(' '.join(REQUIRED_PACKAGES)), file=sys.stderr)
        sys.exit(1)

    pycurl_requests.patch_requests()

    # Requests' tests use compatibility functions
    sys.modules['requests.compat'] = requests.compat

    runpy.run_module('pytest', run_name='__main__')
