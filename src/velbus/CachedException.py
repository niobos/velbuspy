import datetime


class CachedException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timestamp = datetime.datetime.utcnow()


class CachedTimeoutError(CachedException, TimeoutError):
    pass
