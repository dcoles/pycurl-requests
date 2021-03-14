# PycURL Requests `<pycurl://☤>`

**PycURL Requests** is a [Requests](https://github.com/psf/requests)-compatible interface for
[PycURL](https://github.com/pycurl/pycurl).

[![pycurl-requests](https://circleci.com/gh/dcoles/pycurl-requests.svg?style=shield)](https://circleci.com/gh/dcoles/pycurl-requests)

## Requirements

- Python 3.6+
- [PycURL](https://github.com/pycurl/pycurl)
- [chardet](https://github.com/chardet/chardet)

## Installation

Latest release via [`pip`](https://pip.pypa.io/):

```bash
pip install pycurl-requests [--user]
```

via Git:

```bash
git clone https://github.com/dcoles/pycurl-requests.git; cd pycurl-requests
python3 setup.py install [--user]
```

## Quick-start

```python
>>> import pycurl_requests as requests
>>> r = requests.get('https://api.github.com/repos/dcoles/pycurl-requests')
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf-8'
>>> r.encoding
'utf-8'
>>> r.text
'{\n  "id": 236427187,\n...'
>>> data = r.json()
>>> data['name']
'pycurl-requests'
>>> data['html_url']
'https://github.com/dcoles/pycurl-requests'
>>> data['description']
'A Requests-compatible interface for pycURL'

```

The library can also be used to run existing Python scripts that import the `requests` module.
By running the script through the `pycurl_requests` helper, any use of the `requests` module will
be automatically redirected to `pycurl_requests`.

```bash
python3 -m pycurl_requests -- script.py arg arg...
```

## `request` tool

A basic `curl`-like command-line utility is included:

```
usage: request.py [-h] [-d DATA] [-H HEADER] [--json JSON] [-L] [-o OUTPUT]
                  [-X REQUEST] [-v]
                  url

A basic `curl`-like command-line HTTP utility

positional arguments:
  url                   URL of resource to connect to

optional arguments:
  -h, --help            show this help message and exit
  -d DATA, --data DATA  Add POST data
  -H HEADER, --header HEADER
                        Add custom request header (format: `Header: Value`)
  --json JSON           Add JSON POST data
  -L, --location        Follow redirects
  -o OUTPUT, --output OUTPUT
                        Write to file instead of stdout
  -X REQUEST, --request REQUEST
                        Request command to use (e.g. HTTP method)
  -v, --verbose         Verbose logging
```

This can also be used with the [Requests](https://github.com/psf/requests) library if
`PYCURLREQUESTS_REQUESTS` environment variable is set to a non-null value.

## Documentation

This library aims to be API compatible with [Requests](https://github.com/psf/requests),
thus the [Requests documentation](https://requests.readthedocs.io/en/master/) should be
mostly applicable.

### cURL options

It is possible customize cURL's behaviour using the `curl` attribute on a
[`Session object`](https://requests.readthedocs.io/en/master/user/advanced/#session-objects).

For example, to make a request without requesting the body:

```python
import pycurl
import pycurl_requests as requests

with requests.Session() as session:
    session.curl.setopt(pycurl.NOBODY, 1)
    response = session.get('http://example.com')
```

See the [`pycurl.Curl` object](http://pycurl.io/docs/latest/curlobject.html) documentation
for all possible `curl` attribute methods.

### cURL exceptions

All [`pycurl.error` exceptions](http://pycurl.io/docs/latest/callbacks.html#error-reporting)
are mapped to a [`requests.RequestException`](https://requests.readthedocs.io/en/master/api/#exceptions)
(or one of its subclasses).

For convenience, the original `pycurl.error` error message and
[cURL error code](https://curl.haxx.se/libcurl/c/libcurl-errors.html) will be set on the exception
object as the `curl_message` and `curl_code` attributes.

```python
import pycurl_requests as requests

try:
    requests.get('http://connect_error')
except requests.RequestException as e:
    print('ERROR: {} (cURL error: {})'.format(e.curl_message, e.curl_code))
```

It is also possible to obtain the original `pycurl.error` using the `__cause__` attribute.

### Logging

Detailed log records from `libcurl`, including informational text and HTTP headers, can be shown
by setting the `curl` logger (or sub-loggers) to [`DEBUG` level](https://docs.python.org/3/library/logging.html#logging-levels):

```python
import logging

logging.getLogger('curl').setLevel(logging.DEBUG)
```

Log records are split into dedicated sub-loggers for each type of record:

- `curl.text` &mdash; Informational text
- `curl.header_in` &mdash; Header data received from the peer
- `curl.header_out` &mdash; Header data sent to the peer

## Known limitations

- No support for reading [Cookies](https://requests.readthedocs.io/en/master/user/quickstart/#cookies)
- No support for [client-side certificates](https://requests.readthedocs.io/en/master/user/advanced/#client-side-certificates)
- No support for [proxies](https://requests.readthedocs.io/en/master/user/advanced/#proxies)
- No support for [link headers](https://requests.readthedocs.io/en/master/user/advanced/#link-headers) (e.g. [`Response.links`](https://requests.readthedocs.io/en/master/api/#requests.Response.links))
- No support for [sending multi-part encoded files](https://requests.readthedocs.io/en/master/user/advanced/#post-multiple-multipart-encoded-files)
- Basic support for [`Session` objects](https://requests.readthedocs.io/en/master/user/advanced/#session-objects) (e.g. [`requests.Session`](https://requests.readthedocs.io/en/master/api/#requests.Session))

Most of these features should be supported in the near future.

## License

Licensed under the MIT License.
