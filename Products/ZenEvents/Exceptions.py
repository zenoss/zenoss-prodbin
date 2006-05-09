
from Products.ZenUtils.Exceptions import ZentinelException

class ZenEventError(ZentinelException):
    """
    General problem with the event system.
    """

class ZenBackendFailure(ZenEventError):
    """MySQL or ZEO backend database connection is lost.
    """

class ZenEventNotFound(ZenEventError):
    """
    Lookkup of event failed
    """
