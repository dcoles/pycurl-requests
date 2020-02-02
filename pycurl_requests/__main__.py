"""Shim for running existing Requests-based script using PycURL-Requests."""
import argparse
import runpy
import sys

import pycurl_requests


def main():
    parser = argparse.ArgumentParser(description='a Requests-compatible interface for PycURL')
    parser.add_argument('script', help='Python script to run')
    parser.add_argument('arg', nargs='*', help='script arguments')
    args = parser.parse_args()

    # Override requests
    sys.modules['requests'] = pycurl_requests

    # Run script
    sys.argv[1:] = args.arg
    runpy.run_path(args.script, run_name='__main__')
    sys.exit()


if __name__ == '__main__':
    main()
