from pycurl_requests import _pycurl


def request(method, url, **kwargs):
    return _pycurl.request(method, url, **kwargs)


def head(url, **kwargs):
    return request('HEAD', url, **kwargs)


def get(url, params=None, **kwargs):
    return request('GET', url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    return request('POST', url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    return request('PUT', url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    return request('PATCH', url, data=data, **kwargs)


def delete(url, params=None, **kwargs):
    return request('GET', url, params=params, **kwargs)
