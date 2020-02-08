from pycurl_requests import sessions


def request(method, url, **kwargs):
    with sessions.Session() as session:
        return session.request(method, url, **kwargs)


def head(url, **kwargs):
    with sessions.Session() as session:
        return session.head(url, **kwargs)


def get(url, params=None, **kwargs):
    with sessions.Session() as session:
        return session.get(url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    with sessions.Session() as session:
        return session.post(url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    with sessions.Session() as session:
        return session.put(url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    with sessions.Session() as session:
        return session.patch(url, data=data, **kwargs)


def delete(url, params=None, **kwargs):
    with sessions.Session() as session:
        return session.delete(url, params=params, **kwargs)
