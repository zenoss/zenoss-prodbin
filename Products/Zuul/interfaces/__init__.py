from zope.interface import Interface

class IService(Interface):
    """
    An API service
    """

class IServiceable(Interface):
    """
    Marker interface for things that can be the context of an IService
    """

from events import *
