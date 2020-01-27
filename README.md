# PycURL Requests `<pycurl://☤>`

**PycURL Requests** is a [Requests](https://github.com/psf/requests)-compatible interface for
[PycURL](https://github.com/pycurl/pycurl).

## Requirements

- Python 3.5+
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

## Documentation

This library aims to be API compatible with [Requests](https://github.com/psf/requests),
thus the [Requests documentation](https://requests.readthedocs.io/en/master/) should be
mostly applicable.

## Known limitations

- Currently limited to `GET` requests
- No support for [Cookies](https://requests.readthedocs.io/en/master/user/quickstart/#cookies)
- No support for [timeouts](https://requests.readthedocs.io/en/master/user/quickstart/#timeouts)
- No support for [`Session` objects](https://requests.readthedocs.io/en/master/user/advanced/#session-objects) (e.g. [`requests.Session`](https://requests.readthedocs.io/en/master/api/#requests.Session))
- No support for [client-side certificates](https://requests.readthedocs.io/en/master/user/advanced/#client-side-certificates)
- No support for [proxies](https://requests.readthedocs.io/en/master/user/advanced/#proxies)
- No support for [link headers](https://requests.readthedocs.io/en/master/user/advanced/#link-headers) (e.g. [`Response.links`](https://requests.readthedocs.io/en/master/api/#requests.Response.links))
- No support for [authentication](https://requests.readthedocs.io/en/master/user/authentication/)

Most of these features should be supported in the near future.

## License

Licensed under the MIT License.
