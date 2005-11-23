
from Products.ZenUtils.Exceptions import ZentinelException

class ZenEventError(ZentinelException):
    """
    General problem with the event system.
    """

class ZenEventNotFound(ZenEventError):
    """
    Lookkup of event failed
    """
