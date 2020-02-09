import http.client


class CaseInsensitiveDict(http.client.HTTPMessage):
    """For compatibility with Requests."""
    def __init__(self, value=None, **kwargs):
        super(CaseInsensitiveDict, self).__init__()

        value = dict(value, **kwargs) if value is not None else kwargs
        for k, v in value.items():
            self[k] = v
