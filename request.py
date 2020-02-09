#!/usr/bin/env python3
# A basic `curl`-like command-line HTTP utility

import argparse
import http.client
import json
import logging
import sys

from pycurl_requests import requests

SAFE_CONTENT_TYPES = {'application/json'}


def header(h):
    key, value = h.split(':', 1)
    return key, value


class Formatter(logging.Formatter):
    """A formatter that emulates cURLs `--verbose` output"""

    LOGGER_PREFIX = {
        'curl.text': '*',
        'curl.header_out': '>',
        'curl.header_in': '<',
    }

    def formatMessage(self, record: logging.LogRecord):
        prefix = self.LOGGER_PREFIX.get(record.name, '?')
        return '{} {}'.format(prefix, record.getMessage())


def main():
    parser = argparse.ArgumentParser(description='A basic `curl`-like command-line HTTP utility')
    parser.add_argument('-d', '--data', action='append',
                        help='Add POST data')
    parser.add_argument('-H', '--header', action='append', type=header,
                        help='Add custom request header (format: `Header: Value`)')
    parser.add_argument('--json', type=json.loads, help='Add JSON POST data')
    parser.add_argument('-L', '--location', help='Follow redirects', action='store_true')
    parser.add_argument('-o', '--output', help='Write to file instead of stdout')
    parser.add_argument('-X', '--request', help='Request command to use (e.g. HTTP method)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('url', help='URL of resource to connect to')
    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(Formatter())
    logging.basicConfig(
        handlers=[handler],
        level=logging.DEBUG if args.verbose else logging.ERROR)

    if args.output:
        output = open(args.output, 'wb')
    else:
        output = sys.stdout.buffer

    if args.request:
        method = args.request
    else:
        # Determine method
        if any((arg is not None for arg in [args.data, args.json])):
            method = 'POST'
        else:
            method = 'GET'

    if args.header:
        # Custom headers
        headers = http.client.HTTPMessage()
        for k, v in args.header:
            headers[k] = v.strip()
    else:
        headers = None

    if args.data:
        if len(args.data) > 1:
            # URL-encoded key-values (e.g. `a=1&b=2`)
            data = []
            for value in args.data:
                value = value.split('=', 1)
                if len(value) > 1:
                    data.append((value[0], value[1]))
                else:
                    data.append((value[0], ''))
        else:
            data = args.data[0]
            if data.startswith('@'):
                # File-reference
                data = open(data[1:], 'rb')
            else:
                # Raw data
                data = data.encode('utf-8')
    else:
        data = None

    r = requests.request(method, args.url, headers=headers,
                         data=data, json=args.json,
                         allow_redirects=args.location)
    if output.isatty():
        content_type = r.headers.get('Content-Type', 'application/octet-stream').lower()
        if r.encoding or content_type in SAFE_CONTENT_TYPES or content_type.startswith('text/'):
            print(r.text)
        else:
            print('ERROR: Can\'t display raw {} (use `--output` or redirect)'.format(content_type),
                  file=sys.stderr)
            sys.exit(1)
    else:
        output.write(r.content)


if __name__ == '__main__':
    main()
