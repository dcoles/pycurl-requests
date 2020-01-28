class RequestException(IOError):
    def __init__(self, *args, curl_error=None, curl_code=None, request=None, response=None):
        self.curl_error = curl_error
        self.curl_code = curl_code
        self.request = request
        self.response = response

        if self.response is not None and not self.request and hasattr(self.response, 'request'):
            self.request = self.response.request

        super().__init__(*args)


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
