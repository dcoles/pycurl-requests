import io
from pycurl_requests import requests
from pycurl_requests.tests.utils import *


def test_streaming_upload_from_file(http_server):
    f = io.BytesIO(test_data)
    response = requests.post(http_server.base_url + '/stream', data=f)
    assert response.status_code == 200


def data_generator(data: bytes, chunk_size: int):
    i = 0
    while True:
        chunk = data[chunk_size * i: chunk_size * (i + 1)]
        if len(chunk) == 0:
            break
        yield chunk
        i += 1


def test_streaming_upload_form_iterable(http_server):
    response = requests.post(http_server.base_url + '/stream', data=data_generator(test_data, 123))
    assert response.status_code == 200


def test_streaming_upload_form_iterable_with_known_length(http_server):
    class FixedLengthIterable:
        data = test_data

        def __len__(self):
            return len(self.data)

        def __iter__(self):
            return data_generator(data=self.data, chunk_size=123)

    response = requests.post(http_server.base_url + '/stream_no_chunked', data=FixedLengthIterable())
    assert response.status_code == 200