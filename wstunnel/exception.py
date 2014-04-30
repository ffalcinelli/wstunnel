from wstunnel import PY2

__author__ = 'fabio'


class ChainedException(Exception):
    """
    An exception which could be caused by another one
    """

    def __init__(self, message, *args, **kwargs):
        cause = kwargs.get("cause", None)
        if cause:
            message = "%s, caused by %s" % (message, repr(cause))

        super(ChainedException, self).__init__(message)


class EndpointNotAvailableException(ChainedException):
    """
    Exception raised when the endpoint is not available (most likely tunnel server side is down)
    """

    def __init__(self, message="Endpoint is not available", *args, **kwargs):
        super(EndpointNotAvailableException, self).__init__(message, *args, **kwargs)


class MappedServiceNotAvailableException(ChainedException):
    """
    Exception raised when the destination service is not available (most likely tunnel server side is up but the
    service is trying to remap does not respond)
    """

    def __init__(self, message="Mapped service is not available", *args, **kwargs):
        super(MappedServiceNotAvailableException, self).__init__(message, *args, **kwargs)
