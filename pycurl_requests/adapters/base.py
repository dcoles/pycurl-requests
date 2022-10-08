"""
Base adapter.
"""

class BaseAdapter:
    """
    Base transport adapter.

    This should be kept in sync with `requests.adapters.BaseAdapter`.
    """
    def __init__(self) -> None:
        super().__init__()

    # We pass through kwargs, since we have a few pycurl specific extensions.
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None, **kwargs) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
