class RequestException(IOError):
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response', None)
        self.request = kwargs.pop('request', None)

        if self.response is not None and not self.request and hasattr(self.response, 'request'):
            self.request = self.response.request

        super().__init__(*args, **kwargs)


class ConnectionError(RequestException):
    pass


class HTTPError(RequestException):
    pass


class URLRequired(RequestException):
    pass


class TooManyRedirects(RequestException):
    pass


class Timeout(RequestException):
    pass


class ConnectTimeout(ConnectionError, Timeout):
    pass


class ReadTimeout(Timeout):
    pass
