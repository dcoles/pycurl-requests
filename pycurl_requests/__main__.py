"""Shim for running existing Requests-based script using PycURL-Requests."""
import argparse
import runpy
import sys

import pycurl_requests


def main():
    parser = argparse.ArgumentParser(description='a Requests-compatible interface for PycURL')
    parser.add_argument('-m', dest='is_module', action='store_true',
                        help='run library module as script')
    parser.add_argument('name', help='script or module run')
    parser.add_argument('arg', nargs=argparse.REMAINDER, help='script arguments')
    args = parser.parse_args()

    # Override requests
    pycurl_requests.patch_requests()

    # Run script
    sys.argv[1:] = args.arg
    if args.is_module:
        runpy.run_module(args.name, run_name='__main__', alter_sys=True)
    else:
        runpy.run_path(args.name, run_name='__main__')
    sys.exit()


if __name__ == '__main__':
    main()
